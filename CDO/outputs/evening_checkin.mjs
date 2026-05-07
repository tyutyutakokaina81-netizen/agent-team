#!/usr/bin/env node
/**
 * evening_checkin.mjs — 夕方のチェックイン v2（PDCA: Check + Act）
 *
 * v2 改善点：
 *   #7 PDCA スキップ検知：朝会未実行を警告
 *   #8 数字入力との連携：metrics_input.mjs を呼ぶよう誘導
 *   #12 跨日整合性：今朝の Top3 と本日コミットを突合
 *   通知：チェックイン生成完了で通知
 *
 * 費用ゼロ：Node 標準モジュール + 既存 notify.mjs
 */

import { writeFileSync, existsSync, mkdirSync, readFileSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { notify } from './notify.mjs';
import { today, dayOfWeekJa, safe, sh as shBase } from './lib/pdca_lib.mjs';

const __dir = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dir, '../..');
const CHECKINS_DIR = join(REPO_ROOT, 'CDO', 'research', 'checkins');
const MEETINGS_DIR = join(REPO_ROOT, 'CDO', 'research', 'meetings');
const STANDUP_SCRIPT = join(REPO_ROOT, 'CDO', 'outputs', 'daily_standup.mjs');
const METRICS_FILE = join(REPO_ROOT, 'CFO', 'research', '_revenue_data', 'metrics.jsonl');

const sh = (cmd, opts = {}) => shBase(cmd, { cwd: REPO_ROOT, ...opts });

function parseArgs(argv) {
  const args = { dryRun: false, notify: true };
  for (const a of argv) {
    if (a === '--dry-run') args.dryRun = true;
    else if (a === '--no-notify') args.notify = false;
    else if (a === '--help' || a === '-h') args.help = true;
  }
  return args;
}

// 今朝の戦略会議を読む
function readTodayMorningMeeting() {
  return safe(() => {
    const path = join(MEETINGS_DIR, `${today()}_morning.md`);
    if (!existsSync(path)) return null;
    const content = readFileSync(path, 'utf-8');
    const top3 = [];
    const re = /### (.+?)\s+(.+?)\n+- \*\*担当\*\*：(.+?)\n- \*\*時間枠\*\*：(.+?)\n- \*\*詳細\*\*：(.+?)\n- \*\*達成基準\*\*：(.+?)(?=\n)/g;
    let m;
    while ((m = re.exec(content)) !== null) {
      top3.push({
        priority: m[1], title: m[2], target: m[3],
        time: m[4], detail: m[5], success: m[6],
      });
    }
    return { path: path.replace(REPO_ROOT + '/', ''), top3 };
  }, null);
}

// 本日の実行を検知（git log 1回でコミット情報＋ファイル一覧を取得）
function detectExecutionToday() {
  // %x00 区切り＋--name-only で1コマンドにまとめる
  const raw = sh('git log --since="00:00" --name-only --pretty=format:"%x00COMMIT%x00%h|%s"');
  const commits = [];
  const files = new Set();
  if (raw) {
    for (const block of raw.split('\x00COMMIT\x00').filter(Boolean)) {
      const lines = block.split('\n').filter(Boolean);
      if (lines.length === 0) continue;
      const [hash, subject] = lines[0].split('|');
      commits.push({ hash, subject });
      lines.slice(1).forEach(f => files.add(f));
    }
  }
  const fileList = [...files];
  const executionFiles = fileList.filter(f =>
    f.startsWith('context/diary/') ||
    f.includes('_invoices/') ||
    f.includes('_revenue_data/') ||
    f.includes('_clients/')
  );
  return { commits, files: fileList, executionFiles, hasExecution: executionFiles.length > 0 };
}

