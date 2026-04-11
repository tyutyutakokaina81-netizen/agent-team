// budget_guard.mjs
// 自立型AIループの Claude API 支出を封じ込める第一防衛線
//
// 3段階の hard limit:
//   - 1ループあたり: ¥30
//   - 1日あたり: ¥100
//   - 1月あたり: ¥2,000
//
// 上限を超過したら canProceed() が false を返し、呼び出し側は正常終了する。
// 記録は CFO/research/{daily,monthly}_spend.json に蓄積される（Git 管理下）。

import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// ─────────────────────────────────────────────────────────────
// 設定
// ─────────────────────────────────────────────────────────────

export const CONFIG = {
  perLoopLimit: 30,    // ¥/ループ
  dailyLimit: 100,     // ¥/日
  monthlyLimit: 2000,  // ¥/月

  // revenue-gated モードの設定
  // 有効時、monthlyLimit を動的に変更する:
  //   monthlyLimit = max(base, cumulativeRevenue × revenueMultiplier)
  // 収益が出るまで極限まで絞りたい場合は base を 0-500 に設定する
  revenueGated: {
    enabled: false,                // true にすると revenue-gated モード
    baseMonthlyLimit: 500,         // 収益ゼロ時の最低月次予算（¥）
    revenueMultiplier: 1.5,        // 累計収益の何倍まで支出を許容するか
    revenueSourcePath: 'state/revenue/summary.json', // revenue_watcher が生成
    usdcToJpyRate: 150,            // $1 = ¥150 概算
  },

  // 料金レート（円/1Mトークン、$1=¥150 換算の概算）
  // 参考: Anthropic 公式価格（Haiku/Sonnet/Opus）
  rates: {
    'claude-haiku-4-5-20251001': { input: 120, output: 600 },
    'claude-haiku-4-5':          { input: 120, output: 600 },
    'claude-sonnet-4-6':         { input: 450, output: 2250 },
    'claude-sonnet-4-6[1m]':     { input: 900, output: 3375 },
    'claude-opus-4-6':           { input: 2250, output: 11250 },
    'claude-opus-4-6[1m]':       { input: 4500, output: 16875 },
  },
};

// ─────────────────────────────────────────────────────────────
// ファイルパス（リポジトリルートからの相対で解決）
// ─────────────────────────────────────────────────────────────

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, '..');
// 予算台帳は autonomous/state/budget/ に置く。CFO/research/ は .gitignore
// 対象なので、自律ループ間で持続しない（クロスラン共有に不適切）。
const SPEND_DIR = path.join(__dirname, 'state', 'budget');
const DAILY_FILE = path.join(SPEND_DIR, 'daily_spend.json');
const MONTHLY_FILE = path.join(SPEND_DIR, 'monthly_spend.json');

// ─────────────────────────────────────────────────────────────
// 日付ユーティリティ
// ─────────────────────────────────────────────────────────────

function today() {
  return new Date().toISOString().slice(0, 10); // YYYY-MM-DD
}

function currentMonth() {
  return new Date().toISOString().slice(0, 7); // YYYY-MM
}

// ─────────────────────────────────────────────────────────────
// JSON IO（存在しなければデフォルト値）
// ─────────────────────────────────────────────────────────────

async function loadJson(file, defaultValue) {
  if (!existsSync(file)) return { ...defaultValue };
  try {
    const content = await readFile(file, 'utf8');
    return JSON.parse(content);
  } catch (err) {
    console.warn(`[budget_guard] failed to read ${file}: ${err.message}`);
    return { ...defaultValue };
  }
}

async function saveJson(file, data) {
  await mkdir(path.dirname(file), { recursive: true });
  await writeFile(file, JSON.stringify(data, null, 2) + '\n', 'utf8');
}

// ─────────────────────────────────────────────────────────────
// 料金見積もり
// ─────────────────────────────────────────────────────────────

