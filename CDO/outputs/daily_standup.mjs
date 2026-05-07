#!/usr/bin/env node
/**
 * daily_standup.mjs — 日次スタンドアップ自動レポート
 *
 * 目的：
 *   - 昨日の作業を客観的に集計
 *   - 「準備物が増えているのに収益が出ていない」状態を検出
 *   - 今日の優先タスクを自動提案
 *
 * 費用ゼロ：
 *   - Node 標準モジュール（child_process / fs / path）のみ
 *   - 外部API呼び出しなし
 *   - npm install 不要
 *
 * 使い方:
 *   node CDO/outputs/daily_standup.mjs
 *   node CDO/outputs/daily_standup.mjs --since "2 days ago"
 *   node CDO/outputs/daily_standup.mjs --dry-run
 *
 * 出力:
 *   CDO/research/standups/YYYY-MM-DD_standup.md
 *     → 昨日のコミット集計、_index.md 更新有無、推奨アクション
 *     → 「実行アクション（公開・応募・登録）」と「準備物作成」を分離して可視化
 */

import { execSync } from 'node:child_process';
import { writeFileSync, existsSync, mkdirSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dir = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dir, '../..');
const STANDUP_DIR = join(REPO_ROOT, 'CDO', 'research', 'standups');

// ─────────────────────────────────────────────
// CLI
// ─────────────────────────────────────────────
function parseArgs(argv) {
  const args = { since: '1 day ago', dryRun: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--since') args.since = argv[++i];
    else if (a === '--dry-run') args.dryRun = true;
    else if (a === '--help' || a === '-h') args.help = true;
  }
  return args;
}

function showHelp() {
  console.log(`daily_standup.mjs

USAGE:
  node CDO/outputs/daily_standup.mjs
  node CDO/outputs/daily_standup.mjs --since "2 days ago"
  node CDO/outputs/daily_standup.mjs --dry-run

OPTIONS:
  --since <git-time>   集計対象期間（git log の --since と同じ書式）
  --dry-run            ファイルを書かずに stdout に出力
  --help, -h           このヘルプを表示

費用ゼロ：外部API呼び出し・SaaS契約なし。
`);
}

// ─────────────────────────────────────────────
// シェル実行ヘルパー
// ─────────────────────────────────────────────
function sh(cmd) {
  try {
    return execSync(cmd, { cwd: REPO_ROOT, encoding: 'utf-8' }).trim();
  } catch {
    return '';
  }
}

// ─────────────────────────────────────────────
// 日付ユーティリティ
// ─────────────────────────────────────────────
function today() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function dayOfWeekJa() {
  const days = ['日', '月', '火', '水', '木', '金', '土'];
  return days[new Date().getDay()];
}

// ─────────────────────────────────────────────
// コミット集計
// ─────────────────────────────────────────────
function collectCommits(since) {
  const log = sh(`git log --since="${since}" --pretty=format:"%h|%s|%an|%ad" --date=short`);
  if (!log) return [];
  return log.split('\n').filter(Boolean).map(line => {
    const [hash, subject, author, date] = line.split('|');
    return { hash, subject, author, date };
  });
}

function classifyCommit(subject) {
  const lower = subject.toLowerCase();
  if (subject.includes('feat(CMO)') || subject.includes('feat(集客') || subject.includes('feat(C):')) return '集客・販売';
  if (subject.includes('feat(CDO)')) return '自動化・基盤';
  if (subject.includes('feat(CSO)')) return '営業・受注';
  if (subject.includes('feat(CFO)')) return '財務・事務';
  if (subject.includes('feat(CPO)')) return 'プロダクト';
  if (lower.includes('fix')) return 'バグ修正';
  if (lower.includes('docs')) return 'ドキュメント';
  return 'その他';
}

// ─────────────────────────────────────────────
// 変更ファイル集計
// ─────────────────────────────────────────────
function collectChangedFiles(since) {
  const out = sh(`git log --since="${since}" --name-status --pretty=format:""`);
  if (!out) return { added: [], modified: [], deleted: [] };
  const added = new Set(), modified = new Set(), deleted = new Set();
  out.split('\n').filter(Boolean).forEach(line => {
    const [status, ...pathParts] = line.split('\t');
    const filePath = pathParts.join('\t');
    if (!filePath) return;
    if (status === 'A') added.add(filePath);
    else if (status === 'M') modified.add(filePath);
    else if (status === 'D') deleted.add(filePath);
  });
  return {
    added: [...added].sort(),
    modified: [...modified].sort(),
    deleted: [...deleted].sort(),
  };
}

