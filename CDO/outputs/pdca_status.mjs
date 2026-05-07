#!/usr/bin/env node
/**
 * pdca_status.mjs — PDCA ヘルスチェック
 *
 * いつでも実行：「PDCA はちゃんと回ってる？」を一発で確認
 *
 * 費用ゼロ：Node 標準モジュールのみ
 *
 * 使い方:
 *   node CDO/outputs/pdca_status.mjs
 */

import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dir = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dir, '../..');
const MEETINGS_DIR = join(REPO_ROOT, 'CDO', 'research', 'meetings');
const CHECKINS_DIR = join(REPO_ROOT, 'CDO', 'research', 'checkins');
const STANDUPS_DIR = join(REPO_ROOT, 'CDO', 'research', 'standups');
const IMPROVEMENTS_DIR = join(REPO_ROOT, 'CDO', 'research', 'improvements');
const METRICS_FILE = join(REPO_ROOT, 'CFO', 'research', '_revenue_data', 'metrics.jsonl');

function safe(fn, fb) { try { return fn(); } catch { return fb; } }
function today() { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; }

function listFiles(dir, suffix) {
  return safe(() => {
    if (!existsSync(dir)) return [];
    return readdirSync(dir).filter(f => f.endsWith(suffix)).sort();
  }, []);
}

function daysBetween(a, b) {
  return Math.floor((new Date(a) - new Date(b)) / (1000 * 60 * 60 * 24));
}

function status(label, ok, detail) {
  const icon = ok === true ? '🟢' : ok === false ? '🔴' : '🟡';
  console.log(`${icon} ${label}：${detail}`);
}

function main() {
  console.log('━━━━━━━━━━━━━━━━━━━━━━━');
  console.log(`🩺 PDCA ヘルスチェック：${today()}`);
  console.log('━━━━━━━━━━━━━━━━━━━━━━━');

  // 朝会
  const meetings = listFiles(MEETINGS_DIR, '_morning.md');
  const todayMorning = meetings.includes(`${today()}_morning.md`);
  const lastMorning = meetings.length > 0 ? meetings[meetings.length - 1].replace('_morning.md', '') : null;
  const morningGap = lastMorning ? daysBetween(today(), lastMorning) : 999;
  status('本日の朝会', todayMorning,
    todayMorning ? '実行済み' :
    lastMorning ? `${morningGap}日前が最新（${lastMorning}）` :
    '未実行（初回）');

  // 夕方チェックイン
  const checkins = listFiles(CHECKINS_DIR, '_evening.md');
  const todayCheckin = checkins.includes(`${today()}_evening.md`);
  const lastCheckin = checkins.length > 0 ? checkins[checkins.length - 1].replace('_evening.md', '') : null;
  const checkinGap = lastCheckin ? daysBetween(today(), lastCheckin) : 999;
  status('本日のチェックイン', todayCheckin,
    todayCheckin ? '実行済み' :
    lastCheckin ? `${checkinGap}日前が最新（${lastCheckin}）` :
    '未実行（初回）');

  // スタンドアップ
  const standups = listFiles(STANDUPS_DIR, '_standup.md');
  const todayStandup = standups.includes(`${today()}_standup.md`);
  const lastStandup = standups.length > 0 ? standups[standups.length - 1].replace('_standup.md', '') : null;
  const standupGap = lastStandup ? daysBetween(today(), lastStandup) : 999;
  status('本日のスタンドアップ', todayStandup,
    todayStandup ? '実行済み' :
    lastStandup ? `${standupGap}日前が最新（${lastStandup}）` :
    '未実行（初回）');

  // 改善ログ
  const improvements = listFiles(IMPROVEMENTS_DIR, '_improvement.md');
  const last7Days = improvements.filter(f => {
    const d = f.replace('_improvement.md', '');
    return daysBetween(today(), d) <= 7;
  });
  status('直近7日の改善ログ', last7Days.length >= 3,
    `${last7Days.length}日分（推奨：3日以上）`);

  // 数字入力
  const metricsExist = existsSync(METRICS_FILE);
  const todayMetrics = safe(() => {
    if (!metricsExist) return null;
    const lines = readFileSync(METRICS_FILE, 'utf-8').split('\n').filter(Boolean);
    return lines.find(l => { try { const r = JSON.parse(l); return r.date === today(); } catch { return false; } });
  }, null);
  status('本日の数字入力', !!todayMetrics,
    todayMetrics ? '入力済み' : '未入力（node CDO/outputs/metrics_input.mjs）');

  // 連続実行ギャップ
  const recentStandups = standups.slice(-7).reverse();
  let gapDays = 0;
  for (const f of recentStandups) {
    const content = safe(() => readFileSync(join(STANDUPS_DIR, f), 'utf-8'), '');
    if (content.includes('準備物のみ増加')) gapDays++;
    else break;
  }
  status('実行ギャップ', gapDays < 3,
    `${gapDays}日連続「準備物のみ」（警告閾値：3日）`);

  // 戦略文書
  let strategyOk = false;
  let strategyDetail = '未作成';
  safe(() => {
    const candidates = [];
    function scan(dir) {
      if (!existsSync(dir)) return;
      for (const e of readdirSync(dir, { withFileTypes: true })) {
        const full = join(dir, e.name);
        if (e.isDirectory()) scan(full);
        else if (e.name.startsWith('strategy_review_')) candidates.push(full);
      }
    }
    scan(join(REPO_ROOT, 'projects'));
    candidates.sort();
    if (candidates.length > 0) {
      const content = readFileSync(candidates[candidates.length - 1], 'utf-8');
      const decided = /推奨戦略「[^」]+」/.test(content) || /採用：戦略[A-C]/.test(content);
      strategyOk = decided;
      strategyDetail = decided ? '採用戦略あり' : '推奨はあるが未確定';
    }
  });
  status('戦略の意思決定', strategyOk, strategyDetail);

  console.log('━━━━━━━━━━━━━━━━━━━━━━━');

  // 推奨アクション
  const recs = [];
  if (!todayMorning) recs.push('node CDO/outputs/morning_meeting.mjs');
  if (!todayMetrics) recs.push('node CDO/outputs/metrics_input.mjs --quick');
  if (!todayCheckin && new Date().getHours() >= 17) recs.push('node CDO/outputs/evening_checkin.mjs');
  if (gapDays >= 3) recs.push('⚠️ 戦略レビューを再読：projects/2026-04-08_月30万自動化/strategy_review_*.md');

  if (recs.length === 0) {
    console.log('✨ すべて健全。継続しましょう。');
  } else {
    console.log('推奨アクション：');
    recs.forEach(r => console.log(`  - ${r}`));
  }

  console.log('━━━━━━━━━━━━━━━━━━━━━━━');
}

main();
