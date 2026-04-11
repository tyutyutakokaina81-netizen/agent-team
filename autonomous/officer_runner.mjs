// officer_runner.mjs
// 1役職ぶんの "今日のターン" を実行する関数。
//
// 流れ:
//   1. 役職のコンテキスト（company.md / context/ / prompt.md / _index.md / 他役職サマリ）を読み込む
//   2. Claude に「今日1つだけタスクを選んで実行せよ」と依頼する（構造化JSON応答）
//   3. budget_guard に事前許可を問い合わせ、NG なら正常終了する
//   4. Claude API を呼ぶ（dry-run モードではモック応答を返す）
//   5. 応答を parse し、ファイル書き込み＋_index.md 追記＋他役職への message を task_queue に追加
//   6. 実消費を budget_guard.record() に記録する
//
// 重要: このファイルは "呼ばれる" 側。orchestrator.mjs が役職を選んで呼ぶ。
// 重要: Claude API キーは ANTHROPIC_API_KEY 環境変数から読む。キー未設定時は dry-run に自動 fallback。

import { readFile, writeFile, mkdir, readdir, access } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import * as budget from './budget_guard.mjs';
import * as memory from './memory.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, '..');

const OFFICERS = ['CDO', 'CFO', 'CMO', 'CPO', 'CSO'];

const DEFAULT_MODEL = 'claude-haiku-4-5-20251001';
const DEFAULT_MAX_TOKENS = 2000;
const ESTIMATE_PER_TURN_YEN = 15; // 事前見積もり（Haiku で input ~3k / output ~1.5k 程度）

// ─────────────────────────────────────────────────────────────
// コンテキスト読み込み
// ─────────────────────────────────────────────────────────────

async function safeRead(file, fallback = '') {
  try {
    return await readFile(file, 'utf8');
  } catch {
    return fallback;
  }
}

async function safeList(dir) {
  try {
    return await readdir(dir);
  } catch {
    return [];
  }
}

/**
 * context/ 下の指定フォルダから .md ファイルを読み込む。
 * ファイル名 (降順＝新しい順) でソートし、limit 件まで。
 * 各ファイルは chars 文字まで切り詰める。
 */
async function loadContextFolder(dir, { limit, chars }) {
  const names = await safeList(dir);
  const mdFiles = names.filter(n => n.endsWith('.md')).sort().reverse().slice(0, limit);
  const out = [];
  for (const name of mdFiles) {
    const content = await safeRead(path.join(dir, name), '');
    if (content.trim()) {
      out.push({
        filename: name,
        content: content.length > chars ? content.slice(0, chars) + '\n...[切り詰め]' : content,
      });
    }
  }
  return out;
}

/**
 * 役職用のコンテキストを集める。
 * @param {string} officer - 役職名 (e.g. "CDO")
 * @returns {Promise<object>} ctx
 */
