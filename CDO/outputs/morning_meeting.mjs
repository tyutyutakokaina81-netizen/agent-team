#!/usr/bin/env node
/**
 * morning_meeting.mjs — 朝の戦略会議 自動生成（PDCA: Plan + Do）
 *
 * 目的：
 *   - 毎朝1分で読める、今日の戦略会議サマリーを生成
 *   - 昨日の実績(Check)・改善メモ(Act)を踏まえ、今日の3アクション(Plan)を提示
 *   - 戦略文書（projects/.../strategy_review_*.md）と整合
 *
 * 費用ゼロ：
 *   - Node 標準モジュールのみ、外部API呼び出しなし
 *
 * 使い方:
 *   node CDO/outputs/morning_meeting.mjs
 *   node CDO/outputs/morning_meeting.mjs --dry-run
 *
 * 出力:
 *   CDO/research/meetings/YYYY-MM-DD_morning.md
 */

import { execSync } from 'node:child_process';
import { writeFileSync, existsSync, mkdirSync, readFileSync, readdirSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dir = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dir, '../..');
const MEETINGS_DIR = join(REPO_ROOT, 'CDO', 'research', 'meetings');
const STANDUPS_DIR = join(REPO_ROOT, 'CDO', 'research', 'standups');
const IMPROVEMENTS_DIR = join(REPO_ROOT, 'CDO', 'research', 'improvements');
const PROJECT_DIR = join(REPO_ROOT, 'projects');

// ─────────────────────────────────────────────
// CLI
// ─────────────────────────────────────────────
function parseArgs(argv) {
  const args = { dryRun: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--dry-run') args.dryRun = true;
    else if (a === '--help' || a === '-h') args.help = true;
  }
  return args;
}

function showHelp() {
  console.log(`morning_meeting.mjs — 朝の戦略会議 自動生成

USAGE:
  node CDO/outputs/morning_meeting.mjs
  node CDO/outputs/morning_meeting.mjs --dry-run

費用ゼロ：外部API呼び出しなし、Node標準モジュールのみ。
`);
}

// ─────────────────────────────────────────────
// ユーティリティ
// ─────────────────────────────────────────────
function sh(cmd) {
  try { return execSync(cmd, { cwd: REPO_ROOT, encoding: 'utf-8' }).trim(); }
  catch { return ''; }
}

function today() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function yesterday() {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function dayOfWeekJa() {
  return ['日', '月', '火', '水', '木', '金', '土'][new Date().getDay()];
}

// ─────────────────────────────────────────────
// 直近の戦略文書を取得
// ─────────────────────────────────────────────
function getLatestStrategyDoc() {
  const candidates = [];
  function scan(dir) {
    if (!existsSync(dir)) return;
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const full = join(dir, entry.name);
      if (entry.isDirectory()) scan(full);
      else if (entry.name.startsWith('strategy_review_') && entry.name.endsWith('.md')) {
        candidates.push(full);
      }
    }
  }
  scan(PROJECT_DIR);
  if (candidates.length === 0) return null;
  candidates.sort();
  return candidates[candidates.length - 1];
}

