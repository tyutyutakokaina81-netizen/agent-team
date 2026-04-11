// dashboard.mjs
// Always-On Company の Review Dashboard サーバー。
//
// オーナーが週末10分でスマホから覗くことを想定した、zero-dep HTTP サーバー。
// 承認ボタンは意図的に置かない（未承認でも AI は動き続ける設計）。
// 閲覧専用。
//
// 起動:
//   node autonomous/dashboard.mjs                  # 3002
//   DASHBOARD_PORT=8080 node autonomous/dashboard.mjs
//
// エンドポイント:
//   GET /              → HTML ダッシュボード
//   GET /api/budget    → 予算サマリ JSON
//   GET /api/memory    → 全役職の記憶サマリ JSON
//   GET /api/queue     → task_queue 内容 JSON
//   GET /api/loops     → 直近の daily_loop_*.md 一覧 JSON
//   GET /api/products  → autonomous/products/ の一覧とメタ情報 JSON
//   GET /api/revenue   → revenue_watcher の summary / snapshots JSON
//   GET /api/health    → ヘルスチェック

import { createServer } from 'node:http';
import { readFile, readdir, stat } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import * as budget from './budget_guard.mjs';
import * as memory from './memory.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, '..');
const TASK_QUEUE_FILE = path.join(__dirname, 'state', 'task_queue.json');
const PRODUCTS_DIR = path.join(__dirname, 'products');
const REVENUE_SUMMARY_FILE = path.join(__dirname, 'state', 'revenue', 'summary.json');
const REVENUE_SNAPSHOTS_FILE = path.join(__dirname, 'state', 'revenue', 'snapshots.json');

const PORT = parseInt(process.env.DASHBOARD_PORT || '3002', 10);
const HOST = process.env.DASHBOARD_HOST || '0.0.0.0';

// ─────────────────────────────────────────────────────────────
// データ取得
// ─────────────────────────────────────────────────────────────

async function getBudget() {
  return await budget.summary();
}

async function getMemory() {
  return await memory.allSummary();
}

async function getQueue() {
  if (!existsSync(TASK_QUEUE_FILE)) return { queue: [] };
  try {
    return JSON.parse(await readFile(TASK_QUEUE_FILE, 'utf8'));
  } catch {
    return { queue: [], error: 'parse failed' };
  }
}

async function getRecentLoops(limit = 14) {
  const loopDir = path.join(REPO_ROOT, 'CDO', 'research');
  if (!existsSync(loopDir)) return [];
  try {
    const files = await readdir(loopDir);
    const loopFiles = files
      .filter(f => /^daily_loop_\d{4}-\d{2}-\d{2}\.md$/.test(f))
      .sort()
      .reverse()
      .slice(0, limit);

    const loops = [];
    for (const f of loopFiles) {
      const content = await readFile(path.join(loopDir, f), 'utf8');
      const date = f.match(/(\d{4}-\d{2}-\d{2})/)?.[1] || '';
      loops.push({ filename: f, date, preview: content.slice(0, 2000) });
    }
    return loops;
  } catch {
    return [];
  }
}

async function getProducts() {
  if (!existsSync(PRODUCTS_DIR)) return [];
  try {
    const entries = await readdir(PRODUCTS_DIR, { withFileTypes: true });
    const products = [];
    for (const entry of entries) {
      if (!entry.isDirectory()) continue;
      const productDir = path.join(PRODUCTS_DIR, entry.name);
      const pkgPath = path.join(productDir, 'package.json');
      const wranglerPath = path.join(productDir, 'wrangler.toml');
      const dataDir = path.join(productDir, 'data');

      const product = {
        name: entry.name,
        has_code: existsSync(path.join(productDir, 'src')),
        has_wrangler: existsSync(wranglerPath),
        deployed: false, // 後で actual deploy 状態を見る
      };

      if (existsSync(pkgPath)) {
        try {
          const pkg = JSON.parse(await readFile(pkgPath, 'utf8'));
          product.version = pkg.version;
          product.description = pkg.description;
        } catch { /* skip */ }
      }

      // data/ の件数
      if (existsSync(dataDir)) {
        try {
          const dataFiles = await readdir(dataDir);
          const jsonFiles = dataFiles.filter(f => f.endsWith('.json'));
          if (jsonFiles.length > 0) {
            const firstData = JSON.parse(await readFile(path.join(dataDir, jsonFiles[0]), 'utf8'));
            product.data_count = firstData._meta?.count ?? Object.keys(firstData).filter(k => Array.isArray(firstData[k])).reduce((max, k) => Math.max(max, firstData[k].length), 0);
          }
        } catch { /* skip */ }
      }

      // wrangler.toml から prices を抜く（簡易パース）
      if (existsSync(wranglerPath)) {
        try {
          const toml = await readFile(wranglerPath, 'utf8');
          const priceMatch = toml.match(/X402_PRICE_\w+\s*=\s*"([^"]+)"/g);
          if (priceMatch) {
            product.pricing = priceMatch.map(m => {
              const [, key] = m.match(/X402_PRICE_(\w+)/) || [];
              const [, val] = m.match(/"([^"]+)"/) || [];
              return { endpoint: key?.toLowerCase(), price_usd: val };
            });
          }
        } catch { /* skip */ }
      }

      products.push(product);
    }
    return products;
  } catch {
    return [];
  }
}