export async function loadOfficerContext(officer) {
  if (!OFFICERS.includes(officer)) {
    throw new Error(`unknown officer: ${officer}`);
  }

  const companyMd = await safeRead(path.join(REPO_ROOT, 'company.md'), '(company.md not found)');
  const claudeMd = await safeRead(path.join(REPO_ROOT, 'CLAUDE.md'), '');
  const officerPrompt = await safeRead(
    path.join(REPO_ROOT, officer, 'prompt.md'),
    `(${officer}/prompt.md not found)`
  );
  const officerIndex = await safeRead(
    path.join(REPO_ROOT, officer, '_index.md'),
    ''
  );

  // 他役職の _index.md 冒頭 40 行だけ読む（トークン節約）
  const otherOfficersSummary = {};
  for (const other of OFFICERS) {
    if (other === officer) continue;
    const content = await safeRead(path.join(REPO_ROOT, other, '_index.md'), '');
    otherOfficersSummary[other] = content.split('\n').slice(0, 40).join('\n');
  }

  // context/ の中身を読み込む。
  // ideas は standing directive を含むため全文読み込み（上限 20 件・各 4000 字）。
  // diary と references は直近 5 件・各 2000 字まで。
  const contextBody = {
    ideas: await loadContextFolder(path.join(REPO_ROOT, 'context', 'ideas'), { limit: 20, chars: 4000 }),
    diary: await loadContextFolder(path.join(REPO_ROOT, 'context', 'diary'), { limit: 5, chars: 2000 }),
    references: await loadContextFolder(path.join(REPO_ROOT, 'context', 'references'), { limit: 5, chars: 2000 }),
  };

  // プロジェクトブリーフ
  const projectBrief = await safeRead(
    path.join(REPO_ROOT, 'projects', '2026-04-08_月30万自動化', 'brief.md'),
    ''
  );

  // 自律基盤の設計仕様（CDO 限定で詳細、他は概要のみ）
  const autonomousSpec = await safeRead(
    path.join(REPO_ROOT, 'CDO', 'outputs', '2026-04-11_autonomous_ai_spec.md'),
    ''
  );

  // task_queue から自分宛メッセージを取り出す（consume は turn 成功後に実施）
  const queue = await loadTaskQueue();
  const myMessages = queue.queue.filter(m => m.to === officer);

  // 短期記憶（memory.mjs）を読み込む
  const mem = await memory.recall(officer);

  return {
    officer,
    today: new Date().toISOString().slice(0, 10),
    companyMd,
    claudeMdHeader: claudeMd.split('\n').slice(0, 80).join('\n'),
    officerPrompt,
    officerIndex,
    otherOfficersSummary,
    contextBody,
    projectBrief,
    autonomousSpec: officer === 'CDO' ? autonomousSpec : autonomousSpec.split('\n').slice(0, 30).join('\n'),
    myMessages,
    shortTermMemory: mem.shortTerm,
    longTermMemory: mem.longTerm,
  };
}

// ─────────────────────────────────────────────────────────────
// メッセージ構築（Claude API への入力）
// ─────────────────────────────────────────────────────────────

export function buildMessages(ctx) {
  // オーナーからの standing directive（context/ideas/ に置かれたもの）を強調ブロックで出す
  const ideasBlock = ctx.contextBody.ideas.length > 0
    ? [
        '## ⭐ オーナーからの standing directive（context/ideas/）',
        '以下は「日々のループで必ず考慮すべき」オーナー指示である。優先度は最高。',
        '',
        ...ctx.contextBody.ideas.map(f => `### ${f.filename}\n${f.content}`),
      ].join('\n')
    : '';

  const diaryBlock = ctx.contextBody.diary.length > 0
    ? [
        '## オーナーの日記（context/diary/ 直近分）',
        ...ctx.contextBody.diary.map(f => `### ${f.filename}\n${f.content}`),
      ].join('\n')
    : '';

  const referencesBlock = ctx.contextBody.references.length > 0
    ? [
        '## 参考資料（context/references/ 直近分）',
        ...ctx.contextBody.references.map(f => `### ${f.filename}\n${f.content}`),
      ].join('\n')
    : '';

  const system = [
    `あなたは AI 自律経営会社の ${ctx.officer} です。`,
    '',
    '## あなたの役職定義（prompt.md）',
    ctx.officerPrompt,
    '',
    '## 会社全体ルール（company.md 要約）',
    ctx.companyMd.slice(0, 3000),
    '',
    '## 現在のミッション',
    '今月（2026-04）は「自立型AI基盤構築月」。収益目標はゼロ、インフラ構築が目的。',
    '人間オーナーは一切作業しない。あなたは自律して判断し、1ターンで1つだけ成果物を作る。',
    '',
    ideasBlock,
    '',
    diaryBlock,
    '',
    referencesBlock,
  ].filter(s => s && s.trim()).join('\n');

  const shortTermBlock = memory.formatShortTermForPrompt(ctx.shortTermMemory);

  const user = [
    `今日の日付: ${ctx.today}`,
    '',
    '## あなたの短期記憶（直近ターンの履歴）',
    shortTermBlock,
    '',
    '## あなた自身の成果物ログ（_index.md）',
    ctx.officerIndex,
    '',
    '## 他役職の最新サマリ',
    Object.entries(ctx.otherOfficersSummary)
      .map(([k, v]) => `### ${k}\n${v}`)
      .join('\n\n'),
    '',
    '## プロジェクトブリーフ（月30万自動化 → 自立型AI構築月）',
    ctx.projectBrief,
    '',
    ctx.myMessages.length > 0 ? '## あなた宛の task_queue メッセージ' : '',
    ctx.myMessages.length > 0 ? JSON.stringify(ctx.myMessages, null, 2) : '',
    '',
    '## 今日のあなたのタスク',
    '自律判断で、今日1つだけやるべきことを決めて実行してください。',
    '直近の短期記憶を見て、同じことを繰り返さず、連続性のある次の一手を選ぶこと。',
    '',
    '## 出力形式（必ず有効な JSON で、他の文字は一切含めない）',
    '```json',
    '{',
    '  "today_decision": "今日やる1文（100文字以内）",',
    '  "rationale": "なぜそれを選んだか（200文字以内）",',
    '  "artifact": {',
    '    "type": "research" または "outputs",',
    '    "filename": "YYYY-MM-DD_わかりやすい名前.md",',
    '    "title": "成果物のタイトル",',
    '    "content": "成果物の本文（markdown、2000文字以内）"',
    '  },',
    '  "index_row": "| 2026-04-11 | ファイル名 | 種別 | 概要 | ステータス |",',
    '  "messages_to_others": [',
    '    { "to": "CPO", "message": "他役職への引き継ぎメモ（任意、なければ空配列）" }',
    '  ]',
    '}',
    '```',
    '',
    '必ず有効な JSON のみを返してください。markdown のコードブロックで囲んでも構いませんが、JSON 以外の説明文は一切不要です。',
  ].filter(Boolean).join('\n');

  return { system, user };
}

