#!/usr/bin/env node
// autonomous/cfo_report.mjs — CFO リアルタイム財務レポート
// Usage: node autonomous/cfo_report.mjs [daily|status|monthly]

import { readFile, readdir, writeFile, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(__dirname, '..');
const STATE = path.join(__dirname, 'state');
const PRODUCTS = path.join(__dirname, 'products');
const REPORT_DIR = path.join(REPO, 'CFO', 'outputs', 'reports');
const USD_JPY = 150;

async function sj(f, d) {
  if (!existsSync(f)) return d;
  try { return JSON.parse(await readFile(f, 'utf8')); } catch { return d; }
}
const today = () => new Date().toISOString().slice(0, 10);
const now = () => new Date().toISOString();

async function getBudget() {
  const d = await sj(path.join(STATE, 'budget', 'daily_spend.json'), {});
  const m = await sj(path.join(STATE, 'budget', 'monthly_spend.json'), {});
  const t = today(), mo = t.slice(0, 7);
  return { today: d[t]||0, month: m[mo]||0, dLim: 100, mLim: 2000 };
}

async function getRevenue() {
  const s = await sj(path.join(STATE, 'revenue', 'summary.json'), null);
  const sn = await sj(path.join(STATE, 'revenue', 'snapshots.json'), { history: [] });
  const bal = sn.history?.[sn.history.length-1]?.balance_usdc ?? 0;
  const cum = s?.cumulative_diff ?? 0;
  return { bal, cum, jpy: Math.round(cum * USD_JPY) };
}

async function getProducts() {
  if (!existsSync(PRODUCTS)) return [];
  const es = await readdir(PRODUCTS, { withFileTypes: true });
  const out = [];
  for (const e of es) {
    if (!e.isDirectory()) continue;
    const p = await sj(path.join(PRODUCTS, e.name, 'package.json'), null);
    if (!p) continue;
    let dc = 0;
    const dd = path.join(PRODUCTS, e.name, 'data');
    if (existsSync(dd)) {
      for (const f of await readdir(dd).catch(()=>[])) {
        if (!f.endsWith('.json')) continue;
        const j = await sj(path.join(dd, f), {});
        const a = Object.values(j).find(v => Array.isArray(v));
        if (a) dc += a.length;
      }
    }
    out.push({ name: e.name, ver: p.version, dc });
  }
  return out;
}

async function daily() {
  const b = await getBudget(), r = await getRevenue(), p = await getProducts();
  const cl = 30000, sub = 2800, auto = b.month;
  const tot = cl + sub + auto, net = r.jpy - tot;
  const rw = net >= 0 ? '∞' : `${Math.abs(Math.floor(100000/(tot-r.jpy)))}m`;

  return `# CFO Daily Report — ${today()}
Generated: ${now()}

## Summary
| Metric | Value |
|---|---|
| Runway | ${rw} (¥100K budget) |
| MTD Revenue | $${r.cum.toFixed(4)} USDC (≈¥${r.jpy}) |
| MTD Cost | ¥${tot.toLocaleString()} |
| MTD Net | **¥${net.toLocaleString()}** |
| MCP Portfolio | ${p.length} deployed |
| Total Data | ${p.reduce((s,x)=>s+x.dc,0)} records |

## Costs (MTD)
| Item | Amount |
|---|---|
| Claude personal | ¥${cl.toLocaleString()} |
| Auto loop API | ¥${auto.toFixed(0)} |
| Subscriptions | ¥${sub.toLocaleString()} |
| Cloudflare | ¥0 |
| **Total** | **¥${tot.toLocaleString()}** |

## Revenue (MTD)
| Source | Amount |
|---|---|
| USDC (x402) | $${r.cum.toFixed(4)} (≈¥${r.jpy}) |
| **Total** | **¥${r.jpy}** |

## Products
| MCP | Ver | Data | Status |
|---|---|---|---|
${p.map(x=>`| ${x.name} | ${x.ver} | ${x.dc} | deployed |`).join('\n')||'| (none) | — | — | — |'}

## Auto Loop Budget
| Metric | Value |
|---|---|
| Today | ¥${b.today.toFixed(2)} / ¥${b.dLim} |
| Month | ¥${b.month.toFixed(2)} / ¥${b.mLim} |

## Risks
${net<-30000?'- 🔴 Monthly deficit exceeds ¥30K\n':''}${r.jpy===0?'- 🟡 Zero revenue — discovery needed\n':''}${p.length<5?`- 🟡 Only ${p.length} MCP(s) — target 30\n`:''}
## Next Actions
1. ${r.jpy===0?'Create Coinbase Wallet → update SERVER_ADDRESS':'Monitor revenue trend'}
2. Expand MCP portfolio: ${p.length} → ${p.length+5}
3. Launch Zenn/HN for organic discovery

---
*cfo_report.mjs — autonomous CFO*
`;
}

async function status() {
  const b = await getBudget(), r = await getRevenue(), p = await getProducts();
  const tot = 30000+2800+b.month, net = r.jpy-tot;
  return `[CFO] ${today()} | MCP:${p.length} | Rev:¥${r.jpy} | Cost:¥${tot} | Net:¥${net} | Loop:¥${b.month.toFixed(0)}/${b.mLim}`;
}

const cmd = process.argv[2]||'daily';
if (cmd==='status') { console.log(await status()); }
else if (cmd==='daily'||cmd==='report'||cmd==='monthly') {
  const rpt = await daily();
  console.log(rpt);
  await mkdir(REPORT_DIR, { recursive: true });
  const f = path.join(REPORT_DIR, `${today()}_${cmd}.md`);
  await writeFile(f, rpt, 'utf8');
  console.error(`[cfo] saved: ${path.relative(REPO, f)}`);
} else { console.error('Usage: cfo_report.mjs [daily|status|monthly]'); process.exit(1); }