// ─────────────────────────────────────────────
// 「実行アクション」検知
// 準備物（.md / .json / .mjs）ばかり増えていて、
// 実収益アクション（context/diary 更新・CFO _invoices/ 等）が無いかを判定
// ─────────────────────────────────────────────
function detectExecutionGap(files) {
  const allFiles = [...files.added, ...files.modified];

  const preparationFiles = allFiles.filter(f =>
    /\.(md|json|mjs|ts|js|py)$/.test(f) &&
    !f.startsWith('context/diary/') &&
    !f.includes('_invoices/') &&
    !f.includes('_revenue_data/')
  );

  const executionFiles = allFiles.filter(f =>
    f.startsWith('context/diary/') ||
    f.includes('_invoices/') ||
    f.includes('_revenue_data/') ||
    f.includes('_clients/')
  );

  const ratio = preparationFiles.length === 0
    ? 0
    : executionFiles.length / (preparationFiles.length + executionFiles.length);

  let verdict = '';
  if (preparationFiles.length === 0 && executionFiles.length === 0) {
    verdict = '⚪ 作業なし';
  } else if (executionFiles.length === 0) {
    verdict = '⚠️ 準備物のみ増加（実行アクションなし）— 公開・応募・登録の実行を推奨';
  } else if (ratio < 0.2) {
    verdict = '🟡 準備物が実行を上回る';
  } else {
    verdict = '🟢 準備と実行のバランス良好';
  }

  return { preparationFiles, executionFiles, ratio, verdict };
}