// ─────────────────────────────────────────────────────────────
// Claude API 呼び出し
// ─────────────────────────────────────────────────────────────

async function callClaudeAPI({ system, user, model, maxTokens }) {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    throw new Error('ANTHROPIC_API_KEY not set');
  }

  const res = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({
      model,
      max_tokens: maxTokens,
      system,
      messages: [{ role: 'user', content: user }],
    }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Claude API ${res.status}: ${text}`);
  }

  const data = await res.json();
  const textBlock = (data.content || []).find(b => b.type === 'text');
  const text = textBlock ? textBlock.text : '';

  return {
    text,
    usage: data.usage || { input_tokens: 0, output_tokens: 0 },
  };
}

function mockResponse({ officer, today }) {
  const mockArtifact = {
    today_decision: `[dry-run] ${officer} の今日のサンプルタスク`,
    rationale: 'dry-run モードなので実 API は呼ばれていません。構造テスト用のモックです。',
    artifact: {
      type: 'research',
      filename: `${today}_dryrun_${officer.toLowerCase()}.md`,
      title: `${officer} dry-run sample`,
      content: `# ${officer} dry-run sample\n\nこれは officer_runner.mjs を dry-run モードで実行した際のモック成果物です。\n\n- 日付: ${today}\n- 役職: ${officer}\n- 実 Claude API は呼び出されていません\n`,
    },
    index_row: `| ${today} | ${today}_dryrun_${officer.toLowerCase()}.md | dry-run | officer_runner 動作確認 | モック |`,
    messages_to_others: [],
  };
  return {
    text: JSON.stringify(mockArtifact),
    usage: { input_tokens: 0, output_tokens: 0 },
    mock: true,
  };
}

// ─────────────────────────────────────────────────────────────
// 応答 parse
// ─────────────────────────────────────────────────────────────

export function parseResponse(text) {
  // ```json ... ``` で囲まれていたら剥がす
  let cleaned = text.trim();
  const fence = cleaned.match(/^```(?:json)?\s*\n([\s\S]*?)\n```\s*$/);
  if (fence) cleaned = fence[1];

  // 先頭/末尾の余計な文字を削る（最初の { から最後の } まで）
  const firstBrace = cleaned.indexOf('{');
  const lastBrace = cleaned.lastIndexOf('}');
  if (firstBrace >= 0 && lastBrace > firstBrace) {
    cleaned = cleaned.slice(firstBrace, lastBrace + 1);
  }

  try {
    const parsed = JSON.parse(cleaned);
    validateResponse(parsed);
    return parsed;
  } catch (err) {
    throw new Error(`failed to parse officer response: ${err.message}\n--- raw ---\n${text.slice(0, 500)}`);
  }
}