// #12 跨日整合性：今朝のTop3が本日のコミット/数字に反映されたか
function evaluateTop3Alignment(morning, execution, todayMetrics) {
  if (!morning || morning.top3.length === 0) return [];
  return morning.top3.map(action => {
    const titleLower = action.title.toLowerCase();
    let likelyDone = false;
    let evidence = '';

    // ヒューリスティック：応募・受注・公開系のアクションは数字で判定
    if (titleLower.includes('応募') && todayMetrics.applications > 0) {
      likelyDone = true;
      evidence = `本日応募 ${todayMetrics.applications}件`;
    } else if (titleLower.includes('受注') && todayMetrics.received > 0) {
      likelyDone = true;
      evidence = `本日受注 ${todayMetrics.received}件`;
    } else if (titleLower.includes('登録') && execution.commits.length > 0) {
      // コミットでなく外部作業のため、自動判定不可
      evidence = '外部作業のため要オーナー記入';
    } else if (action.target === 'AI' && execution.commits.some(c => c.subject.includes('チェックイン'))) {
      likelyDone = true;
      evidence = '夕方チェックインを実行中';
    }

    return {
      ...action,
      likelyDone,
      evidence,
    };
  });
}

// 本日の数字（直近1日分）
function loadTodayMetrics() {
  return safe(() => {
    if (!existsSync(METRICS_FILE)) return { applications: 0, received: 0, revenue_jpy: 0 };
    const lines = readFileSync(METRICS_FILE, 'utf-8').split('\n').filter(Boolean);
    const todayRecords = lines
      .map(l => { try { return JSON.parse(l); } catch { return null; } })
      .filter(r => r && r.date === today());
    if (todayRecords.length === 0) return { applications: 0, received: 0, revenue_jpy: 0 };
    const last = todayRecords[todayRecords.length - 1];
    return last;
  }, { applications: 0, received: 0, revenue_jpy: 0 });
}

// #7 朝会のスキップ検知
function checkMorningMeetingExists() {
  return existsSync(join(MEETINGS_DIR, `${today()}_morning.md`));
}

// スタンドアップ自動実行
function runStandup() {
  if (!existsSync(STANDUP_SCRIPT)) return false;
  return safe(() => { sh(`node ${STANDUP_SCRIPT}`, { stdio: 'inherit' }); return true; }, false);
}

// チェックイン生成
function buildCheckin(opts) {
  const { dateStr, dow, morning, execution, alignment, todayMetrics, morningSkipped } = opts;

  const skipWarning = morningSkipped
    ? '\n> ⚠️ **本日の朝会未実行**：明朝は必ず `node CDO/outputs/morning_meeting.mjs` で開始しましょう。\n'
    : '';

  const top3Section = !morning || morning.top3.length === 0
    ? '_今朝の朝会レポートが見つかりません_'
    : alignment.map((a, i) => {
        const status = a.likelyDone ? '🟢 達成' : a.evidence ? '🟡 記入待ち' : '⚪ 未確認';
        return `### ${i + 1}. ${a.priority} ${a.title}\n\n- **担当**：${a.target}\n- **達成基準**：${a.success}\n- **自動判定**：${status} ${a.evidence ? `（${a.evidence}）` : ''}\n- **オーナー記入**：[ ] 完了 / [ ] 部分的 / [ ] 未着手\n- **数字や成果**：\n- **次の改善**：`;
      }).join('\n\n');

  const commitsSection = execution.commits.length === 0
    ? '_本日のコミットなし_'
    : execution.commits.map(c => `- \`${c.hash}\` ${c.subject}`).join('\n');

  const verdict = execution.hasExecution
    ? '🟢 実行アクションあり'
    : '🟡 準備物のみ（要数字入力で実態把握）';

  return `# 夕方チェックイン：${dateStr}（${dow}曜日）v2

> このレポートは \`CDO/outputs/evening_checkin.mjs\` v2 が自動生成しました。
> 5分で記入し、明朝の朝会に反映します。
> 費用：¥0
${skipWarning}
---

## 1. 朝会 Top3 の達成度（PDCA: Check）

朝会レポート：${morning ? `\`${morning.path}\`` : 'なし'}