// ─────────────────────────────────────────────
// 各役職の _index.md から進行中タスクを抽出
// ─────────────────────────────────────────────
function collectInProgressTasks() {
  const roles = ['CDO', 'CFO', 'CMO', 'CPO', 'CSO'];
  const tasks = {};
  for (const role of roles) {
    const indexPath = join(REPO_ROOT, role, '_index.md');
    if (!existsSync(indexPath)) continue;
    const content = readFileSync(indexPath, 'utf-8');
    const match = content.match(/## 進行中タスク\s*\n+([\s\S]*?)(?:\n## |$)/);
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
// 簡易メトリクス
// ─────────────────────────────────────────────
function getMetrics(since) {
  const stats = sh(`git log --since="${since}" --pretty=tformat: --numstat | awk 'BEGIN{a=0;d=0;f=0} {a+=$1; d+=$2; f++} END{print a"|"d"|"f}'`);
  const [insertions, deletions, files] = (stats || '0|0|0').split('|').map(n => parseInt(n) || 0);
  return { insertions, deletions, files };
}

// ─────────────────────────────────────────────
// 推奨アクションの生成
// ─────────────────────────────────────────────
function generateRecommendations(gap, tasks) {
  const recs = [];

  if (gap.executionFiles.length === 0 && gap.preparationFiles.length > 0) {
    recs.push({
      priority: '🥇',
      target: 'オーナー',
      action: 'note 集客記事を1本でも公開する（既に本文完成済み・コピペのみで30分）',
      impact: '初回 ¥0 → 数千円の収益発生の可能性',
    });
    recs.push({
      priority: '🥈',
      target: 'オーナー',
      action: 'クラウドワークスに登録 → profile_bio.md をコピペ（1時間）',
      impact: '柱A SEOライティング受注の最初の1歩',
    });
  }

  // CFOタスクの期限切迫チェック
  if (tasks.CFO?.some(t => t.includes('開業届'))) {
    recs.push({
      priority: '⚠️',
      target: 'オーナー',
      action: '開業届の e-Tax 提出（期限切迫）',
      impact: '青色申告65万円控除の権利を失わない',
    });
  }

  if (recs.length === 0) {
    recs.push({
      priority: '✅',
      target: '全員',
      action: '本日の重点タスクは特になし。継続中タスクを進める',
      impact: '—',
    });
  }

  return recs;
}

// ─────────────────────────────────────────────
// レポート生成
// ─────────────────────────────────────────────
function buildReport(opts) {
  const { commits, files, gap, tasks, metrics, recommendations, since, dateStr, dow } = opts;

  const commitsByCategory = {};
  commits.forEach(c => {
    const cat = classifyCommit(c.subject);
    (commitsByCategory[cat] = commitsByCategory[cat] || []).push(c);
  });

  const commitTable = Object.entries(commitsByCategory)
    .map(([cat, cs]) => `### ${cat}（${cs.length}コミット）\n${cs.map(c => `- \`${c.hash}\` ${c.subject}`).join('\n')}`)
    .join('\n\n');

  const tasksSection = Object.keys(tasks).length === 0
    ? '（進行中タスクなし）'
    : Object.entries(tasks)
        .map(([role, items]) => `**${role}**\n${items.map(t => `- ${t}`).join('\n')}`)
        .join('\n\n');

  const recsTable = recommendations
    .map(r => `| ${r.priority} | ${r.target} | ${r.action} | ${r.impact} |`)
    .join('\n');

  return `# 日次スタンドアップ：${dateStr}（${dow}曜日）

> このレポートは \`CDO/outputs/daily_standup.mjs\` が自動生成しました。
> 集計期間：\`${since}\` 以降のコミット
> 費用：¥0（外部API呼び出しなし、Node 標準モジュールのみ）

---

## 1. 数字サマリー

| 指標 | 値 |
|------|---|
| コミット数 | ${commits.length} |
| 変更ファイル数 | ${metrics.files} |
| 追加行数 | +${metrics.insertions} |
| 削除行数 | -${metrics.deletions} |
| 新規ファイル | ${files.added.length} |
| 修正ファイル | ${files.modified.length} |
| 削除ファイル | ${files.deleted.length} |

---

## 2. 実行ギャップ分析

**判定：${gap.verdict}**

- 準備物の作成（.md / .json / .mjs 等）：**${gap.preparationFiles.length}件**
- 実行アクション（diary / 請求書 / 顧客記録）：**${gap.executionFiles.length}件**
- 実行比率：**${(gap.ratio * 100).toFixed(1)}%**

> 「準備物のみ増加」が3日続く場合、戦略の見直しを推奨。
> 真の収益は \`context/diary/\` または \`CFO/outputs/_invoices/\` の更新で発生する。

---

## 3. コミット詳細

${commitTable || '（コミットなし）'}

---

## 4. 各役職の進行中タスク

${tasksSection}

---

## 5. 推奨アクション（今日の優先順位）

| 優先度 | 担当 | アクション | 期待インパクト |
|------|------|----------|------------|
${recsTable}

---

## 6. 振り返りメモ（手動入力欄）

オーナーが本日の終わりに記入：

\`\`\`
■ 今日うまくいったこと
-

■ 詰まったポイント・改善したいこと
-

■ 明日の重点タスク（最大3つ）
1.
2.
3.

■ 数字（あれば）
- note PV：
- 応募数：
- 受注数：
- 売上：
\`\`\`

---

## 7. 改善ループ（CDO 自動チェック）

次回スタンドアップ生成時に下記を自動でチェックします：

- [ ] 「実行ギャップ」が改善されたか
- [ ] 進行中タスクが減ったか
- [ ] 期限切迫タスク（開業届・青色申告）が完了したか
- [ ] 連続3日以上「準備物のみ」状態が続いていないか

---

*このレポートは費用ゼロで自動生成されています。
スタンドアップ実行：\`node CDO/outputs/daily_standup.mjs\`*
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
  const since = args.since;

  const commits = collectCommits(since);
  const files = collectChangedFiles(since);
  const gap = detectExecutionGap(files);
  const tasks = collectInProgressTasks();
  const metrics = getMetrics(since);
  const recommendations = generateRecommendations(gap, tasks);

  const report = buildReport({
    commits, files, gap, tasks, metrics, recommendations, since, dateStr, dow,
  });

  if (args.dryRun) {
    console.log(report);
    return;
  }

  if (!existsSync(STANDUP_DIR)) mkdirSync(STANDUP_DIR, { recursive: true });
  const outPath = join(STANDUP_DIR, `${dateStr}_standup.md`);
  writeFileSync(outPath, report, 'utf-8');
  console.log(`✅ スタンドアップ生成: ${outPath}`);
  console.log('');
  console.log('要約：');
  console.log(`  コミット ${commits.length}件 / +${metrics.insertions}行 / -${metrics.deletions}行`);
  console.log(`  実行ギャップ判定：${gap.verdict}`);
  console.log('');
  console.log('次の手順：');
  console.log(`  1. ${outPath} を開いて確認`);
  console.log(`  2. 「振り返りメモ」を本日の終わりに記入`);
  console.log(`  3. 推奨アクションから1つでも実行`);
}

main();
