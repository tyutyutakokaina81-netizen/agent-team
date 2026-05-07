#!/usr/bin/env node
/**
 * note_article_scaffold.mjs — note 集客記事スキャフォルド生成
 *
 * 費用ゼロ：
 *   - Node 標準モジュール（node:fs / node:path / node:url）のみ
 *   - 外部 API 呼び出しなし
 *   - npm install 不要
 *
 * 使い方:
 *   node CDO/outputs/note_article_scaffold.mjs --topic vol2_sns_calendar
 *   node CDO/outputs/note_article_scaffold.mjs --topic vol3_restaurant_prompts --dry-run
 *   node CDO/outputs/note_article_scaffold.mjs --list
 *
 * 出力:
 *   CMO/research/YYYY-MM-DD_note集客記事_<slug>_input.md
 *     → INPUT JSON ＋ プロンプト貼り付け手順を含むファイル
 *     → これを Claude Pro チャットに貼って本文を生成する
 *
 *   CMO/_index.md に「下書き」ステータスで自動追記
 *
 * 本文の最終版は Claude Pro の出力を CMO/outputs/YYYY-MM-DD_note集客記事_<slug>.md に保存。
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync, readdirSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { today } from './lib/pdca_lib.mjs';

const __dir = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dir, '../..');
const TOPICS_DIR = join(__dir, 'topics');
const CMO_RESEARCH = join(REPO_ROOT, 'CMO', 'research');
const CMO_INDEX = join(REPO_ROOT, 'CMO', '_index.md');

// ─────────────────────────────────────────────
// CLI 引数
// ─────────────────────────────────────────────
function parseArgs(argv) {
  const args = { topic: null, dryRun: false, list: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--topic') args.topic = argv[++i];
    else if (a === '--dry-run') args.dryRun = true;
    else if (a === '--list') args.list = true;
    else if (a === '--help' || a === '-h') args.help = true;
  }
  return args;
}

function showHelp() {
  console.log(`note_article_scaffold.mjs

USAGE:
  node CDO/outputs/note_article_scaffold.mjs --topic <slug>
  node CDO/outputs/note_article_scaffold.mjs --list
  node CDO/outputs/note_article_scaffold.mjs --topic <slug> --dry-run

OPTIONS:
  --topic <slug>   topics/<slug>.json を読んでスキャフォルド生成
  --list           利用可能なトピック一覧を表示
  --dry-run        ファイルを書かずに出力内容を表示
  --help, -h       このヘルプを表示

費用ゼロ：外部API呼び出し・SaaS契約・npm install いずれも不要です。
`);
}

// ─────────────────────────────────────────────
// トピック一覧
// ─────────────────────────────────────────────
function listTopics() {
  if (!existsSync(TOPICS_DIR)) {
    console.error(`トピック設定が見つかりません: ${TOPICS_DIR}`);
    process.exit(1);
  }
  const files = readdirSync(TOPICS_DIR).filter(f => f.endsWith('.json'));
  if (!files.length) {
    console.log('（トピック設定なし）');
    return;
  }
  console.log('利用可能なトピック:');
  for (const f of files) {
    const slug = f.replace(/\.json$/, '');
    try {
      const cfg = JSON.parse(readFileSync(join(TOPICS_DIR, f), 'utf-8'));
      console.log(`  - ${slug}  →  Vol.${cfg.vol_number} ${cfg.template_name} (¥${cfg.template_price})`);
    } catch {
      console.log(`  - ${slug}  (設定読み込みエラー)`);
    }
  }
}

// ─────────────────────────────────────────────
// トピック読み込み
// ─────────────────────────────────────────────
function loadTopic(slug) {
  const path = join(TOPICS_DIR, `${slug}.json`);
  if (!existsSync(path)) {
    console.error(`トピック設定が見つかりません: ${path}`);
    console.error(`--list で一覧を確認してください。`);
    process.exit(1);
  }
  try {
    return JSON.parse(readFileSync(path, 'utf-8'));
  } catch (e) {
    console.error(`JSON パースエラー (${path}): ${e.message}`);
    process.exit(1);
  }
}

// ─────────────────────────────────────────────
// バリデーション
// ─────────────────────────────────────────────
function validateTopic(cfg) {
  const required = ['vol_number', 'slug', 'template_name', 'template_price', 'problem', 'target_reader', 'seo_keywords', 'features', 'tone'];
  const missing = required.filter(k => cfg[k] === undefined || cfg[k] === null || cfg[k] === '');
  if (missing.length) {
    console.error(`トピック設定に必須キーが不足: ${missing.join(', ')}`);
    process.exit(1);
  }
  if (!Array.isArray(cfg.seo_keywords) || cfg.seo_keywords.length === 0) {
    console.error('seo_keywords は配列で1つ以上必要です。');
    process.exit(1);
  }
  if (!Array.isArray(cfg.features) || cfg.features.length < 3) {
    console.error('features は配列で3つ以上必要です。');
    process.exit(1);
  }
  if (!['共感', '実用', '理論派'].includes(cfg.tone)) {
    console.error(`tone は「共感」「実用」「理論派」のいずれか。受信値: ${cfg.tone}`);
    process.exit(1);
  }
}

// ─────────────────────────────────────────────
// スキャフォルド本体
// ─────────────────────────────────────────────
function buildScaffold(cfg, dateStr) {
  const featuresText = cfg.features.map(f => `- ${f}`).join('\n');
  const keywordsText = cfg.seo_keywords.map(k => `「${k}」`).join('・');
  const inputJson = JSON.stringify(cfg, null, 2);

  return `# [INPUT] note 集客記事スキャフォルド：Vol.${cfg.vol_number} ${cfg.template_name}

> このファイルは \`CDO/outputs/note_article_scaffold.mjs\` が自動生成しました。
> 本文の最終生成は **既存契約済みの Claude Pro チャット** に下記プロンプトを貼って行ってください。
> 外部 API 呼び出しはありません。費用は発生しません。

## ステップ

1. このファイル下部の「Claude Pro 用プロンプト全文」をコピー
2. Claude Pro のチャットに貼って送信
3. 出力された Markdown 本文を \`CMO/outputs/${dateStr}_note集客記事_${cfg.slug}.md\` として保存
4. \`CMO/_index.md\` のステータスを「完了」に更新（自動追記済み）

## トピック概要

| 項目 | 内容 |
|------|------|
| Vol | ${cfg.vol_number} |
| テンプレ名 | ${cfg.template_name} |
| 価格 | ¥${cfg.template_price} |
| 困りごと | ${cfg.problem} |
| ターゲット | ${cfg.target_reader} |
| 検索想定キーワード | ${keywordsText} |
| トーン | ${cfg.tone} |

## テンプレ機能（記事の根拠）

${featuresText}

---

## Claude Pro 用プロンプト全文（ここからコピー）

\`\`\`
あなたはこの会社のCMO（Chief Marketing Officer）です。
オーナーが運営する note アカウントで、テンプレート販売への集客記事を作成します。

【絶対ルール】
1. 出力は日本語のみ
2. 8割は無料で実践できるノウハウ、2割だけ自然にテンプレへ誘導する
3. 売り込み色を出さない（「絶対」「必ず」「儲かる」等の煽り表現禁止）
4. 専門用語は必ず1行で補足する
5. 冒頭は読者の感情・困りごとから入る（情報からは入らない）
6. 数字は具体的に（「多くの人が」ではなく「3人に1人が」のように）
7. 出力は下記のテンプレート構造を厳守する

【出力テンプレート構造】
- タイトル（30字以内、検索キーワードを必ず1つ含む）
- 冒頭フック（読者の困りごと・感情に共感、3〜5行）
- 本論：3つの「習慣／コツ／ステップ」（各300〜400字）
- まとめ（型・本質を1段落で）
- CTA（テンプレ案内、控えめに1ブロック、価格と [LINK_PLACEHOLDER] を含める）
- 締めの一言（コメント・スキ誘導）
- ハッシュタグ（5個まで）
- 公開チェックリスト（オーナー作業用）

【入力】
${inputJson}

【出力形式】
Markdown のコードブロック（\\\`\\\`\\\`）の中に、note にそのまま貼れる本文を入れてください。
コードブロックの後ろに、ハッシュタグ・公開チェックリスト・効果測定指標を Markdown で続けてください。
\`\`\`

ここまでコピー ↑

---

## 出力後にやること

\`\`\`
□ Claude Pro の出力を CMO/outputs/${dateStr}_note集客記事_${cfg.slug}.md に保存
□ [LINK_PLACEHOLDER] を Vol.${cfg.vol_number} 販売ページの実 URL に差し替え
□ Canva でアイキャッチ作成（既存契約済み・新規費用ゼロ）
□ note にコピペして公開（無料記事）
□ 公開後、X で告知（既存アカウント・費用ゼロ）
□ CMO/_index.md のステータスを「完了 → 公開済」に更新
\`\`\`
`;
}

// ─────────────────────────────────────────────
// _index.md への追記
// ─────────────────────────────────────────────
function appendToIndex(cfg, dateStr, scaffoldPath) {
  if (!existsSync(CMO_INDEX)) {
    console.warn(`CMO/_index.md が見つかりません。スキップします。`);
    return;
  }
  const current = readFileSync(CMO_INDEX, 'utf-8');
  const relPath = scaffoldPath.replace(REPO_ROOT + '/', '');
  const newRow = `| ${dateStr} | ${relPath} | スキャフォルド | Vol.${cfg.vol_number} ${cfg.template_name} 集客記事の入力JSON＋プロンプト | 下書き |`;

  if (current.includes(relPath)) {
    console.log(`  _index.md に既存記載あり、追記スキップ: ${relPath}`);
    return;
  }

  const lines = current.split('\n');
  let inserted = false;
  const out = [];
  for (let i = 0; i < lines.length; i++) {
    out.push(lines[i]);
    if (!inserted && lines[i].startsWith('|------')) {
      // テーブルヘッダ直下に挿入したいが、既存行を保持するため最後の行を探す方式に切替
      // → ヘッダ直下挿入方式：以降の最後のテーブル行の次に挿入する
    }
  }

  // 改めて：最後のテーブル行を見つけて、その下に挿入
  const out2 = [];
  let lastTableRowIdx = -1;
  for (let i = 0; i < lines.length; i++) {
    if (/^\|\s*\d{4}-\d{2}-\d{2}\s*\|/.test(lines[i]) || /^\|\s*—\s*\|/.test(lines[i])) {
      lastTableRowIdx = i;
    }
  }
  if (lastTableRowIdx === -1) {
    console.warn(`  _index.md のテーブル形式が想定外。手動で追記してください。`);
    return;
  }
  for (let i = 0; i < lines.length; i++) {
    out2.push(lines[i]);
    if (i === lastTableRowIdx) {
      // 既存の「| — | — | — | — | — |」プレースホルダ行は削除しない（オーナー判断に委ねる）
      out2.push(newRow);
    }
  }

  writeFileSync(CMO_INDEX, out2.join('\n'), 'utf-8');
  console.log(`  ✅ CMO/_index.md に追記: ${relPath}`);
}

// ─────────────────────────────────────────────
// メイン
// ─────────────────────────────────────────────
function main() {
  const args = parseArgs(process.argv.slice(2));

  if (args.help) { showHelp(); return; }
  if (args.list) { listTopics(); return; }

  if (!args.topic) {
    console.error('--topic <slug> を指定してください（--list で一覧表示）。');
    showHelp();
    process.exit(1);
  }

  const cfg = loadTopic(args.topic);
  validateTopic(cfg);

  const dateStr = today();
  const fileName = `${dateStr}_note集客記事_${cfg.slug}_input.md`;
  const outPath = join(CMO_RESEARCH, fileName);
  const content = buildScaffold(cfg, dateStr);

  if (args.dryRun) {
    console.log(`[DRY-RUN] 書き込み予定: ${outPath}`);
    console.log('---');
    console.log(content);
    console.log('---');
    console.log('[DRY-RUN] 実際のファイル書き込みはスキップしました。');
    return;
  }

  if (!existsSync(CMO_RESEARCH)) mkdirSync(CMO_RESEARCH, { recursive: true });
  if (existsSync(outPath)) {
    console.error(`既にファイルが存在します: ${outPath}`);
    console.error(`上書きする場合は手動で削除してから再実行してください。`);
    process.exit(1);
  }
  writeFileSync(outPath, content, 'utf-8');
  console.log(`✅ スキャフォルド生成: ${outPath}`);

  appendToIndex(cfg, dateStr, outPath);

  console.log('');
  console.log('次の手順:');
  console.log(`  1. ${outPath} を開く`);
  console.log(`  2. 「Claude Pro 用プロンプト全文」を Claude Pro チャットに貼る（費用：既存契約のみ）`);
  console.log(`  3. 出力を CMO/outputs/${dateStr}_note集客記事_${cfg.slug}.md に保存`);
}

main();
