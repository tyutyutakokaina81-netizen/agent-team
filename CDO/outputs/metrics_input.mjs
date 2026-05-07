#!/usr/bin/env node
/**
 * metrics_input.mjs — 数字を CLI で入力（git 外作業の検知補完）
 *
 * 目的：
 *   - 応募数・受注数・売上・note PV 等の Git 外作業を手動で記録
 *   - PDCA の「Check」フェーズで実態を把握
 *   - 朝会の「Top3 動的生成」が数字を参照できるようにする
 *
 * 費用ゼロ：Node 標準モジュール（readline）のみ
 *
 * 使い方:
 *   node CDO/outputs/metrics_input.mjs                     # 対話入力
 *   node CDO/outputs/metrics_input.mjs --quick             # 0埋めスキップで早く
 *   node CDO/outputs/metrics_input.mjs --show              # 直近の数字を表示
 *   node CDO/outputs/metrics_input.mjs --json              # JSON で出力
 *
 * 保存先：
 *   CFO/research/_revenue_data/metrics.jsonl   ← gitignore 対象（実数字）
 *   CFO/outputs/metrics_summary.md             ← 集計サマリ（公開可）
 */

import { readFileSync, writeFileSync, appendFileSync, existsSync, mkdirSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import readline from 'node:readline';
import { today } from './lib/pdca_lib.mjs';

const __dir = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dir, '../..');
const DATA_DIR = join(REPO_ROOT, 'CFO', 'research', '_revenue_data');
const DATA_FILE = join(DATA_DIR, 'metrics.jsonl');
const SUMMARY_FILE = join(REPO_ROOT, 'CFO', 'outputs', 'metrics_summary.md');

const FIELDS = [
  { key: 'applications', label: '柱A 応募数（クラウドワークス・ランサーズ）', unit: '件', type: 'int' },
  { key: 'received', label: '柱A 受注数', unit: '件', type: 'int' },
  { key: 'delivered', label: '柱A 納品完了数', unit: '件', type: 'int' },
  { key: 'revenue_jpy', label: '本日の売上（税込）', unit: '円', type: 'int' },
  { key: 'note_pv', label: 'note 記事 PV 合計', unit: 'PV', type: 'int' },
  { key: 'note_likes', label: 'note スキ数（合計）', unit: 'スキ', type: 'int' },
  { key: 'template_sales', label: 'テンプレ販売数（Vol合計）', unit: '本', type: 'int' },
  { key: 'memo', label: '本日のメモ（自由記述・Enter スキップ）', unit: '', type: 'text' },
];

// ─────────────────────────────────────────────
// CLI
// ─────────────────────────────────────────────
function parseArgs(argv) {
  const args = { quick: false, show: false, json: false };
  for (const a of argv) {
    if (a === '--quick') args.quick = true;
    else if (a === '--show') args.show = true;
    else if (a === '--json') args.json = true;
    else if (a === '--help' || a === '-h') args.help = true;
  }
  return args;
}

function showHelp() {
  console.log(`metrics_input.mjs — 数字入力 CLI

USAGE:
  node CDO/outputs/metrics_input.mjs           対話で入力
  node CDO/outputs/metrics_input.mjs --quick   0埋めスキップで早く
  node CDO/outputs/metrics_input.mjs --show    直近を表示
  node CDO/outputs/metrics_input.mjs --json    JSON 出力

費用ゼロ：標準入力のみ、外部API呼び出しなし。
`);
}

// ─────────────────────────────────────────────
// ストレージ操作
// ─────────────────────────────────────────────
function loadAll() {
  if (!existsSync(DATA_FILE)) return [];
  return readFileSync(DATA_FILE, 'utf-8')
    .split('\n')
    .filter(Boolean)
    .map(l => { try { return JSON.parse(l); } catch { return null; } })
    .filter(Boolean);
}

function appendRecord(record) {
  if (!existsSync(DATA_DIR)) mkdirSync(DATA_DIR, { recursive: true });
  appendFileSync(DATA_FILE, JSON.stringify(record) + '\n', 'utf-8');
}

// ─────────────────────────────────────────────
// 対話入力
// ─────────────────────────────────────────────
function prompt(rl, question) {
  return new Promise(resolve => rl.question(question, resolve));
}