async function getRevenue() {
  const out = {
    summary: null,
    latest_snapshot: null,
    snapshot_count: 0,
    estimated_jpy: 0,
  };
  if (existsSync(REVENUE_SUMMARY_FILE)) {
    try {
      out.summary = JSON.parse(await readFile(REVENUE_SUMMARY_FILE, 'utf8'));
    } catch { /* skip */ }
  }
  if (existsSync(REVENUE_SNAPSHOTS_FILE)) {
    try {
      const snap = JSON.parse(await readFile(REVENUE_SNAPSHOTS_FILE, 'utf8'));
      if (Array.isArray(snap.history)) {
        out.snapshot_count = snap.history.length;
        out.latest_snapshot = snap.history[snap.history.length - 1] || null;
      }
    } catch { /* skip */ }
  }
  if (out.latest_snapshot) {
    out.estimated_jpy = Math.round((out.latest_snapshot.balance_usdc || 0) * 150);
  }
  return out;
}

// ─────────────────────────────────────────────────────────────
// HTML ダッシュボード
// ─────────────────────────────────────────────────────────────

async function renderHtml() {
  const [budgetData, memoryData, queueData, loops, products, revenue] = await Promise.all([
    getBudget(),
    getMemory(),
    getQueue(),
    getRecentLoops(7),
    getProducts(),
    getRevenue(),
  ]);

  const html = `<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Always-On Company Dashboard</title>
  <style>
    :root {
      --bg: #0d1117;
      --card: #161b22;
      --text: #c9d1d9;
      --muted: #8b949e;
      --accent: #58a6ff;
      --ok: #3fb950;
      --warn: #d29922;
      --err: #f85149;
      --border: #30363d;
    }
    * { box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", sans-serif;
      background: var(--bg);
      color: var(--text);
      margin: 0;
      padding: 16px;
      line-height: 1.6;
    }
    h1 { font-size: 20px; margin: 0 0 8px; }
    h2 { font-size: 15px; margin: 16px 0 8px; color: var(--accent); }
    .sub { color: var(--muted); font-size: 12px; margin-bottom: 16px; }
    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px 16px;
      margin-bottom: 12px;
    }
    .grid2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }
    .stat {
      font-size: 20px;
      font-weight: 600;
    }
    .stat-label {
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
    }
    .progress {
      width: 100%;
      height: 6px;
      background: var(--border);
      border-radius: 3px;
      overflow: hidden;
      margin-top: 4px;
    }
    .progress-bar {
      height: 100%;
      background: var(--ok);
      transition: width 0.3s;
    }
    .progress-bar.warn { background: var(--warn); }
    .progress-bar.err { background: var(--err); }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }
    th, td {
      text-align: left;
      padding: 6px 8px;
      border-bottom: 1px solid var(--border);
    }
    th { color: var(--muted); font-weight: normal; font-size: 11px; text-transform: uppercase; }
    code, pre { font-family: "SF Mono", Menlo, monospace; font-size: 12px; }
    pre {
      background: #0a0e14;
      padding: 8px;
      border-radius: 6px;
      overflow-x: auto;
      white-space: pre-wrap;
      color: var(--muted);
      max-height: 300px;
      overflow-y: auto;
    }
    .ok { color: var(--ok); }
    .warn { color: var(--warn); }
    .muted { color: var(--muted); font-size: 12px; }
  </style>
</head>
<body>
  <h1>🤖 Always-On Company</h1>
  <div class="sub">自立型AI運営ダッシュボード · 閲覧専用 · 更新: ${new Date().toLocaleString('ja-JP')}</div>

  <div class="card">
    <h2>💰 予算</h2>
    <div class="grid2">
      <div>
        <div class="stat-label">本日 (¥${budgetData.dailyLimit})</div>
        <div class="stat">¥${budgetData.today.toFixed(2)}</div>
        <div class="progress">
          <div class="progress-bar ${pctClass(budgetData.today, budgetData.dailyLimit)}"
               style="width: ${Math.min(100, (budgetData.today / budgetData.dailyLimit) * 100)}%"></div>
        </div>
      </div>
      <div>
        <div class="stat-label">今月 (¥${budgetData.monthlyLimit})</div>
        <div class="stat">¥${budgetData.month.toFixed(2)}</div>
        <div class="progress">
          <div class="progress-bar ${pctClass(budgetData.month, budgetData.monthlyLimit)}"
               style="width: ${Math.min(100, (budgetData.month / budgetData.monthlyLimit) * 100)}%"></div>
        </div>
      </div>
    </div>
    <div class="muted" style="margin-top: 8px;">残り本日 ¥${budgetData.todayRemaining.toFixed(2)} / 今月 ¥${budgetData.monthRemaining.toFixed(2)}${budgetData.revenueGatedMode ? ' · <span class="warn">revenue-gated mode ON</span>' : ''}</div>
  </div>

  <div class="card">
    <h2>💵 収益（USDC on Base）</h2>
    ${revenue.latest_snapshot ? `
    <div class="grid2">
      <div>
        <div class="stat-label">最新残高</div>
        <div class="stat">${revenue.latest_snapshot.balance_usdc.toFixed(4)} USDC</div>
        <div class="muted">≈ ¥${revenue.estimated_jpy.toLocaleString()}</div>
      </div>
      <div>
        <div class="stat-label">累計受領 (diff)</div>
        <div class="stat">${(revenue.summary?.cumulative_diff ?? 0).toFixed(4)} USDC</div>
        <div class="muted">スナップショット ${revenue.snapshot_count} 件</div>
      </div>
    </div>
    ${revenue.latest_snapshot.wallet ? `<div class="muted" style="margin-top: 8px;">wallet: <code>${escapeHtml(revenue.latest_snapshot.wallet.slice(0, 10))}…${escapeHtml(revenue.latest_snapshot.wallet.slice(-4))}</code> / block ${revenue.latest_snapshot.block_number}</div>` : ''}
    ` : '<div class="muted">revenue_watcher snapshot がまだありません。<br>Coinbase Wallet アドレス受領後に <code>node autonomous/revenue_watcher.mjs snapshot</code> を実行してください。</div>'}
  </div>

  <div class="card">
    <h2>📦 Products (${products.length})</h2>
    ${products.length === 0 ? '<div class="muted">(まだプロダクトがありません)</div>' : `
    <table>
      <thead><tr><th>name</th><th>version</th><th>data</th><th>pricing</th><th>deploy</th></tr></thead>
      <tbody>
        ${products.map(p => `<tr>
          <td><strong>${escapeHtml(p.name)}</strong><div class="muted" style="font-size: 11px;">${escapeHtml((p.description || '').slice(0, 60))}</div></td>
          <td>${escapeHtml(p.version || '?')}</td>
          <td>${p.data_count || '—'}</td>
          <td class="muted" style="font-size: 11px;">${p.pricing ? p.pricing.map(x => `${x.endpoint}: $${x.price_usd}`).join('<br>') : '—'}</td>
          <td class="${p.has_wrangler ? 'warn' : 'muted'}">${p.has_wrangler ? 'ready' : '—'}</td>
        </tr>`).join('')}
      </tbody>
    </table>`}
  </div>

  <div class="card">
    <h2>🧠 各役職の短期記憶</h2>
    <table>
      <thead><tr><th>役職</th><th>短期</th><th>長期</th><th>最新の決定</th></tr></thead>
      <tbody>
        ${['CDO', 'CFO', 'CMO', 'CPO', 'CSO'].map(o => {
          const m = memoryData[o] || {};
          return `<tr>
            <td><strong>${o}</strong></td>
            <td>${m.shortTermCount || 0}</td>
            <td>${m.longTermCount || 0}</td>
            <td class="muted">${escapeHtml(m.latestDecision || '—')}</td>
          </tr>`;
        }).join('')}
      </tbody>
    </table>
  </div>

  <div class="card">
    <h2>📬 task_queue (${queueData.queue?.length || 0})</h2>
    ${(queueData.queue && queueData.queue.length > 0)
      ? `<table>
          <thead><tr><th>from</th><th>to</th><th>priority</th><th>message</th></tr></thead>
          <tbody>
            ${queueData.queue.slice(0, 10).map(m => `<tr>
              <td>${escapeHtml(m.from)}</td>
              <td>${escapeHtml(m.to)}</td>
              <td>${escapeHtml(m.priority || 'normal')}</td>
              <td class="muted">${escapeHtml((m.message || '').slice(0, 80))}</td>
            </tr>`).join('')}
          </tbody>
        </table>`
      : '<div class="muted">(空)</div>'}
  </div>

  <div class="card">
    <h2>📅 直近のループ (${loops.length})</h2>
    ${loops.length === 0 ? '<div class="muted">(まだありません)</div>' : loops.map(l => `
      <details${l === loops[0] ? ' open' : ''}>
        <summary><strong>${l.date}</strong> <span class="muted">${l.filename}</span></summary>
        <pre>${escapeHtml(l.preview)}</pre>
      </details>
    `).join('')}
  </div>

  <div class="muted" style="text-align:center; margin-top: 24px;">
    <a href="/api/budget" style="color: var(--muted);">/api/budget</a> ·
    <a href="/api/memory" style="color: var(--muted);">/api/memory</a> ·
    <a href="/api/queue" style="color: var(--muted);">/api/queue</a> ·
    <a href="/api/loops" style="color: var(--muted);">/api/loops</a> ·
    <a href="/api/products" style="color: var(--muted);">/api/products</a> ·
    <a href="/api/revenue" style="color: var(--muted);">/api/revenue</a>
  </div>
</body>
</html>`;
  return html;
}

