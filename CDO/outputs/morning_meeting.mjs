#!/usr/bin/env node
/**
 * morning_meeting.mjs — 朝の戦略会議 自動生成（PDCA: Plan + Do）v2
 *
 * v2 改善点（13項目反映）：
 *   #1 戦略検知の堅牢化：複数パターンで採用戦略を抽出
 *   #2 Top3 動的生成：戦略 × 数字 × 直近チェックインから推論
 *   #3 昨日 fallback：昨日なければ最新スタンドアップ
 *   #4 robust parsing：try/catch で全体保護
 *   #9 動的アクション：metrics_summary を読んで指標連動
 *   #11 戦略未確定の自動エスカレーション：3日以上未決で警告
 *   #12 跨日整合性：昨夕のチェックイン Top3 と今朝の連続性
 *   #13 役職別議論：CMO/CSO/CDO/CFO/CPO 5役職の独立視点
 *
 * 費用ゼロ：Node 標準モジュールのみ
 *
 * 使い方:
 *   node CDO/outputs/morning_meeting.mjs
 *   node CDO/outputs/morning_meeting.mjs --dry-run
 *   node CDO/outputs/morning_meeting.mjs --no-notify
 */

import { writeFileSync, existsSync, mkdirSync, readFileSync, readdirSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { notify } from './notify.mjs';
import { today, dayOfWeekJa, safe, sh as shBase } from './lib/pdca_lib.mjs';

const __dir = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dir, '../..');
const MEETINGS_DIR = join(REPO_ROOT, 'CDO', 'research', 'meetings');
const STANDUPS_DIR = join(REPO_ROOT, 'CDO', 'research', 'standups');
const CHECKINS_DIR = join(REPO_ROOT, 'CDO', 'research', 'checkins');
const PROJECT_DIR = join(REPO_ROOT, 'projects');
const METRICS_FILE = join(REPO_ROOT, 'CFO', 'research', '_revenue_data', 'metrics.jsonl');

const sh = (cmd) => shBase(cmd, { cwd: REPO_ROOT });

// ─────────────────────────────────────────────
// CLI
// ─────────────────────────────────────────────
function parseArgs(argv) {
  const args = { dryRun: false, notify: true, ifMissing: false };
  for (const a of argv) {
    if (a === '--dry-run') args.dryRun = true;
    else if (a === '--no-notify') args.notify = false;
    else if (a === '--if-missing') args.ifMissing = true;
    else if (a === '--help' || a === '-h') args.help = true;
  }
  return args;
}

function showHelp() {
  console.log(`morning_meeting.mjs — 朝の戦略会議

USAGE:
  node CDO/outputs/morning_meeting.mjs
  node CDO/outputs/morning_meeting.mjs --dry-run
  node CDO/outputs/morning_meeting.mjs --no-notify
  node CDO/outputs/morning_meeting.mjs --if-missing  # 当日分が無い時だけ生成（冪等）

費用ゼロ：外部API呼び出しなし、Node標準モジュールのみ。
`);
}

// ─────────────────────────────────────────────
// #1 堅牢な戦略検知
// ─────────────────────────────────────────────
function findLatestStrategyDoc() {
  return safe(() => {
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
    candidates.sort();
    return candidates[candidates.length - 1] || null;
  }, null);
}

function extractStrategy(strategyPath) {
  if (!strategyPath || !existsSync(strategyPath)) return null;
  return safe(() => {
    const content = readFileSync(strategyPath, 'utf-8');
    // 複数パターンで採用戦略を抽出
    const patterns = [
      /推奨戦略「([^」]+)」/,
      /採用する?戦略[:：]\s*(.+?)(?:\n|$)/,
      /\[x\]\s*戦略([A-C])/i,
      /採用：戦略([A-C])/,
      /# Part 4：推奨戦略「([^」]+)」/,
    ];
    let recommended = null;
    for (const p of patterns) {
      const m = content.match(p);
      if (m) { recommended = m[1].startsWith('戦略') ? m[1] : `戦略${m[1]}`; break; }
    }
    return {
      path: strategyPath.replace(REPO_ROOT + '/', ''),
      recommended,
      hasContent: content.length > 0,
    };
  }, null);
}

// #11 戦略未決の連続日数（戦略文書の更新日が古ければ未決とみなす）
function getStrategyUndecidedDays(strategy) {
  if (!strategy) return 999;
  if (!strategy.recommended) {
    return safe(() => {
      const stat = require('node:fs').statSync(join(REPO_ROOT, strategy.path));
      const days = Math.floor((Date.now() - stat.mtimeMs) / (1000 * 60 * 60 * 24));
      return days;
    }, 0);
  }
  return 0;
}