async function interactive(quick) {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  const record = { date: today(), recorded_at: new Date().toISOString() };

  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━');
  console.log(`📊 数字入力：${today()}`);
  console.log('━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('（Enter で 0 / スキップ）\n');

  for (const f of FIELDS) {
    const ans = (await prompt(rl, `${f.label}（${f.unit}）: `)).trim();
    if (f.type === 'int') {
      record[f.key] = ans === '' ? 0 : parseInt(ans) || 0;
    } else {
      record[f.key] = ans;
    }
  }

  rl.close();
  appendRecord(record);
  return record;
}

async function quick() {
  // 全部 0 で作成、メモのみ対話
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  const record = { date: today(), recorded_at: new Date().toISOString() };
  for (const f of FIELDS) {
    record[f.key] = f.type === 'int' ? 0 : '';
  }
  const memo = (await prompt(rl, '本日のメモ（任意）: ')).trim();
  record.memo = memo;
  rl.close();
  appendRecord(record);
  return record;
}

// ─────────────────────────────────────────────
// 集計サマリ生成
// ─────────────────────────────────────────────
function generateSummary() {
  const all = loadAll();
  if (all.length === 0) return;

  const recent7 = all.slice(-7);
  const recent30 = all.slice(-30);

  const sum = (arr, key) => arr.reduce((s, r) => s + (r[key] || 0), 0);

  const summary = `# 数字サマリ（自動生成）

> このファイルは \`CDO/outputs/metrics_input.mjs\` が自動生成しました。
> 生データは \`CFO/research/_revenue_data/metrics.jsonl\`（gitignore 対象）に保管。
> 本ファイルには **集計値のみ** を載せ、Git に乗せて朝会等で参照可能にしています。

最終更新：${today()}

## 直近30日 累計

| 指標 | 7日累計 | 30日累計 |
|------|--------|---------|
| 応募数 | ${sum(recent7, 'applications')} | ${sum(recent30, 'applications')} |
| 受注数 | ${sum(recent7, 'received')} | ${sum(recent30, 'received')} |
| 納品数 | ${sum(recent7, 'delivered')} | ${sum(recent30, 'delivered')} |
| 売上（円） | ${sum(recent7, 'revenue_jpy').toLocaleString()} | ${sum(recent30, 'revenue_jpy').toLocaleString()} |
| note PV | ${sum(recent7, 'note_pv')} | ${sum(recent30, 'note_pv')} |
| note スキ | ${sum(recent7, 'note_likes')} | ${sum(recent30, 'note_likes')} |
| テンプレ販売 | ${sum(recent7, 'template_sales')} | ${sum(recent30, 'template_sales')} |

## 達成率（30日目標 vs 実績）

| 指標 | 30日累計 | 目標 | 達成率 |
|------|---------|------|-------|
| 応募数 | ${sum(recent30, 'applications')} | 100 | ${Math.round(sum(recent30, 'applications') / 100 * 100)}% |
| 受注数 | ${sum(recent30, 'received')} | 8 | ${Math.round(sum(recent30, 'received') / 8 * 100)}% |
| 売上（円） | ${sum(recent30, 'revenue_jpy').toLocaleString()} | 40,000 | ${Math.round(sum(recent30, 'revenue_jpy') / 40000 * 100)}% |

## 直近の入力

${recent7.slice(-5).reverse().map(r =>
  `- **${r.date}**: 応募${r.applications}・受注${r.received}・売上¥${(r.revenue_jpy || 0).toLocaleString()}` +
  (r.memo ? `\n  > ${r.memo}` : '')
).join('\n')}

---

## 入力方法

\`\`\`bash
node CDO/outputs/metrics_input.mjs           # 対話で全項目
node CDO/outputs/metrics_input.mjs --quick   # メモのみ・他は0
\`\`\`

## 運用コスト

| 項目 | 金額 |
|------|------|
| 入力ツール | ¥0（Node 標準の readline） |
| 保存（jsonl） | ¥0 |
| **追加発生コスト** | **¥0** |
`;

  writeFileSync(SUMMARY_FILE, summary, 'utf-8');
}

// ─────────────────────────────────────────────
// メイン
// ─────────────────────────────────────────────
async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) { showHelp(); return; }

  if (args.show) {
    const all = loadAll().slice(-7);
    if (all.length === 0) { console.log('（記録なし）'); return; }
    console.log('直近7日：');
    for (const r of all) {
      console.log(`  ${r.date}: 応募${r.applications}/受注${r.received}/売上¥${(r.revenue_jpy || 0).toLocaleString()}`);
    }
    return;
  }

  if (args.json) {
    console.log(JSON.stringify(loadAll(), null, 2));
    return;
  }

  let record;
  if (args.quick) record = await quick();
  else record = await interactive(false);

  generateSummary();

  console.log('');
  console.log(`✅ 記録完了：${DATA_FILE.replace(REPO_ROOT + '/', '')}`);
  console.log(`✅ サマリ更新：${SUMMARY_FILE.replace(REPO_ROOT + '/', '')}`);
  console.log('');
  console.log(`本日：応募${record.applications}・受注${record.received}・売上¥${(record.revenue_jpy || 0).toLocaleString()}`);
}

main().catch(e => { console.error(e); process.exit(1); });