export function estimateYen({ model, inputTokens, outputTokens }) {
  const rate = CONFIG.rates[model];
  if (!rate) {
    console.warn(`[budget_guard] unknown model "${model}", using sonnet rate`);
    const fallback = CONFIG.rates['claude-sonnet-4-6'];
    return (
      (inputTokens / 1_000_000) * fallback.input +
      (outputTokens / 1_000_000) * fallback.output
    );
  }
  return (
    (inputTokens / 1_000_000) * rate.input +
    (outputTokens / 1_000_000) * rate.output
  );
}

// ─────────────────────────────────────────────────────────────
// Revenue-gated 予算計算
// ─────────────────────────────────────────────────────────────

/**
 * revenue_watcher が生成した state/revenue/summary.json を読み、
 * 累計 USDC 収益を円換算で返す。ファイルが無ければ 0。
 */
async function loadCumulativeRevenueYen() {
  const revPath = path.join(__dirname, CONFIG.revenueGated.revenueSourcePath);
  if (!existsSync(revPath)) return 0;
  try {
    const summary = JSON.parse(await readFile(revPath, 'utf8'));
    const usdc = Number(summary.cumulative_diff ?? summary.last_balance ?? 0);
    return usdc * CONFIG.revenueGated.usdcToJpyRate;
  } catch {
    return 0;
  }
}

/**
 * revenue-gated モード時の有効月次上限を計算する。
 * 有効でない場合は CONFIG.monthlyLimit をそのまま返す。
 */
export async function effectiveMonthlyLimit() {
  if (!CONFIG.revenueGated.enabled) {
    return CONFIG.monthlyLimit;
  }
  const revenueYen = await loadCumulativeRevenueYen();
  const gated = Math.max(
    CONFIG.revenueGated.baseMonthlyLimit,
    revenueYen * CONFIG.revenueGated.revenueMultiplier
  );
  // 絶対上限（CONFIG.monthlyLimit）は超えない
  return Math.min(gated, CONFIG.monthlyLimit);
}

// ─────────────────────────────────────────────────────────────
// 許可判定
// ─────────────────────────────────────────────────────────────

/**
 * 新しい呼び出しを許可してよいか判定する。
 * @param {{ estimate: number }} args - 見積もり消費額（円）
 * @returns {Promise<{ allowed: boolean, reason?: string, state?: object }>}
 */
export async function canProceed({ estimate }) {
  const daily = await loadJson(DAILY_FILE, {});
  const monthly = await loadJson(MONTHLY_FILE, {});
  const t = today();
  const m = currentMonth();
  const todaySpend = daily[t] || 0;
  const monthSpend = monthly[m] || 0;

  // revenue-gated 時は動的な月次上限を計算
  const effectiveMonthly = await effectiveMonthlyLimit();

  if (estimate > CONFIG.perLoopLimit) {
    return {
      allowed: false,
      reason: `per-loop limit exceeded: estimate ¥${estimate} > limit ¥${CONFIG.perLoopLimit}`,
      state: { todaySpend, monthSpend, effectiveMonthly },
    };
  }
  if (todaySpend + estimate > CONFIG.dailyLimit) {
    return {
      allowed: false,
      reason: `daily limit exceeded: today ¥${todaySpend.toFixed(2)} + ¥${estimate} > limit ¥${CONFIG.dailyLimit}`,
      state: { todaySpend, monthSpend, effectiveMonthly },
    };
  }
  if (monthSpend + estimate > effectiveMonthly) {
    const gatedSuffix = CONFIG.revenueGated.enabled
      ? ` (revenue-gated effective limit ¥${effectiveMonthly.toFixed(0)})`
      : '';
    return {
      allowed: false,
      reason: `monthly limit exceeded: month ¥${monthSpend.toFixed(2)} + ¥${estimate} > limit ¥${effectiveMonthly.toFixed(0)}${gatedSuffix}`,
      state: { todaySpend, monthSpend, effectiveMonthly },
    };
  }
  return { allowed: true, state: { todaySpend, monthSpend, effectiveMonthly } };
}