// ─────────────────────────────────────────────
// #3 昨日 fallback
// ─────────────────────────────────────────────
function getMostRecentStandup() {
  return safe(() => {
    if (!existsSync(STANDUPS_DIR)) return null;
    const files = readdirSync(STANDUPS_DIR)
      .filter(f => f.endsWith('_standup.md'))
      .sort()
      .reverse();
    const todayName = `${today()}_standup.md`;
    for (const f of files) {
      if (f === todayName) continue;  // 今日のはスキップ
      const dateStr = f.replace('_standup.md', '');
      const content = readFileSync(join(STANDUPS_DIR, f), 'utf-8');
      const verdictMatch = content.match(/判定：(.+?)\*\*/);
      const commitsMatch = content.match(/コミット数 \| (\d+)/);
      return {
        date: dateStr,
        path: join(STANDUPS_DIR, f).replace(REPO_ROOT + '/', ''),
        verdict: verdictMatch ? verdictMatch[1].trim() : '不明',
        commits: commitsMatch ? parseInt(commitsMatch[1]) : 0,
        ageInDays: Math.floor((new Date(today()) - new Date(dateStr)) / (1000 * 60 * 60 * 24)),
      };
    }
    return null;
  }, null);
}

// ─────────────────────────────────────────────
// #12 昨夕のチェックインから「跨日連続性」
// ─────────────────────────────────────────────
function getLastEveningCheckin() {
  return safe(() => {
    if (!existsSync(CHECKINS_DIR)) return null;
    const files = readdirSync(CHECKINS_DIR)
      .filter(f => f.endsWith('_evening.md'))
      .sort()
      .reverse();
    const todayName = `${today()}_evening.md`;
    for (const f of files) {
      if (f === todayName) continue;
      return {
        date: f.replace('_evening.md', ''),
        path: join(CHECKINS_DIR, f).replace(REPO_ROOT + '/', ''),
      };
    }
    return null;
  }, null);
}

// ─────────────────────────────────────────────
// #9, #10 数字の参照
// ─────────────────────────────────────────────
function loadMetrics() {
  return safe(() => {
    if (!existsSync(METRICS_FILE)) return [];
    return readFileSync(METRICS_FILE, 'utf-8')
      .split('\n').filter(Boolean)
      .map(l => { try { return JSON.parse(l); } catch { return null; } })
      .filter(Boolean);
  }, []);
}

function metricsSummary(records) {
  const recent7 = records.slice(-7);
  const recent30 = records.slice(-30);
  const sum = (arr, key) => arr.reduce((s, r) => s + (r[key] || 0), 0);
  return {
    last7_applications: sum(recent7, 'applications'),
    last7_received: sum(recent7, 'received'),
    last7_revenue: sum(recent7, 'revenue_jpy'),
    last30_applications: sum(recent30, 'applications'),
    last30_received: sum(recent30, 'received'),
    last30_revenue: sum(recent30, 'revenue_jpy'),
    last30_pv: sum(recent30, 'note_pv'),
    last30_template_sales: sum(recent30, 'template_sales'),
  };
}