function validateResponse(r) {
  if (!r || typeof r !== 'object') throw new Error('response is not an object');
  if (typeof r.today_decision !== 'string') throw new Error('today_decision missing');
  if (!r.artifact || typeof r.artifact !== 'object') throw new Error('artifact missing');
  const a = r.artifact;
  if (!['research', 'outputs'].includes(a.type)) throw new Error('artifact.type invalid');
  if (typeof a.filename !== 'string' || !a.filename) throw new Error('artifact.filename missing');
  if (typeof a.content !== 'string' || !a.content) throw new Error('artifact.content missing');
  if (typeof r.index_row !== 'string') throw new Error('index_row missing');
  if (!Array.isArray(r.messages_to_others)) r.messages_to_others = [];
}

// ─────────────────────────────────────────────────────────────
// 結果の適用（ファイル書き込み／_index.md 追記／task_queue 更新）
// ─────────────────────────────────────────────────────────────

export async function applyResult(officer, result) {
  const { artifact, index_row, messages_to_others } = result;

  // 1. 成果物を書き出す
  const targetDir = path.join(REPO_ROOT, officer, artifact.type);
  await mkdir(targetDir, { recursive: true });
  const targetFile = path.join(targetDir, artifact.filename);
  await writeFile(targetFile, artifact.content + '\n', 'utf8');

  // 2. _index.md に追記（成果物ログ行の末尾に追加）
  const indexPath = path.join(REPO_ROOT, officer, '_index.md');
  const indexContent = await safeRead(indexPath, '');
  const updated = appendIndexRow(indexContent, index_row);
  if (updated !== indexContent) {
    await writeFile(indexPath, updated, 'utf8');
  }

  // 3. task_queue に他役職向けメッセージを追加
  if (messages_to_others.length > 0) {
    await appendToTaskQueue(officer, messages_to_others);
  }

  return {
    artifactPath: path.relative(REPO_ROOT, targetFile),
    indexUpdated: updated !== indexContent,
    messagesQueued: messages_to_others.length,
  };
}

function appendIndexRow(indexContent, newRow) {
  if (!indexContent) return indexContent;
  const lines = indexContent.split('\n');
  // 「成果物ログ」テーブルを探して、最後の行の後に追加する
  let inTable = false;
  let lastTableLine = -1;
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].startsWith('| 日付') || lines[i].startsWith('|------')) {
      inTable = true;
      continue;
    }
    if (inTable) {
      if (lines[i].startsWith('|')) {
        lastTableLine = i;
      } else if (lines[i].trim() === '' || lines[i].startsWith('#')) {
        break;
      }
    }
  }
  if (lastTableLine >= 0) {
    // 既存の "| — | — | — | — | — |" プレースホルダを置き換える
    if (lines[lastTableLine].includes('| — |')) {
      lines[lastTableLine] = newRow;
    } else {
      lines.splice(lastTableLine + 1, 0, newRow);
    }
    return lines.join('\n');
  }
  return indexContent;
}

// task_queue.json は autonomous/state/ 以下に置く（クロスラン永続）
const TASK_QUEUE_FILE = path.join(__dirname, 'state', 'task_queue.json');

async function loadTaskQueue() {
  if (!existsSync(TASK_QUEUE_FILE)) return { queue: [] };
  try {
    const q = JSON.parse(await readFile(TASK_QUEUE_FILE, 'utf8'));
    if (!Array.isArray(q.queue)) q.queue = [];
    return q;
  } catch {
    return { queue: [] };
  }
}

async function saveTaskQueue(queue) {
  await mkdir(path.dirname(TASK_QUEUE_FILE), { recursive: true });
  await writeFile(TASK_QUEUE_FILE, JSON.stringify(queue, null, 2) + '\n', 'utf8');
}

async function appendToTaskQueue(fromOfficer, messages) {
  const queue = await loadTaskQueue();
  const now = new Date().toISOString();
  for (const m of messages) {
    queue.queue.push({
      id: `${now}-${Math.random().toString(36).slice(2, 8)}`,
      from: fromOfficer,
      to: m.to,
      priority: m.priority || 'normal',
      created: now,
      message: m.message,
    });
  }
  await saveTaskQueue(queue);
}

/**
 * 役職に届いていた message を queue から削除する（consume）。
 * ターン成功後に呼ぶことで、同じメッセージを繰り返し処理しない。
 */
async function consumeTaskQueueFor(officer) {
  const queue = await loadTaskQueue();
  const before = queue.queue.length;
  queue.queue = queue.queue.filter(m => m.to !== officer);
  const consumed = before - queue.queue.length;
  if (consumed > 0) {
    await saveTaskQueue(queue);
  }
  return consumed;
}

