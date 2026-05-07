#!/usr/bin/env node
/**
 * evening_checkin.mjs — 夕方のチェックイン（PDCA: Check + Act）
 *
 * 目的：
 *   - 朝の戦略会議 Top3 が実行されたかを評価
 *   - 改善メモを残し、明日の朝会に反映
 *   - スタンドアップを自動生成（昨日との比較）
 *
 * 費用ゼロ：Node 標準モジュールのみ
 *
 * 使い方:
 *   node CDO/outputs/evening_checkin.mjs
 *   node CDO/outputs/evening_checkin.mjs --dry-run
 *
 * 出力:
 *   CDO/research/checkins/YYYY-MM-DD_evening.md
 *   CDO/research/standups/YYYY-MM-DD_standup.md（標準スタンドアップも自動更新）
 */

import { execSync } from 'node:child_process';
import { writeFileSync, existsSync, mkdirSync, readFileSync, readdirSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dir = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dir, '../..');
const CHECKINS_DIR = join(REPO_ROOT, 'CDO', 'research', 'checkins');
const MEETINGS_DIR = join(REPO_ROOT, 'CDO', 'research', 'meetings');
const STANDUP_SCRIPT = join(REPO_ROOT, 'CDO', 'outputs', 'daily_standup.mjs');

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
  console.log(`evening_checkin.mjs — 夕方のチェックイン（PDCA: Check + Act）

USAGE:
  node CDO/outputs/evening_checkin.mjs
  node CDO/outputs/evening_checkin.mjs --dry-run

費用ゼロ：外部API呼び出しなし。
`);
}

// ─────────────────────────────────────────────
// ユーティリティ
// ─────────────────────────────────────────────
function sh(cmd, opts = {}) {
  try { return execSync(cmd, { cwd: REPO_ROOT, encoding: 'utf-8', ...opts }).trim(); }
  catch { return ''; }
}

function today() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function dayOfWeekJa() {
  return ['日', '月', '火', '水', '木', '金', '土'][new Date().getDay()];
}

// ─────────────────────────────────────────────
// 今朝の戦略会議を読む
// ─────────────────────────────────────────────
function readTodayMorningMeeting() {
  const path = join(MEETINGS_DIR, `${today()}_morning.md`);
  if (!existsSync(path)) return null;
  const content = readFileSync(path, 'utf-8');
  const top3 = [];
  const re = /### (.+?)\s+(.+?)\n+- \*\*担当\*\*：(.+?)\n- \*\*時間枠\*\*：(.+?)\n- \*\*詳細\*\*：(.+?)\n- \*\*達成基準\*\*：(.+?)(?=\n)/g;
  let m;
  while ((m = re.exec(content)) !== null) {
    top3.push({
      priority: m[1],
      title: m[2],
      target: m[3],
      time: m[4],
      detail: m[5],
      success: m[6],
    });
  }
  return { path: path.replace(REPO_ROOT + '/', ''), top3 };
}

// ─────────────────────────────────────────────
// 今日のコミットから「実行」を検知
// ─────────────────────────────────────────────
function detectExecutionToday() {
  const log = sh('git log --since="00:00" --pretty=format:"%h|%s"');
  if (!log) return { commits: [], hasExecution: false };
  const commits = log.split('\n').filter(Boolean).map(l => {
    const [hash, subject] = l.split('|');
    return { hash, subject };
  });
  // 「実行アクション」の検知：context/diary, _invoices, _clients 系のファイル
  const files = sh('git log --since="00:00" --name-only --pretty=format:""').split('\n').filter(Boolean);
  const executionFiles = files.filter(f =>
    f.startsWith('context/diary/') ||
    f.includes('_invoices/') ||
    f.includes('_revenue_data/') ||
    f.includes('_clients/')
  );
  return {
    commits,
    files,
    executionFiles,
    hasExecution: executionFiles.length > 0,
  };
}

// ─────────────────────────────────────────────
// スタンドアップを自動生成
// ─────────────────────────────────────────────
function runStandup() {
  if (!existsSync(STANDUP_SCRIPT)) return false;
  try {
    sh(`node ${STANDUP_SCRIPT}`, { stdio: 'inherit' });
    return true;
  } catch {
    return false;
  }
}