// ─────────────────────────────────────────────
// 連続Top3検知：過去N日の朝会 Top3 タイトルが同一なら警告
// ─────────────────────────────────────────────
function getTop3StreakDays() {
  return safe(() => {
    if (!existsSync(MEETINGS_DIR)) return { count: 0, lastTitles: [] };
    const files = readdirSync(MEETINGS_DIR)
      .filter(f => f.endsWith('_morning.md'))
      .sort()
      .reverse();
    if (files.length < 2) return { count: 0, lastTitles: [] };

    const extractTitles = (filePath) => {
      const content = readFileSync(filePath, 'utf-8');
      const titles = [];
      const lines = content.split('\n');
      let inSection = false;
      for (const line of lines) {
        if (line.includes('## 🎬 今日のTop3アクション')) inSection = true;
        else if (line.startsWith('---') && inSection) inSection = false;
        else if (inSection && line.startsWith('### ')) {
          const m = line.match(/### .+?\s+(.+)/);
          if (m) titles.push(m[1].trim());
        }
      }
      return titles.slice(0, 3);
    };

    const todayName = `${today()}_morning.md`;
    const candidates = files.filter(f => f !== todayName);
    if (candidates.length === 0) return { count: 0, lastTitles: [] };

    const recent = candidates.slice(0, 7);
    const baseTitles = extractTitles(join(MEETINGS_DIR, recent[0]));
    if (baseTitles.length === 0) return { count: 0, lastTitles: [] };

    let count = 1;
    for (let i = 1; i < recent.length; i++) {
      const titles = extractTitles(join(MEETINGS_DIR, recent[i]));
      if (titles.length === 0) break;
      const same = titles.length === baseTitles.length &&
                   titles.every((t, idx) => t === baseTitles[idx]);
      if (same) count++;
      else break;
    }
    return { count, lastTitles: baseTitles };
  }, { count: 0, lastTitles: [] });
}

// ─────────────────────────────────────────────
// #7 PDCA スキップ検知
// ─────────────────────────────────────────────
function getPdcaSkipDays() {
  return safe(() => {
    if (!existsSync(MEETINGS_DIR)) return 0;
    const files = readdirSync(MEETINGS_DIR)
      .filter(f => f.endsWith('_morning.md'))
      .sort()
      .reverse();
    if (files.length === 0) return 999;
    const lastDate = files[0].replace('_morning.md', '');
    if (lastDate === today()) {
      // 今日既に存在する場合は2番目で判定
      if (files.length < 2) return 0;
      const prev = files[1].replace('_morning.md', '');
      return Math.floor((new Date(today()) - new Date(prev)) / (1000 * 60 * 60 * 24)) - 1;
    }
    return Math.floor((new Date(today()) - new Date(lastDate)) / (1000 * 60 * 60 * 24));
  }, 0);
}

// 連続実行ギャップ日数
function getConsecutiveGapDays() {
  return safe(() => {
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
  }, 0);
}

// ─────────────────────────────────────────────
// 各役職の進行中タスク
// ─────────────────────────────────────────────
function collectInProgressTasks() {
  const roles = ['CDO', 'CFO', 'CMO', 'CPO', 'CSO'];
  const tasks = {};
  for (const role of roles) {
    safe(() => {
      const indexPath = join(REPO_ROOT, role, '_index.md');
      if (!existsSync(indexPath)) return;
      const content = readFileSync(indexPath, 'utf-8');
      const match = content.match(/## 進行中タスク\s*\n+([\s\S]*?)(?=\n## |$)/);
      if (!match) return;
      const items = match[1]
        .split('\n')
        .map(l => l.trim())
        .filter(l => l.startsWith('- ') && !l.includes('（なし）'))
        .map(l => l.replace(/^- /, ''));
      if (items.length) tasks[role] = items;
    });
  }
  return tasks;
}

// ─────────────────────────────────────────────
// #13 役職別議論シミュレーション
// ─────────────────────────────────────────────
function simulateRolePerspectives(strategy, metrics, tasks, gapDays) {
  const isPillarA = strategy?.recommended?.match(/A/);
  const lowApplications = (metrics.last7_applications || 0) < 10;
  const lowRevenue = (metrics.last30_revenue || 0) < 10000;
  const noNotePub = (metrics.last30_pv || 0) === 0;

  const perspectives = [];

  // CMO（マーケティング・コンテンツ）
  perspectives.push({
    role: 'CMO',
    icon: '📣',
    point:
      noNotePub
        ? '直近30日で note PV ゼロ。コンテンツが世に出ていない。今日 Vol.1 集客記事を公開すべき。コピペで30分の作業'
        : metrics.last30_pv < 100
          ? 'PV はあるが集客力不足。タイトルやサムネ A/B テストを推奨'
          : '集客記事は機能している。次は SNS 連動で増幅'
  });

  // CSO（営業・受注）
  perspectives.push({
    role: 'CSO',
    icon: '💼',
    point:
      lowApplications
        ? `応募数が直近7日で${metrics.last7_applications || 0}件。1日5件目標に対して${metrics.last7_applications < 35 ? '不足' : '達成'}。今日5件応募する時間枠を確保すべき`
        : metrics.last7_received === 0
          ? '応募はあるが受注ゼロ。応募メッセージか案件選定の見直しが必要'
          : '受注が出始めた。継続契約への切替交渉を最優先で'
  });

  // CFO（財務・税務）
  perspectives.push({
    role: 'CFO',
    icon: '💰',
    point: tasks.CFO?.some(t => t.includes('開業届'))
      ? '開業届の期限が切迫中。本日中に e-Tax 提出を推奨。青色申告65万円控除の権利確保'
      : lowRevenue
        ? `30日売上 ¥${(metrics.last30_revenue || 0).toLocaleString()}。月次目標 ¥40K に対して${Math.round((metrics.last30_revenue || 0) / 40000 * 100)}%`
        : '売上は計画通り。請求書発行・経費記録の習慣化を継続'
  });

  // CDO（自動化・技術）
  perspectives.push({
    role: 'CDO',
    icon: '⚙️',
    point: gapDays >= 3
      ? `実行ギャップ${gapDays}日連続。スクリプトはすべて稼働しているが、オーナーの実行アクションが必要`
      : '自動化基盤は機能中。改善ログ・週次レトロを習慣化することで、PDCA の質が上がる'
  });

  // CPO（プロダクト）
  perspectives.push({
    role: 'CPO',
    icon: '📦',
    point: isPillarA
      ? '戦略A 採用なら、テンプレ販売（柱C）の新規制作は停止が妥当。既存 Vol.1〜5 の note 公開のみ最低限維持'
      : 'テンプレ販売の Vol.1 が note で動いていない。Vol.2 以降の制作より Vol.1 の販売チャネル開拓が優先'
  });

  return perspectives;
}

// ─────────────────────────────────────────────
// #2, #9 動的 Top3 生成（戦略 × 数字 × 直近チェックイン）
// ─────────────────────────────────────────────
function generateTodayActions(strategy, metrics, tasks, gapDays, undecidedDays) {
  const actions = [];

  // #11 戦略未決のエスカレーション
  if (undecidedDays >= 3) {
    actions.push({
      priority: '🚨',
      target: 'オーナー',
      title: '戦略の意思決定（3日以上未決）',
      time: '今日の最初',
      detail: 'strategy_review の Part 8 で戦略A/B/C を選択し、文書に追記',
      success: '戦略採用が確定する',
    });
    return actions; // これが最優先
  }

  // 実行ギャップ警告
  if (gapDays >= 3) {
    actions.push({
      priority: '🚨',
      target: 'オーナー',
      title: `${gapDays}日連続「実行アクションなし」状態`,
      time: '今すぐ',
      detail: 'note 公開・応募・登録のいずれか1つを実行する。準備物の追加生成は禁止',
      success: 'context/diary または metrics に実行記録が増える',
    });
  }

  const isPillarA = strategy?.recommended?.match(/A/);

  if (isPillarA) {
    // 数字駆動：何が遅れているかで優先順位を決める
    if ((metrics.last7_applications || 0) === 0) {
      actions.push({
        priority: actions.length === 0 ? '🥇' : '🥈',
        target: 'オーナー',
        title: 'クラウドワークス・ランサーズ登録',
        time: '午前9〜10時',
        detail: 'profile_bio.md コピペ＋本人確認＋プロフィール画像（Canva）',
        success: 'プロフィール完成度100%',
      });
      actions.push({
        priority: actions.length === 0 ? '🥇' : actions.length === 1 ? '🥈' : '🥉',
        target: 'オーナー',
        title: '初応募 5件',
        time: '午前10〜11時',
        detail: 'job_evaluation_checklist.md で80点以上のみ。業種別テンプレ使用',
        success: 'metrics_input.mjs で5件記録',
      });
    } else if ((metrics.last7_applications || 0) < 35) {
      actions.push({
        priority: actions.length === 0 ? '🥇' : '🥈',
        target: 'オーナー',
        title: `応募ペース回復（先週${metrics.last7_applications}件 → 目標35件）`,
        time: '午前9〜11時',
        detail: '今日5件以上応募。返信があった案件主の質問に24h以内返信',
        success: 'metrics で応募+5件以上',
      });
    } else if ((metrics.last7_received || 0) === 0) {
      actions.push({
        priority: '🥇',
        target: 'オーナー',
        title: '応募メッセージの A/B テスト',
        time: '午前',
        detail: '受注ゼロが続く場合、テンプレを業種別に短縮版へ切替えて検証',
        success: '改善ログに仮説と結果を記録',
      });
    } else if ((metrics.last7_received || 0) > 0) {
      actions.push({
        priority: '🥇',
        target: 'オーナー',
        title: '受注案件の品質納品＋継続交渉',
        time: '集中時間',
        detail: '初回案件は速納・修正最少を死守。納品時に2回目以降の打診',
        success: '評価★4以上獲得',
      });
    }
  } else {
    actions.push({
      priority: '⚠️',
      target: 'オーナー',
      title: '戦略の意思決定',
      time: '本日中',
      detail: 'strategy_review の Part 8 で戦略A/B/C を選択',
      success: '戦略確定',
    });
  }

  // 夕方チェックインを最後に必ず追加
  if (actions.length < 3) {
    actions.push({
      priority: '🥉',
      target: 'AI',
      title: '夕方チェックインで実績集計',
      time: '夕方17時以降',
      detail: 'node CDO/outputs/evening_checkin.mjs を実行（または自動）',
      success: 'チェックインファイルが生成される',
    });
  }

  return actions.slice(0, 3);
}

// ─────────────────────────────────────────────
// #4 既存 24h コミット数（堅牢化）
// ─────────────────────────────────────────────
function recentCommitsCount() {
  const r = sh(`git log --since="1 day ago" --oneline | wc -l`);
  return parseInt(r) || 0;
}

// ─────────────────────────────────────────────
// レポート生成
// ─────────────────────────────────────────────
function buildMeeting(opts) {
  const {
    strategy, standup, lastCheckin, metrics, perspectives,
    tasks, gapDays, skipDays, undecidedDays, commitsCount,
    dateStr, dow, todayActions,
  } = opts;

  const tasksSection = Object.keys(tasks).length === 0
    ? '_（進行中タスクなし）_'
    : Object.entries(tasks)
        .map(([role, items]) => `**${role}**\n${items.map(t => `- ${t}`).join('\n')}`)
        .join('\n\n');

  const actionsSection = todayActions.map(a =>
    `### ${a.priority} ${a.title}\n\n- **担当**：${a.target}\n- **時間枠**：${a.time}\n- **詳細**：${a.detail}\n- **達成基準**：${a.success}`
  ).join('\n\n');

  const perspectivesSection = perspectives.map(p =>
    `### ${p.icon} ${p.role} の視点\n\n${p.point}`
  ).join('\n\n');

  const warnings = [];
  if (undecidedDays >= 3) warnings.push(`🚨 **戦略未決定が${undecidedDays}日継続中**`);
  if (gapDays >= 3) warnings.push(`🚨 **実行ギャップ${gapDays}日連続**`);
  if (skipDays >= 2) warnings.push(`⚠️ 朝会スキップ${skipDays}日`);
  if (opts.top3Streak >= 3) warnings.push(`🟡 **同じTop3が${opts.top3Streak}日連続**：戦略は機能しているが実行が進んでいない兆候`);

  const warningsBlock = warnings.length === 0 ? '' : `\n${warnings.map(w => `> ${w}`).join('\n')}\n`;

  const standupSection = standup
    ? `- **判定**：${standup.verdict}\n- **コミット**：${standup.commits}件\n- **${standup.ageInDays}日前**：\`${standup.path}\``
    : '_スタンドアップなし（初回実行か削除）_';

  const continuitySection = lastCheckin
    ? `- 直近の夕方チェックイン：\`${lastCheckin.path}\`（${lastCheckin.date}）\n- 上記の「明日の Top3 案」を本日の Top3 に反映してください`
    : '_直近の夕方チェックインなし。今夕 \`evening_checkin.mjs\` の実行を推奨_';

  const metricsSection =
`| 指標 | 7日 | 30日 |
|------|-----|------|
| 応募数 | ${metrics.last7_applications} | ${metrics.last30_applications} |
| 受注数 | ${metrics.last7_received} | ${metrics.last30_received} |
| 売上（円） | ${metrics.last7_revenue.toLocaleString()} | ${metrics.last30_revenue.toLocaleString()} |
| note PV | — | ${metrics.last30_pv} |
| テンプレ販売 | — | ${metrics.last30_template_sales} |`;

  return `# 朝の戦略会議：${dateStr}（${dow}曜日）v2

> このレポートは \`CDO/outputs/morning_meeting.mjs\` v2 が自動生成しました。
> 1分で読んで、今日の3アクションを実行してください。
> 費用：¥0（外部API呼び出しなし）
${warningsBlock}
---

## 🎯 戦略アライメント（PDCA: Plan）

${strategy
  ? `- **採用戦略**：${strategy.recommended || '⚠️ 未確定（要意思決定）'}\n- **戦略文書**：\`${strategy.path}\`\n- **未決定継続**：${undecidedDays}日`
  : '- 戦略文書なし。要作成'}

---

## 🎬 今日のTop3アクション（PDCA: Do）

${actionsSection}

---

## 🗣 役職別の視点（議論シミュレーション）

${perspectivesSection}

---

## 📊 数字（直近実績）

${metricsSection}

> 数字を更新する：\`node CDO/outputs/metrics_input.mjs\`

---

## 📋 昨日のチェック（PDCA: Check）

### 直近スタンドアップ

${standupSection}

### 跨日連続性

${continuitySection}

- **直近24時間のコミット数**：${commitsCount}件

---

## 🔄 進行中タスク（参考）

${tasksSection}

---

## 🎯 今日のルーティン

\`\`\`
07:30  この朝会レポートを読む（1分）
09:00  Top3 アクション開始
12:00  進捗の自己チェック（任意）
17:00  夕方チェックイン：node CDO/outputs/evening_checkin.mjs
21:00  数字入力：node CDO/outputs/metrics_input.mjs --quick
\`\`\`

---

## 📚 リファレンス

- 戦略：\`${strategy?.path || '（未作成）'}\`
- 応募ツール：\`projects/2026-04-08_月30万自動化/A_ライティング/templates/\`
- 数字サマリ：\`CFO/outputs/metrics_summary.md\`
- PDCA セットアップ：\`CDO/outputs/pdca_scheduling_setup.md\`

---

*手動実行：\`node CDO/outputs/morning_meeting.mjs\`*
*完璧でない点は \`CDO/outputs/morning_meeting.mjs\` のコメント参照*
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

  // --if-missing：今日の朝会レポートが既存ならファイル書き込みをスキップ
  if (args.ifMissing && existsSync(join(MEETINGS_DIR, `${dateStr}_morning.md`))) {
    console.log(`✅ 朝会レポート既存（スキップ）: CDO/research/meetings/${dateStr}_morning.md`);
    return;
  }

  const strategy = extractStrategy(findLatestStrategyDoc());
  const undecidedDays = getStrategyUndecidedDays(strategy);
  const standup = getMostRecentStandup();
  const lastCheckin = getLastEveningCheckin();
  const tasks = collectInProgressTasks();
  const gapDays = getConsecutiveGapDays();
  const skipDays = getPdcaSkipDays();
  const top3StreakInfo = getTop3StreakDays();
  const commitsCount = recentCommitsCount();
  const metrics = metricsSummary(loadMetrics());
  const perspectives = simulateRolePerspectives(strategy, metrics, tasks, gapDays);
  const todayActions = generateTodayActions(strategy, metrics, tasks, gapDays, undecidedDays);

  const report = buildMeeting({
    strategy, standup, lastCheckin, metrics, perspectives,
    tasks, gapDays, skipDays, undecidedDays, commitsCount,
    top3Streak: top3StreakInfo.count, top3StreakTitles: top3StreakInfo.lastTitles,
    dateStr, dow, todayActions,
  });

  if (args.dryRun) {
    console.log(report);
    return;
  }

  if (!existsSync(MEETINGS_DIR)) mkdirSync(MEETINGS_DIR, { recursive: true });
  const outPath = join(MEETINGS_DIR, `${dateStr}_morning.md`);
  writeFileSync(outPath, report, 'utf-8');

  console.log(`✅ 朝会レポート v2 生成: ${outPath}`);
  console.log('━━━━━━━━━━━━━━━━━━━━━━━');
  console.log(`📅 ${dateStr}（${dow}）の朝会`);
  console.log('━━━━━━━━━━━━━━━━━━━━━━━');
  if (undecidedDays >= 3) console.log(`🚨 戦略未決定 ${undecidedDays}日継続`);
  if (gapDays >= 3) console.log(`🚨 実行ギャップ ${gapDays}日連続`);
  if (skipDays >= 2) console.log(`⚠️ 朝会スキップ ${skipDays}日`);
  console.log(`🎯 戦略：${strategy?.recommended || '未確定'}`);
  console.log(`📊 7日応募：${metrics.last7_applications} / 受注：${metrics.last7_received} / 売上：¥${metrics.last7_revenue.toLocaleString()}`);
  console.log('');
  console.log('今日のTop3：');
  todayActions.forEach(a => console.log(`  ${a.priority} ${a.title} (${a.target})`));

  if (args.notify) {
    const notifyBody = todayActions.length > 0
      ? `Top3: ${todayActions.map(a => a.title).join(' / ')}`
      : '本日の朝会レポート生成済み';
    notify('Agent Team 朝会', notifyBody, gapDays >= 3 ? 'warn' : 'info');
  }
}

main();