function extractStrategySummary(strategyPath) {
  if (!strategyPath || !existsSync(strategyPath)) return null;
  const content = readFileSync(strategyPath, 'utf-8');
  const titleMatch = content.match(/^# (.+)/m);
  const recommendMatch = content.match(/推奨戦略「([^」]+)」/);
  const recommendBlockMatch = content.match(/# Part 4：推奨戦略[^\n]*\n+([\s\S]*?)(?=\n# Part)/);
  return {
    path: strategyPath.replace(REPO_ROOT + '/', ''),
    title: titleMatch ? titleMatch[1] : '不明',
    recommended: recommendMatch ? recommendMatch[1] : null,
    summary: recommendBlockMatch ? recommendBlockMatch[1].slice(0, 600) : '',
  };
}

// ─────────────────────────────────────────────
// 昨日のスタンドアップを取得
// ─────────────────────────────────────────────
function getYesterdayStandup() {
  const path = join(STANDUPS_DIR, `${yesterday()}_standup.md`);
  if (!existsSync(path)) return null;
  const content = readFileSync(path, 'utf-8');
  const verdictMatch = content.match(/判定：(.+?)\*\*/);
  const commitsMatch = content.match(/コミット数 \| (\d+)/);
  return {
    path: path.replace(REPO_ROOT + '/', ''),
    verdict: verdictMatch ? verdictMatch[1].trim() : '不明',
    commits: commitsMatch ? parseInt(commitsMatch[1]) : 0,
  };
}

// ─────────────────────────────────────────────
// 直近の改善ログを取得
// ─────────────────────────────────────────────
function getRecentImprovements() {
  if (!existsSync(IMPROVEMENTS_DIR)) return [];
  const files = readdirSync(IMPROVEMENTS_DIR)
    .filter(f => f.endsWith('_improvement.md'))
    .sort()
    .slice(-3);
  return files.map(f => f.replace('_improvement.md', ''));
}

// ─────────────────────────────────────────────
// 各役職の進行中タスク
// ─────────────────────────────────────────────
function collectInProgressTasks() {
  const roles = ['CDO', 'CFO', 'CMO', 'CPO', 'CSO'];
  const tasks = {};
  for (const role of roles) {
    const indexPath = join(REPO_ROOT, role, '_index.md');
    if (!existsSync(indexPath)) continue;
    const content = readFileSync(indexPath, 'utf-8');
    const match = content.match(/## 進行中タスク\s*\n+([\s\S]*?)(?=\n## |$)/);
    if (!match) continue;
    const items = match[1]
      .split('\n')
      .map(l => l.trim())
      .filter(l => l.startsWith('- ') && !l.includes('（なし）'))
      .map(l => l.replace(/^- /, ''));
    if (items.length) tasks[role] = items;
  }
  return tasks;
}

// ─────────────────────────────────────────────
// 連続日数の検知（実行ギャップ警告）
// ─────────────────────────────────────────────
function getConsecutiveGapDays() {
  if (!existsSync(STANDUPS_DIR)) return 0;
  const files = readdirSync(STANDUPS_DIR)
    .filter(f => f.endsWith('_standup.md'))
    .sort()
    .reverse();
  let count = 0;
  for (const f of files) {
    const content = readFileSync(join(STANDUPS_DIR, f), 'utf-8');
    if (content.includes('準備物のみ増加')) count++;
    else break;
  }
  return count;
}

// ─────────────────────────────────────────────
// 直近24時間のコミット
// ─────────────────────────────────────────────
function recentCommitsCount() {
  return parseInt(sh(`git log --since="1 day ago" --oneline | wc -l`)) || 0;
}

// ─────────────────────────────────────────────
// 今日の Top3 アクション生成（戦略との整合）
// ─────────────────────────────────────────────
function generateTodayActions(strategy, gapDays, tasks) {
  const isStrategyA = strategy?.recommended?.includes('柱A集中') || strategy?.recommended?.includes('A：柱A');
  const actions = [];

  if (gapDays >= 3) {
    actions.push({
      priority: '🚨',
      target: 'オーナー',
      title: '【警告】3日以上「実行アクションなし」状態',
      time: '今すぐ',
      detail: '戦略文書（Part 8）を再読し、戦略の見直しまたは実行コミットを判断',
      success: '判断が決まった旨を改善ログに記入',
    });
  }

  if (isStrategyA) {
    // 戦略A 採用前提のアクション
    if (tasks.CSO?.some(t => t.includes('クラウドワークス'))) {
      actions.push({
        priority: '🥇',
        target: 'オーナー',
        title: 'クラウドワークス・ランサーズ登録',
        time: '午前9〜10時',
        detail: '`A_ライティング/templates/profile_bio.md` の本文をコピペ。本人確認まで完了',
        success: 'プロフィール完成度100%、認証マーク取得',
      });
    }
    actions.push({
      priority: '🥈',
      target: 'オーナー',
      title: '初応募 5件',
      time: '午前10〜11時',
      detail: '`job_evaluation_checklist.md` で80点以上の案件のみ。`application_messages.md` の業種別テンプレ使用',
      success: '応募実績スプレッドシートに5行追記',
    });
    actions.push({
      priority: '🥉',
      target: 'AI（Claude）',
      title: '夕方の振り返りで応募結果を集計',
      time: '夕方17時以降',
      detail: '`node CDO/outputs/evening_checkin.mjs` を実行',
      success: 'evening_checkin が生成される',
    });
  } else {
    actions.push({
      priority: '⚠️',
      target: 'オーナー',
      title: '戦略の意思決定',
      time: '本日中',
      detail: '`projects/.../strategy_review_*.md` の Part 8 で戦略A/B/C を選択',
      success: '戦略採用が確定し、後続アクションが定まる',
    });
  }

  if (actions.length === 0) {
    actions.push({
      priority: '✅',
      target: '全員',
      title: '進行中タスクの推進',
      time: '通常時間',
      detail: '各役職 _index.md の進行中タスクから1〜3件',
      success: 'タスク完了',
    });
  }

  return actions.slice(0, 3);
}

// ─────────────────────────────────────────────
// レポート生成
// ─────────────────────────────────────────────
function buildMeeting(opts) {
  const { strategy, standup, improvements, tasks, gapDays, commitsCount, dateStr, dow, todayActions } = opts;

  const tasksSection = Object.keys(tasks).length === 0
    ? '_（進行中タスクなし）_'
    : Object.entries(tasks)
        .map(([role, items]) => `**${role}**\n${items.map(t => `- ${t}`).join('\n')}`)
        .join('\n\n');

  const actionsTable = todayActions
    .map(a => `### ${a.priority} ${a.title}\n\n- **担当**：${a.target}\n- **時間枠**：${a.time}\n- **詳細**：${a.detail}\n- **達成基準**：${a.success}`)
    .join('\n\n');

  const gapWarning = gapDays >= 3
    ? `\n> 🚨 **警告：${gapDays}日連続で「準備物のみ増加」状態です。** 戦略の見直しが必要かもしれません。\n`
    : gapDays > 0
      ? `\n> ⚠️ ${gapDays}日連続で実行アクションが少ない状態です。\n`
      : '';

  return `# 朝の戦略会議：${dateStr}（${dow}曜日）

> このレポートは \`CDO/outputs/morning_meeting.mjs\` が自動生成しました。
> 1分で読んで、今日の3アクションを実行してください。
> 費用：¥0（外部API呼び出しなし）
${gapWarning}
---

## 🎯 今日のフォーカス（PDCA: Plan/Do）

### 戦略アライメント

${strategy ? `- **採用戦略**：${strategy.recommended || '未確定（要意思決定）'}\n- **戦略文書**：\`${strategy.path}\`` : '- 戦略文書なし。Part 1 から作成する必要あり'}

### 今日のTop3アクション

${actionsTable}

---

## 📊 昨日のチェック（PDCA: Check）

${standup
  ? `- **昨日のスタンドアップ判定**：${standup.verdict}\n- **昨日のコミット数**：${standup.commits}件\n- **詳細**：\`${standup.path}\``
  : '- 昨日のスタンドアップなし'
}

- **直近24時間のコミット数**：${commitsCount}件

---

## 📝 直近の改善メモ（PDCA: Act）

${improvements.length === 0
  ? '- _改善ログなし。今日から `improvement_log_template.md` で記入を習慣化推奨_'
  : improvements.map(d => `- \`CDO/research/improvements/${d}_improvement.md\``).join('\n')
}

---

## 🔄 進行中タスク（参考）

${tasksSection}

---

## 🎬 今日のルーティン

\`\`\`
07:30  この朝会レポートを読む（5分）
09:00  Top3 アクション開始（オーナー側）
17:00  夕方チェックイン実行：node CDO/outputs/evening_checkin.mjs
21:00  改善ログ記入（5分・任意）
\`\`\`

---

## 📚 リファレンス

- 戦略文書：\`projects/2026-04-08_月30万自動化/strategy_review_2026-05-07.md\`
- 応募ツール：\`projects/2026-04-08_月30万自動化/A_ライティング/templates/\`
- 改善テンプレ：\`CDO/outputs/improvement_log_template.md\`
- 週次レトロ：\`CDO/outputs/weekly_retrospective.md\`

---

*次の朝会自動生成：明日の朝（cron / launchd 設定済みなら自動）*
*手動実行：\`node CDO/outputs/morning_meeting.mjs\`*
`;
}

// ─────────────────────────────────────────────
// メイン
// ─────────────────────────────────────────────
function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) { showHelp(); return; }

  const dateStr = today();
  const dow = dayOfWeekJa();

  const strategy = extractStrategySummary(getLatestStrategyDoc());
  const standup = getYesterdayStandup();
  const improvements = getRecentImprovements();
  const tasks = collectInProgressTasks();
  const gapDays = getConsecutiveGapDays();
  const commitsCount = recentCommitsCount();
  const todayActions = generateTodayActions(strategy, gapDays, tasks);

  const report = buildMeeting({
    strategy, standup, improvements, tasks, gapDays, commitsCount,
    dateStr, dow, todayActions,
  });

  if (args.dryRun) {
    console.log(report);
    return;
  }

  if (!existsSync(MEETINGS_DIR)) mkdirSync(MEETINGS_DIR, { recursive: true });
  const outPath = join(MEETINGS_DIR, `${dateStr}_morning.md`);
  writeFileSync(outPath, report, 'utf-8');

  console.log(`✅ 朝会レポート生成: ${outPath}`);
  console.log('');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━');
  console.log(`📅 ${dateStr}（${dow}）の朝会`);
  console.log('━━━━━━━━━━━━━━━━━━━━━━━');
  if (gapDays >= 3) {
    console.log(`🚨 警告：${gapDays}日連続で実行ギャップ`);
  }
  console.log(`🎯 戦略：${strategy?.recommended || '未確定'}`);
  console.log(`📊 直近24時間コミット：${commitsCount}件`);
  console.log('');
  console.log('今日のTop3：');
  todayActions.forEach((a, i) => {
    console.log(`  ${a.priority} ${a.title} (${a.target})`);
  });
  console.log('');
  console.log('次の手順：');
  console.log(`  1. ${outPath} を開いて確認（1分）`);
  console.log(`  2. Top3を順に実行`);
  console.log(`  3. 夕方に：node CDO/outputs/evening_checkin.mjs`);
}

main();