// ─────────────────────────────────────────────
// チェックイン本文生成
// ─────────────────────────────────────────────
function buildCheckin(opts) {
  const { dateStr, dow, morning, execution } = opts;

  const top3Section = !morning || morning.top3.length === 0
    ? '_朝会レポートが見つからないか Top3 抽出失敗_'
    : morning.top3.map((a, i) => `### ${i + 1}. ${a.priority} ${a.title}\n\n- 担当：${a.target}\n- 達成基準：${a.success}\n- **実行できた？** [ ] はい / [ ] 部分的 / [ ] 未着手\n- **数字や成果**（記入）：\n- **次の改善**（記入）：`).join('\n\n');

  const commitsSection = execution.commits.length === 0
    ? '_本日のコミットなし_'
    : execution.commits.map(c => `- \`${c.hash}\` ${c.subject}`).join('\n');

  const verdict = execution.hasExecution
    ? '🟢 実行アクションあり（ファイル：' + execution.executionFiles.join(', ') + '）'
    : '🟡 準備物のみ（実行アクションなし）';

  return `# 夕方チェックイン：${dateStr}（${dow}曜日）

> このレポートは \`CDO/outputs/evening_checkin.mjs\` が自動生成しました。
> 5分で記入し、明日の朝会に反映します。
> 費用：¥0

---

## 1. 朝会の Top3 振り返り（PDCA: Check）

朝会レポート：${morning ? `\`${morning.path}\`` : 'なし'}

${top3Section}

---

## 2. 本日の事実

- **本日の実行判定**：${verdict}
- **本日のコミット数**：${execution.commits.length}件
- **コミット詳細**：

${commitsSection}

---

## 3. 「やったこと vs やらなかったこと」（PDCA: Check）

### ✅ やった
- _記入_

### ❌ やらなかった（と理由）
- _記入_

### 🤔 想定外（良くも悪くも）
- _記入_

---

## 4. 改善（PDCA: Act）

明日に持ち越す改善ポイント。最大3つ。

```
1.
2.
3.
```

→ 上記を別途 \`CDO/research/improvements/${dateStr}_improvement.md\` にも転記推奨。

---

## 5. 数字ログ

| 指標 | 本日 | 月累計 |
|------|------|-------|
| 応募数（柱A） | | |
| 受注数 | | |
| 売上（円） | | |
| note PV | | |
| note公開数 | | |

→ 月初比較は週次レトロで実施。

---

## 6. 明日の朝会への申し送り

- **明日の Top3 案**（参考になる場合）：
  1.
  2.
  3.

- **戦略変更が必要か？**
  □ 不要（現戦略継続）
  □ 必要（理由：）

- **オーナーへの相談事項**：
  -

---

## 7. PDCA サイクルの完成

```
今朝の Plan/Do        ✅ 完了
今夕の Check/Act      ⏳ 記入中
明日の朝会で反映      → morning_meeting.mjs が自動取り込み
```

夕方に5分の記入で、PDCAが回ります。
記入忘れの日があってもOK（過剰負荷を避ける）。
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

  console.log('━━━━━━━━━━━━━━━━━━━━━━━');
  console.log(`🌆 ${dateStr}（${dow}）の夕方チェックイン`);
  console.log('━━━━━━━━━━━━━━━━━━━━━━━');

  const morning = readTodayMorningMeeting();
  const execution = detectExecutionToday();

  const report = buildCheckin({ dateStr, dow, morning, execution });

  if (args.dryRun) {
    console.log(report);
    return;
  }

  if (!existsSync(CHECKINS_DIR)) mkdirSync(CHECKINS_DIR, { recursive: true });
  const outPath = join(CHECKINS_DIR, `${dateStr}_evening.md`);
  writeFileSync(outPath, report, 'utf-8');
  console.log(`✅ 夕方チェックイン生成: ${outPath}`);

  // 標準スタンドアップも自動更新
  console.log('');
  console.log('▼ スタンドアップも更新します');
  runStandup();

  console.log('');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━');
  console.log(`📊 本日の判定：${execution.hasExecution ? '🟢 実行あり' : '🟡 準備物のみ'}`);
  console.log(`   コミット数：${execution.commits.length}件`);
  console.log('');
  console.log('次の手順：');
  console.log(`  1. ${outPath} を開いて記入（5分）`);
  console.log(`  2. 改善ログも更新：CDO/research/improvements/${dateStr}_improvement.md`);
  console.log(`  3. 明日朝：node CDO/outputs/morning_meeting.mjs`);
}

main();