// ─────────────────────────────────────────────────────────────
// 公開 API: 1役職の 1 ターンを実行
// ─────────────────────────────────────────────────────────────

/**
 * 1役職の1ターンを実行する。
 *
 * @param {string} officer - 役職名
 * @param {object} [opts]
 * @param {string} [opts.mode='auto'] - 'live' | 'dry-run' | 'auto'（auto: APIキーあれば live、なければ dry-run）
 * @param {string} [opts.model] - 使用モデル
 * @param {number} [opts.maxTokens]
 * @returns {Promise<object>} 実行結果
 */
export async function runOfficerTurn(officer, opts = {}) {
  const mode = opts.mode || 'auto';
  const model = opts.model || DEFAULT_MODEL;
  const maxTokens = opts.maxTokens || DEFAULT_MAX_TOKENS;

  // 1. 予算チェック（事前見積もり）
  const check = await budget.canProceed({ estimate: ESTIMATE_PER_TURN_YEN });
  if (!check.allowed) {
    return {
      officer,
      skipped: true,
      reason: check.reason,
      state: check.state,
    };
  }

  // 2. コンテキスト読み込み
  const ctx = await loadOfficerContext(officer);

  // 3. メッセージ構築
  const messages = buildMessages(ctx);

  // 4. 実行モード決定
  const resolved = mode === 'auto'
    ? (process.env.ANTHROPIC_API_KEY ? 'live' : 'dry-run')
    : mode;

  // 5. Claude 呼び出し
  let response;
  try {
    if (resolved === 'dry-run') {
      response = mockResponse({ officer, today: ctx.today });
    } else {
      response = await callClaudeAPI({
        system: messages.system,
        user: messages.user,
        model,
        maxTokens,
      });
    }
  } catch (err) {
    return {
      officer,
      error: `claude call failed: ${err.message}`,
      mode: resolved,
    };
  }

  // 6. 応答 parse
  let parsed;
  try {
    parsed = parseResponse(response.text);
  } catch (err) {
    return {
      officer,
      error: `parse failed: ${err.message}`,
      raw: response.text.slice(0, 500),
    };
  }

  // 7. 結果適用
  const applied = await applyResult(officer, parsed);

  // 8. 実消費を記録（dry-run でも 0 円で記録）
  const recorded = await budget.record({
    officer,
    model,
    inputTokens: response.usage.input_tokens,
    outputTokens: response.usage.output_tokens,
  });

  // 9. 短期記憶に追加
  await memory.remember(officer, {
    date: ctx.today,
    decision: parsed.today_decision,
    rationale: parsed.rationale,
    artifactPath: applied.artifactPath,
  });

  // 10. task_queue から自分宛メッセージを consume（繰り返し処理を防ぐ）
  const consumed = await consumeTaskQueueFor(officer);

  return {
    officer,
    mode: resolved,
    decision: parsed.today_decision,
    rationale: parsed.rationale,
    artifactPath: applied.artifactPath,
    indexUpdated: applied.indexUpdated,
    messagesQueued: applied.messagesQueued,
    messagesConsumed: consumed,
    spend: {
      thisCall: recorded.yen,
      today: recorded.todaySpend,
      month: recorded.monthSpend,
    },
  };
}

// ─────────────────────────────────────────────────────────────
// CLI エントリ
// ─────────────────────────────────────────────────────────────
//
// 使い方:
//   node autonomous/officer_runner.mjs CDO           # 自動モード
//   node autonomous/officer_runner.mjs CDO dry-run   # 強制 dry-run
//   node autonomous/officer_runner.mjs CDO live      # 強制 live（APIキー必須）

const isMain = import.meta.url === `file://${process.argv[1]}`;
if (isMain) {
  const officer = process.argv[2];
  const mode = process.argv[3] || 'auto';
  if (!officer || !OFFICERS.includes(officer)) {
    console.error(`Usage: node officer_runner.mjs <CDO|CFO|CMO|CPO|CSO> [auto|dry-run|live]`);
    process.exit(1);
  }
  const result = await runOfficerTurn(officer, { mode });
  console.log(JSON.stringify(result, null, 2));
}
