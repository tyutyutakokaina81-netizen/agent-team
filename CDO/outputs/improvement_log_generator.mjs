#!/usr/bin/env node
/**
 * improvement_log_generator.mjs — 日次改善ログの自動雛形生成
 *
 * 目的：
 *   - 毎日の改善ログ記入を「ゼロから書く」状態から「埋めるだけ」状態にする
 *   - 朝会・夕会・コミット履歴から自動抽出した文脈を雛形に反映
 *
 * 費用ゼロ：Node 標準モジュールのみ
 *
 * 使い方:
 *   node CDO/outputs/improvement_log_generator.mjs              # 当日分を生成
 *   node CDO/outputs/improvement_log_generator.mjs --dry-run    # 出力プレビュー
 *   node CDO/outputs/improvement_log_generator.mjs --force      # 既存ファイル上書き
 */

import { writeFileSync, existsSync, mkdirSync, readFileSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { today, dayOfWeekJa as dow, safe, sh as shBase } from './lib/pdca_lib.mjs';

const __dir = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dir, '../..');
const IMPROVEMENTS_DIR = join(REPO_ROOT, 'CDO', 'research', 'improvements');
const MEETINGS_DIR = join(REPO_ROOT, 'CDO', 'research', 'meetings');
const METRICS_FILE = join(REPO_ROOT, 'CFO', 'research', '_revenue_data', 'metrics.jsonl');

const sh = (cmd) => shBase(cmd, { cwd: REPO_ROOT });

function parseArgs(argv) {
  const a = { dryRun: false, force: false };
  for (const x of argv) {
    if (x === '--dry-run') a.dryRun = true;
    else if (x === '--force') a.force = true;
    else if (x === '--help' || x === '-h') a.help = true;
  }
  return a;
}

// 朝会から Top3 を抽出
function readMorningTop3() {
  return safe(() => {
    const path = join(MEETINGS_DIR, `${today()}_morning.md`);
    if (!existsSync(path)) return [];
    const content = readFileSync(path, 'utf-8');
    const top3 = [];
    const re = /### (.+?)\s+(.+?)\n/g;
    let m;
    let inSection = false;
    const lines = content.split('\n');
    for (let i = 0; i < lines.length; i++) {
      if (lines[i].includes('## 🎬 今日のTop3アクション')) inSection = true;
      else if (lines[i].startsWith('---') && inSection) inSection = false;
      else if (inSection && lines[i].startsWith('### ')) {
        const m = lines[i].match(/### (.+?)\s+(.+)/);
        if (m) top3.push({ priority: m[1], title: m[2] });
      }
    }
    return top3.slice(0, 3);
  }, []);
}

// 当日のコミット
function todayCommits() {
  const log = sh('git log --since="00:00" --pretty=format:"%h|%s"');
  return log
    ? log.split('\n').filter(Boolean).map(l => { const [h, s] = l.split('|'); return { hash: h, subject: s }; })
    : [];
}

// 当日の数字
function todayMetrics() {
  return safe(() => {
    if (!existsSync(METRICS_FILE)) return null;
    const lines = readFileSync(METRICS_FILE, 'utf-8').split('\n').filter(Boolean);
    const recs = lines.map(l => { try { return JSON.parse(l); } catch { return null; } }).filter(r => r && r.date === today());
    return recs.length > 0 ? recs[recs.length - 1] : null;
  }, null);
}

function buildLog({ dateStr, dowStr, top3, commits, metrics }) {
  const top3Section = top3.length === 0
    ? '（朝会未実行 or Top3 抽出失敗）'
    : top3.map((a, i) => `${i + 1}. ${a.priority} ${a.title}`).join('\n');

  const commitsSection = commits.length === 0
    ? '（本日コミットなし）'
    : commits.slice(0, 10).map(c => `- \`${c.hash}\` ${c.subject}`).join('\n');

  const metricsSection = metrics
    ? `応募${metrics.applications || 0}・受注${metrics.received || 0}・売上¥${(metrics.revenue_jpy || 0).toLocaleString()}`
    : '（数字未入力）';

  return `# 改善ログ：${dateStr}（${dowStr}）

> このファイルは \`CDO/outputs/improvement_log_generator.mjs\` が自動生成しました。
> 各セクションを5分で埋めてください。空欄でも当日の自動データは残ります。

## 自動データ（朝会・コミット・数字）

### 今日の Top3（朝会から）

${top3Section}

### 今日のコミット

${commitsSection}

### 今日の数字

${metricsSection}

---

## 1. 今日の作業から見えた「無駄・摩擦」

具体的に書く（抽象的な「効率化したい」ではなく、何が・なぜ・どれくらい）。

-
-

## 2. 改善案（小さく実行可能なもの）

完璧な改善ではなく、「今週中に試せる小さな1歩」を書く。

-
-

## 3. 実験：試したいアイデア

**仮説**と**検証方法**を書く。

- 仮説：
- 検証：

## 4. 削除・撤退の判断

「今やってる作業のうち、やめても支障ないもの」を書く。

-

## 5. 学び（成功・失敗の両方）

- 成功：
- 失敗：

## 6. 次の改善サイクル（明日／明後日に試すこと）

最大3つに絞る。

1.
2.
3.

---

*この雛形は \`CDO/outputs/improvement_log_template.md\` に基づきます。*
*手動執筆もOK：\`CDO/research/improvements/${dateStr}_improvement.md\` を直接編集*
`;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    console.log('node CDO/outputs/improvement_log_generator.mjs [--dry-run] [--force]');
    return;
  }

  const dateStr = today();
  const outPath = join(IMPROVEMENTS_DIR, `${dateStr}_improvement.md`);

  if (existsSync(outPath) && !args.force && !args.dryRun) {
    console.log(`✅ 既に存在：${outPath}`);
    console.log('   上書きする場合：--force');
    return;
  }

  const top3 = readMorningTop3();
  const commits = todayCommits();
  const metrics = todayMetrics();

  const content = buildLog({ dateStr, dowStr: dow(), top3, commits, metrics });

  if (args.dryRun) {
    console.log(content);
    return;
  }

  if (!existsSync(IMPROVEMENTS_DIR)) mkdirSync(IMPROVEMENTS_DIR, { recursive: true });
  writeFileSync(outPath, content, 'utf-8');
  console.log(`✅ 改善ログ雛形生成: ${outPath}`);
  console.log('');
  console.log('   - 朝会 Top3 / コミット / 数字 は自動で埋まっています');
  console.log('   - 残り 6セクションを5分で埋めてください');
}

main();