${top3Section}

---

## 2. 本日の事実

- **判定**：${verdict}
- **本日コミット数**：${execution.commits.length}件
- **本日入力された数字**：応募${todayMetrics.applications}・受注${todayMetrics.received}・売上¥${(todayMetrics.revenue_jpy || 0).toLocaleString()}

### コミット詳細

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

\`\`\`text
1.
2.
3.
\`\`\`

→ 別途 \`CDO/research/improvements/${dateStr}_improvement.md\` への転記推奨。

---

## 5. 本日の数字（記録忘れ防止）

数字をまだ入力していなければ：

\`\`\`bash
node CDO/outputs/metrics_input.mjs           # 全項目
node CDO/outputs/metrics_input.mjs --quick   # メモのみ・他は0
\`\`\`

---

## 6. 明日の朝会への申し送り

### 明日の Top3 案（任意）
1.
2.
3.

### 戦略変更
- [ ] 不要（現戦略継続）
- [ ] 必要（理由：）

### オーナーへの相談事項
-

---

## 7. PDCA 完成

\`\`\`
今朝 Plan/Do      ${morningSkipped ? '⚠️ 朝会未実行' : '✅ 完了'}
今夕 Check/Act    ⏳ 記入中
明日 朝会で反映   → morning_meeting.mjs が自動取り込み
\`\`\`

夕方の5分記入で、PDCAが回ります。
`;
}

// メイン
function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) { console.log('node CDO/outputs/evening_checkin.mjs [--dry-run] [--no-notify]'); return; }

  const dateStr = today();
  const dow = dayOfWeekJa();

  console.log('━━━━━━━━━━━━━━━━━━━━━━━');
  console.log(`🌆 ${dateStr}（${dow}）の夕方チェックイン v2`);
  console.log('━━━━━━━━━━━━━━━━━━━━━━━');

  const morning = readTodayMorningMeeting();
  const execution = detectExecutionToday();
  const todayMetrics = loadTodayMetrics();
  const morningSkipped = !checkMorningMeetingExists();
  const alignment = evaluateTop3Alignment(morning, execution, todayMetrics);

  const report = buildCheckin({
    dateStr, dow, morning, execution, alignment, todayMetrics, morningSkipped,
  });

  if (args.dryRun) { console.log(report); return; }

  if (!existsSync(CHECKINS_DIR)) mkdirSync(CHECKINS_DIR, { recursive: true });
  const outPath = join(CHECKINS_DIR, `${dateStr}_evening.md`);
  writeFileSync(outPath, report, 'utf-8');
  console.log(`✅ チェックイン生成: ${outPath}`);

  // スタンドアップ自動更新
  console.log('\n▼ スタンドアップ更新');
  runStandup();

  console.log('━━━━━━━━━━━━━━━━━━━━━━━');
  console.log(`📊 判定：${execution.hasExecution ? '🟢 実行あり' : '🟡 準備物のみ'}`);
  console.log(`   コミット：${execution.commits.length}件`);
  console.log(`   数字：応募${todayMetrics.applications}・受注${todayMetrics.received}・売上¥${(todayMetrics.revenue_jpy || 0).toLocaleString()}`);

  if (morningSkipped) console.log('   ⚠️ 本日朝会未実行');

  console.log('');
  console.log('次の手順：');
  console.log(`  1. ${outPath} を開いて記入（5分）`);
  if (todayMetrics.applications === 0 && todayMetrics.received === 0) {
    console.log('  2. 数字入力：node CDO/outputs/metrics_input.mjs');
  }
  console.log('  3. 改善ログ：CDO/research/improvements/' + dateStr + '_improvement.md');
  console.log('  4. 明朝：node CDO/outputs/morning_meeting.mjs');

  if (args.notify) {
    notify('Agent Team 夕会', `判定：${execution.hasExecution ? '実行あり' : '準備物のみ'}`, execution.hasExecution ? 'info' : 'warn');
  }
}

main();
