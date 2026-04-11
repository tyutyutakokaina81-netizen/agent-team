// revenue_watcher.mjs
//
// Base ネットワーク上のオーナーウォレットに入金される USDC を監視する。
// 完全 zero-dep（fetch + Node.js 標準ライブラリのみ）。
//
// 使い方:
//   export OWNER_WALLET=0xYourWalletAddress
//   node autonomous/revenue_watcher.mjs snapshot   # 現在残高を記録
//   node autonomous/revenue_watcher.mjs report     # 差分レポート
//   node autonomous/revenue_watcher.mjs watch      # 10分おきに snapshot（長時間実行）
//
// 保存先:
//   autonomous/state/revenue/config.json    - ウォレット設定
//   autonomous/state/revenue/snapshots.json - 残高スナップショット履歴（追記型）
//   autonomous/state/revenue/summary.json   - 集計（累計入金額・最終確認時刻）
//
// USDC on Base contract: 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
// Decimals: 6

import { readFile, writeFile, mkdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// ─────────────────────────────────────────────────────────────
// 設定
// ─────────────────────────────────────────────────────────────

const STATE_DIR = path.join(__dirname, "state", "revenue");
const CONFIG_FILE = path.join(STATE_DIR, "config.json");
const SNAPSHOTS_FILE = path.join(STATE_DIR, "snapshots.json");
const SUMMARY_FILE = path.join(STATE_DIR, "summary.json");

// USDC on Base (Coinbase の公式ブリッジ版)
const USDC_CONTRACT = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const USDC_DECIMALS = 6;

// 複数のパブリック RPC endpoint（fallback 用）
const BASE_RPC_ENDPOINTS = [
  "https://mainnet.base.org",
  "https://base.llamarpc.com",
  "https://base-rpc.publicnode.com",
  "https://1rpc.io/base",
];

// ─────────────────────────────────────────────────────────────
// ファイル IO
// ─────────────────────────────────────────────────────────────

async function loadJson(file, fallback) {
  if (!existsSync(file)) return structuredClone(fallback);
  try {
    return JSON.parse(await readFile(file, "utf8"));
  } catch {
    return structuredClone(fallback);
  }
}

async function saveJson(file, data) {
  await mkdir(path.dirname(file), { recursive: true });
  await writeFile(file, JSON.stringify(data, null, 2) + "\n", "utf8");
}

// ─────────────────────────────────────────────────────────────
// 設定管理
// ─────────────────────────────────────────────────────────────

async function loadConfig() {
  const cfg = await loadJson(CONFIG_FILE, {
    wallet: null,
    network: "base",
    currency: "USDC",
    contract: USDC_CONTRACT,
    decimals: USDC_DECIMALS,
    poll_interval_ms: 600000, // 10 分
  });
  // 環境変数が最優先
  if (process.env.OWNER_WALLET) {
    cfg.wallet = process.env.OWNER_WALLET;
  }
  return cfg;
}

async function saveConfig(cfg) {
  await saveJson(CONFIG_FILE, cfg);
}

// ─────────────────────────────────────────────────────────────
// ERC20 balanceOf を RPC で呼ぶ
// ─────────────────────────────────────────────────────────────

function encodeBalanceOf(address) {
  // balanceOf(address) = function selector 0x70a08231
  const selector = "70a08231";
  const padded = address.toLowerCase().replace("0x", "").padStart(64, "0");
  return "0x" + selector + padded;
}

async function rpcCall(endpoint, method, params) {
  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: Date.now(),
      method,
      params,
    }),
  });
  if (!res.ok) {
    throw new Error(`RPC ${endpoint} returned ${res.status}`);
  }
  const data = await res.json();
  if (data.error) {
    throw new Error(`RPC error: ${JSON.stringify(data.error)}`);
  }
  return data.result;
}

async function rpcCallWithFallback(method, params) {
  let lastErr;
  for (const endpoint of BASE_RPC_ENDPOINTS) {
    try {
      return await rpcCall(endpoint, method, params);
    } catch (err) {
      lastErr = err;
      // 次の endpoint を試す
    }
  }
  throw lastErr || new Error("all RPC endpoints failed");
}

async function getUSDCBalance(wallet) {
  const data = encodeBalanceOf(wallet);
  const result = await rpcCallWithFallback("eth_call", [
    {
      to: USDC_CONTRACT,
      data,
    },
    "latest",
  ]);
  // result は 0x プレフィックスの hex string
  const balanceWei = BigInt(result);
  const divisor = 10n ** BigInt(USDC_DECIMALS);
  const wholeUnits = Number(balanceWei / divisor);
  const fraction = Number(balanceWei % divisor) / Number(divisor);
  return wholeUnits + fraction;
}

async function getBlockNumber() {
  const result = await rpcCallWithFallback("eth_blockNumber", []);
  return parseInt(result, 16);
}

// ─────────────────────────────────────────────────────────────
// Snapshot 取得
// ─────────────────────────────────────────────────────────────