// ─────────────────────────────────────────────────────────────
// 消費記録
// ─────────────────────────────────────────────────────────────

/**
 * Claude API 呼び出しの実績を記録する。
 * 省略可: estimatedYen（指定時はそれを使う、未指定なら token から計算）
 */
export async function record({
  officer,
  model,
  inputTokens = 0,
  outputTokens = 0,
  estimatedYen,
}) {
  const yen = estimatedYen ?? estimateYen({ model, inputTokens, outputTokens });
  const daily = await loadJson(DAILY_FILE, {});
  const monthly = await loadJson(MONTHLY_FILE, {});
  const t = today();
  const m = currentMonth();

  daily[t] = Math.round(((daily[t] || 0) + yen) * 100) / 100;
  monthly[m] = Math.round(((monthly[m] || 0) + yen) * 100) / 100;

  // ログ行を追記（役職・モデル・トークン・金額）
  if (!daily._log) daily._log = [];
  daily._log.push({
    at: new Date().toISOString(),
    officer,
    model,
    inputTokens,
    outputTokens,
    yen: Math.round(yen * 100) / 100,
  });
  // ログは直近 500 件まで保持
  if (daily._log.length > 500) daily._log = daily._log.slice(-500);

  await saveJson(DAILY_FILE, daily);
  await saveJson(MONTHLY_FILE, monthly);

  return {
    yen,
    todaySpend: daily[t],
    monthSpend: monthly[m],
  };
}

// ─────────────────────────────────────────────────────────────
// 現状サマリ
// ─────────────────────────────────────────────────────────────

export async function summary() {
  const daily = await loadJson(DAILY_FILE, {});
  const monthly = await loadJson(MONTHLY_FILE, {});
  const t = today();
  const m = currentMonth();
  const effectiveMonthly = await effectiveMonthlyLimit();
  return {
    today: daily[t] || 0,
    month: monthly[m] || 0,
    dailyLimit: CONFIG.dailyLimit,
    monthlyLimit: CONFIG.monthlyLimit,
    effectiveMonthlyLimit: effectiveMonthly,
    revenueGatedMode: CONFIG.revenueGated.enabled,
    perLoopLimit: CONFIG.perLoopLimit,
    todayRemaining: Math.max(0, CONFIG.dailyLimit - (daily[t] || 0)),
    monthRemaining: Math.max(0, CONFIG.monthlyLimit - (monthly[m] || 0)),
  };
}

// ─────────────────────────────────────────────────────────────
// CLI エントリ
// ─────────────────────────────────────────────────────────────
//
// 使い方:
//   node autonomous/budget_guard.mjs status
//   node autonomous/budget_guard.mjs check 25
//   node autonomous/budget_guard.mjs simulate 1200 800 claude-haiku-4-5

const isMain = import.meta.url === `file://${process.argv[1]}`;
if (isMain) {
  const cmd = process.argv[2] || 'status';

  if (cmd === 'status') {
    const s = await summary();
    console.log(JSON.stringify(s, null, 2));
  } else if (cmd === 'check') {
    const est = parseFloat(process.argv[3] || '30');
    const r = await canProceed({ estimate: est });
    console.log(JSON.stringify(r, null, 2));
    process.exit(r.allowed ? 0 : 1);
  } else if (cmd === 'simulate') {
    const inputTokens = parseInt(process.argv[3] || '1000', 10);
    const outputTokens = parseInt(process.argv[4] || '500', 10);
    const model = process.argv[5] || 'claude-haiku-4-5-20251001';
    const yen = estimateYen({ model, inputTokens, outputTokens });
    console.log(JSON.stringify({ model, inputTokens, outputTokens, estimatedYen: yen }, null, 2));
  } else {
    console.error(`Unknown command: ${cmd}`);
    console.error('Usage: node budget_guard.mjs [status|check <yen>|simulate <in> <out> <model>]');
    process.exit(1);
  }
}