function pctClass(cur, max) {
  const ratio = cur / max;
  if (ratio >= 0.9) return 'err';
  if (ratio >= 0.6) return 'warn';
  return '';
}

function escapeHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ─────────────────────────────────────────────────────────────
// HTTP handler
// ─────────────────────────────────────────────────────────────

function json(res, data, status = 200) {
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(data, null, 2));
}

const server = createServer(async (req, res) => {
  const start = Date.now();
  try {
    const url = new URL(req.url, `http://${req.headers.host}`);
    const p = url.pathname;

    if (p === '/' || p === '/index.html') {
      const html = await renderHtml();
      res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' });
      res.end(html);
    } else if (p === '/api/health') {
      json(res, { ok: true, time: new Date().toISOString() });
    } else if (p === '/api/budget') {
      json(res, await getBudget());
    } else if (p === '/api/memory') {
      json(res, await getMemory());
    } else if (p === '/api/queue') {
      json(res, await getQueue());
    } else if (p === '/api/loops') {
      json(res, await getRecentLoops(14));
    } else if (p === '/api/products') {
      json(res, await getProducts());
    } else if (p === '/api/revenue') {
      json(res, await getRevenue());
    } else {
      json(res, { error: 'Not Found', path: p }, 404);
    }
  } catch (err) {
    json(res, { error: 'Internal Server Error', message: err.message }, 500);
  } finally {
    const ms = Date.now() - start;
    console.log(`${req.method} ${req.url} ${res.statusCode} ${ms}ms`);
  }
});

const isMain = import.meta.url === `file://${process.argv[1]}`;
if (isMain) {
  server.listen(PORT, HOST, () => {
    console.log(`[dashboard] listening on http://${HOST}:${PORT}`);
    console.log(`[dashboard] open http://localhost:${PORT}/ in a browser`);
  });
}

export default server;