export async function takeSnapshot() {
  const cfg = await loadConfig();
  if (!cfg.wallet) {
    throw new Error(
      "OWNER_WALLET not set. Run: export OWNER_WALLET=0x... or edit config.json"
    );
  }

  const [balance, blockNumber] = await Promise.all([
    getUSDCBalance(cfg.wallet),
    getBlockNumber(),
  ]);

  const snapshot = {
    at: new Date().toISOString(),
    wallet: cfg.wallet,
    network: cfg.network,
    currency: cfg.currency,
    block_number: blockNumber,
    balance_usdc: balance,
  };

  // snapshots 履歴に追記
  const snapshots = await loadJson(SNAPSHOTS_FILE, { history: [] });
  snapshots.history.push(snapshot);
  // 直近 500 件まで保持
  if (snapshots.history.length > 500) {
    snapshots.history = snapshots.history.slice(-500);
  }
  await saveJson(SNAPSHOTS_FILE, snapshots);

  // summary を更新
  const summary = await loadJson(SUMMARY_FILE, {
    first_seen_at: null,
    last_seen_at: null,
    first_balance: null,
    last_balance: null,
    cumulative_diff: 0,
    peak_balance: 0,
  });

  if (summary.first_seen_at === null) {
    summary.first_seen_at = snapshot.at;
    summary.first_balance = balance;
  }
  const prevBalance = summary.last_balance ?? balance;
  const diff = balance - prevBalance;
  summary.last_seen_at = snapshot.at;
  summary.last_balance = balance;
  if (diff > 0) {
    summary.cumulative_diff += diff;
  }
  if (balance > summary.peak_balance) {
    summary.peak_balance = balance;
  }
  await saveJson(SUMMARY_FILE, summary);

  return { snapshot, diff, summary };
}

// ─────────────────────────────────────────────────────────────
// レポート生成
// ─────────────────────────────────────────────────────────────

export async function generateReport() {
  const snapshots = await loadJson(SNAPSHOTS_FILE, { history: [] });
  const summary = await loadJson(SUMMARY_FILE, {});
  const cfg = await loadConfig();

  const last = snapshots.history[snapshots.history.length - 1];
  const prev = snapshots.history[snapshots.history.length - 2];

  return {
    wallet: cfg.wallet,
    network: cfg.network,
    currency: cfg.currency,
    current_balance_usdc: last?.balance_usdc ?? null,
    last_snapshot_at: last?.at ?? null,
    previous_balance_usdc: prev?.balance_usdc ?? null,
    diff_since_previous: last && prev ? last.balance_usdc - prev.balance_usdc : 0,
    snapshot_count: snapshots.history.length,
    summary,
    estimated_jpy: last ? Math.round(last.balance_usdc * 150) : 0, // 1 USD = ¥150 概算
  };
}

// ─────────────────────────────────────────────────────────────
// watch モード（長時間実行）
// ─────────────────────────────────────────────────────────────

export async function watch() {
  const cfg = await loadConfig();
  console.log(
    `[revenue_watcher] watching ${cfg.wallet} on ${cfg.network} every ${cfg.poll_interval_ms / 1000}s`
  );
  while (true) {
    try {
      const result = await takeSnapshot();
      const { snapshot, diff } = result;
      console.log(
        `[revenue_watcher] ${snapshot.at} balance=${snapshot.balance_usdc} USDC (diff ${diff > 0 ? "+" : ""}${diff.toFixed(6)})`
      );
      if (diff > 0) {
        console.log(
          `🎉 [revenue_watcher] REVENUE DETECTED: +${diff} USDC (≈¥${Math.round(diff * 150)})`
        );
      }
    } catch (err) {
      console.error(`[revenue_watcher] error: ${err.message}`);
    }
    await new Promise((r) => setTimeout(r, cfg.poll_interval_ms));
  }
}

// ─────────────────────────────────────────────────────────────
// CLI
// ─────────────────────────────────────────────────────────────

const isMain = import.meta.url === `file://${process.argv[1]}`;
if (isMain) {
  const cmd = process.argv[2] || "report";

  if (cmd === "snapshot") {
    const result = await takeSnapshot();
    console.log(JSON.stringify(result, null, 2));
  } else if (cmd === "report") {
    const report = await generateReport();
    console.log(JSON.stringify(report, null, 2));
  } else if (cmd === "watch") {
    await watch();
  } else if (cmd === "config") {
    const cfg = await loadConfig();
    console.log(JSON.stringify(cfg, null, 2));
  } else if (cmd === "set-wallet") {
    const addr = process.argv[3];
    if (!addr || !addr.startsWith("0x") || addr.length !== 42) {
      console.error("Usage: set-wallet 0x...");
      process.exit(1);
    }
    const cfg = await loadConfig();
    cfg.wallet = addr;
    await saveConfig(cfg);
    console.log(`wallet set to ${addr}`);
  } else {
    console.error(`Unknown command: ${cmd}`);
    console.error(
      "Usage: node revenue_watcher.mjs [snapshot|report|watch|config|set-wallet <addr>]"
    );
    process.exit(1);
  }
}
