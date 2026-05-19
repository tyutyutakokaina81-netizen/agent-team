#!/usr/bin/env node
// 月次レポート生成スクリプト
// 依存ゼロ（Node 標準モジュールのみ使用）
// 用途：A受注 / B営業パイプライン / 経費 / C テンプレ販売 の4CSVを読んで月次サマリmdを出力
//
// 使い方:
//   node CDO/outputs/scripts/monthly_report.mjs <YYYY-MM> [options]
//
// オプション:
//   --out=path           出力ファイルパス（未指定なら標準出力）
//   --slack              SLACK_WEBHOOK_URL 環境変数の Webhook URL にサマリ送信
//   --c-csv=path         C テンプレ販売の売上CSV（noteエクスポート等）を指定
//   --quiet              標準出力への本文表示を抑制（--out / --slack 利用時用）
//
// 例:
//   node monthly_report.mjs 2026-05
//   node monthly_report.mjs 2026-05 --out=CFO/outputs/2026-05_月次サマリ.md
//   SLACK_WEBHOOK_URL=https://hooks.slack.com/... \
//     node monthly_report.mjs 2026-05 --out=CFO/outputs/2026-05_月次サマリ.md --slack --quiet
//   node monthly_report.mjs 2026-05 --c-csv=CFO/outputs/2026-05_note_sales.csv
//
// 入力ファイル（存在しない場合はそのセクションをスキップ）:
//   projects/2026-04-08_月30万自動化/A_ライティング/order_tracker_template.csv
//   projects/2026-04-08_月30万自動化/B_SNS運用代行/sales_pipeline_template.csv
//   CFO/templates/2026-05-19_経費管理シート.csv
//   C: --c-csv で指定したファイル（列例：販売日,商品名,価格,プラットフォーム,数量,合計金額）
//
// 実運用では templates ではなく CFO/outputs/ 配下の実データCSVを指す。

import fs from "node:fs";
import path from "node:path";
import https from "node:https";
import http from "node:http";

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "../../..");

function parseArgs(argv) {
  const args = { month: null, out: null, slack: false, cCsv: null, quiet: false };
  for (const a of argv.slice(2)) {
    if (a.startsWith("--out=")) args.out = a.slice(6);
    else if (a === "--slack") args.slack = true;
    else if (a.startsWith("--c-csv=")) args.cCsv = a.slice(8);
    else if (a === "--quiet") args.quiet = true;
    else if (!args.month) args.month = a;
  }
  return args;
}

function parseCSV(text) {
  const lines = text.replace(/\r\n/g, "\n").split("\n").filter(l => l.length > 0);
  if (lines.length === 0) return { headers: [], rows: [] };
  const parseLine = (line) => {
    const out = [];
    let cur = "";
    let inQ = false;
    for (let i = 0; i < line.length; i++) {
      const c = line[i];
      if (inQ) {
        if (c === '"' && line[i + 1] === '"') { cur += '"'; i++; }
        else if (c === '"') { inQ = false; }
        else cur += c;
      } else {
        if (c === '"') inQ = true;
        else if (c === ",") { out.push(cur); cur = ""; }
        else cur += c;
      }
    }
    out.push(cur);
    return out;
  };
  const headers = parseLine(lines[0]);
  const rows = lines.slice(1).map(l => {
    const cols = parseLine(l);
    const o = {};
    headers.forEach((h, i) => { o[h] = (cols[i] ?? "").trim(); });
    return o;
  });
  return { headers, rows };
}

function readCSVSafe(rel) {
  const p = path.isAbsolute(rel) ? rel : path.join(ROOT, rel);
  if (!fs.existsSync(p)) return null;
  return parseCSV(fs.readFileSync(p, "utf8"));
}

function yen(n) {
  if (Number.isNaN(n) || n === undefined || n === null) return "¥0";
  return "¥" + Number(n).toLocaleString("ja-JP");
}

function num(s) {
  if (s === undefined || s === null || s === "") return 0;
  const n = Number(String(s).replace(/[,¥\s]/g, ""));
  return Number.isNaN(n) ? 0 : n;
}

function inMonth(dateStr, ym) {
  if (!dateStr) return false;
  return String(dateStr).startsWith(ym);
}

function buildOrderSection(month, csv) {
  if (!csv) return { md: "_（受注トラッカーCSVが見つかりません）_\n", total: 0 };
  const rows = csv.rows.filter(r => inMonth(r["受注日"], month));
  const total = rows.reduce((s, r) => s + num(r["金額"]), 0);
  const byPlan = {};
  for (const r of rows) {
    const p = r["プラン"] || "未設定";
    byPlan[p] = (byPlan[p] || 0) + 1;
  }
  const byStatus = {};
  for (const r of rows) {
    const s = r["ステータス"] || "未設定";
    byStatus[s] = (byStatus[s] || 0) + 1;
  }
  const paid = rows.filter(r => ["TRUE", "true", "1"].includes(r["入金確認"]));
  const paidTotal = paid.reduce((s, r) => s + num(r["金額"]), 0);

  let md = "";
  md += `- 受注件数：${rows.length}本\n`;
  md += `- 請求ベース売上：${yen(total)}\n`;
  md += `- 入金確認済み：${paid.length}本 / ${yen(paidTotal)}\n`;
  if (Object.keys(byPlan).length > 0) {
    md += `- プラン別本数：\n`;
    for (const [k, v] of Object.entries(byPlan)) md += `  - ${k}：${v}本\n`;
  }
  if (Object.keys(byStatus).length > 0) {
    md += `- ステータス別本数：\n`;
    for (const [k, v] of Object.entries(byStatus)) md += `  - ${k}：${v}本\n`;
  }
  return { md, total };
}

function buildSalesSection(month, csv) {
  if (!csv) return { md: "_（営業パイプラインCSVが見つかりません）_\n", total: 0 };
  const sent = csv.rows.filter(r => inMonth(r["初回送信日"], month));
  const replied = csv.rows.filter(r => inMonth(r["返信日"], month));
  const meeting = csv.rows.filter(r => inMonth(r["商談日"], month));
  const won = csv.rows.filter(r => inMonth(r["契約開始日"], month));
  const wonTotal = won.reduce((s, r) => s + num(r["受注金額"]), 0);

  const byIndustry = {};
  for (const r of sent) {
    const k = r["業種"] || "未設定";
    byIndustry[k] = (byIndustry[k] || 0) + 1;
  }
  const replyRate = sent.length > 0 ? (replied.length / sent.length * 100).toFixed(1) : "0.0";
  const meetingRate = replied.length > 0 ? (meeting.length / replied.length * 100).toFixed(1) : "0.0";
  const winRate = meeting.length > 0 ? (won.length / meeting.length * 100).toFixed(1) : "0.0";

  let md = "";
  md += `- アプローチ送信：${sent.length}件\n`;
  md += `- 返信獲得：${replied.length}件（返信率 ${replyRate}%）\n`;
  md += `- 商談実施：${meeting.length}件（商談化率 ${meetingRate}%）\n`;
  md += `- 受注：${won.length}社 / ${yen(wonTotal)}（成約率 ${winRate}%）\n`;
  if (Object.keys(byIndustry).length > 0) {
    md += `- 業種別アプローチ数：\n`;
    for (const [k, v] of Object.entries(byIndustry)) md += `  - ${k}：${v}件\n`;
  }
  const lostReasons = csv.rows
    .filter(r => r["ステータス"] === "失注" && inMonth(r["商談日"], month) && r["失注理由"])
    .map(r => r["失注理由"]);
  if (lostReasons.length > 0) {
    md += `- 失注理由（${lostReasons.length}件）：\n`;
    for (const reason of lostReasons) md += `  - ${reason}\n`;
  }
  return { md, total: wonTotal };
}

function buildTemplateSection(month, csv) {
  if (!csv) {
    return {
      md: "_（C テンプレ販売CSV未指定。--c-csv=path で指定すると集計します）_\n",
      total: 0
    };
  }
  const rows = csv.rows.filter(r => inMonth(r["販売日"], month));
  if (rows.length === 0) return { md: "_（当月のC売上レコードなし）_\n", total: 0 };
  const byProduct = {};
  const byPlatform = {};
  let total = 0;
  for (const r of rows) {
    const product = r["商品名"] || "未設定";
    const platform = r["プラットフォーム"] || "未設定";
    const amount = num(r["合計金額"]) || (num(r["価格"]) * num(r["数量"] || 1));
    byProduct[product] = (byProduct[product] || 0) + amount;
    byPlatform[platform] = (byPlatform[platform] || 0) + amount;
    total += amount;
  }
  let md = "";
  md += `- 当月販売数：${rows.length}件\n`;
  md += `- C 売上合計：${yen(total)}\n`;
  md += `- 商品別売上：\n`;
  for (const [k, v] of Object.entries(byProduct)) md += `  - ${k}：${yen(v)}\n`;
  md += `- プラットフォーム別：\n`;
  for (const [k, v] of Object.entries(byPlatform)) md += `  - ${k}：${yen(v)}\n`;
  return { md, total };
}

function buildExpenseSection(month, csv) {
  if (!csv) return { md: "_（経費管理CSVが見つかりません）_\n", total: 0 };
  const rows = csv.rows.filter(r => inMonth(r["日付"], month));
  if (rows.length === 0) return { md: "_（当月の経費レコードなし）_\n", total: 0 };
  const byAccount = {};
  let total = 0;
  for (const r of rows) {
    const acc = r["科目"] || "未設定";
    const amount = num(r["金額"]);
    const ratio = num(String(r["事業按分"] || "100%").replace("%", "")) / 100;
    const calc = amount * ratio;
    byAccount[acc] = (byAccount[acc] || 0) + calc;
    total += calc;
  }
  let md = "";
  md += `- 当月経費合計（按分後）：${yen(total)}\n`;
  md += `- 科目別内訳：\n`;
  for (const [k, v] of Object.entries(byAccount)) md += `  - ${k}：${yen(v)}\n`;
  return { md, total };
}

function buildReport(month, sources) {
  const now = new Date().toISOString().slice(0, 10);
  const order = buildOrderSection(month, sources.order);
  const sales = buildSalesSection(month, sources.sales);
  const cTpl = buildTemplateSection(month, sources.cSales);
  const exp = buildExpenseSection(month, sources.expense);

  const revenue = order.total + sales.total + cTpl.total;
  const profit = revenue - exp.total;

  let md = "";
  md += `# 月次サマリ（${month}）\n\n`;
  md += `生成日：${now}\n`;
  md += `生成元：CDO/outputs/scripts/monthly_report.mjs\n\n`;
  md += `---\n\n`;
  md += `## A：ライティング受注\n\n${order.md}\n`;
  md += `## B：SNS運用代行 営業パイプライン\n\n${sales.md}\n`;
  md += `## C：テンプレ販売\n\n${cTpl.md}\n`;
  md += `## 経費\n\n${exp.md}\n`;
  md += `## 損益（簡易）\n\n`;
  md += `- A売上（請求ベース）：${yen(order.total)}\n`;
  md += `- B売上（契約開始月）：${yen(sales.total)}\n`;
  md += `- C売上（テンプレ販売）：${yen(cTpl.total)}\n`;
  md += `- **売上合計：${yen(revenue)}**\n`;
  md += `- 経費合計：${yen(exp.total)}\n`;
  md += `- **当月利益：${yen(profit)}**\n`;

  return { md, totals: { revenue, profit, order: order.total, sales: sales.total, cTpl: cTpl.total, expense: exp.total } };
}

function buildSlackPayload(month, totals) {
  const fmt = (n) => "¥" + Number(n).toLocaleString("ja-JP");
  const blocks = [
    { type: "header", text: { type: "plain_text", text: `月次サマリ ${month}` } },
    {
      type: "section",
      fields: [
        { type: "mrkdwn", text: `*A 売上*\n${fmt(totals.order)}` },
        { type: "mrkdwn", text: `*B 売上*\n${fmt(totals.sales)}` },
        { type: "mrkdwn", text: `*C 売上*\n${fmt(totals.cTpl)}` },
        { type: "mrkdwn", text: `*経費*\n${fmt(totals.expense)}` },
        { type: "mrkdwn", text: `*売上合計*\n${fmt(totals.revenue)}` },
        { type: "mrkdwn", text: `*当月利益*\n${fmt(totals.profit)}` }
      ]
    },
    { type: "context", elements: [{ type: "mrkdwn", text: `生成: CDO/outputs/scripts/monthly_report.mjs` }] }
  ];
  return { text: `月次サマリ ${month}`, blocks };
}

function postSlack(webhookUrl, payload) {
  return new Promise((resolve, reject) => {
    let u;
    try { u = new URL(webhookUrl); } catch (e) { return reject(new Error("Invalid SLACK_WEBHOOK_URL")); }
    const lib = u.protocol === "https:" ? https : http;
    const body = JSON.stringify(payload);
    const req = lib.request({
      method: "POST",
      hostname: u.hostname,
      port: u.port || (u.protocol === "https:" ? 443 : 80),
      path: u.pathname + u.search,
      headers: { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(body) }
    }, (res) => {
      let data = "";
      res.on("data", (c) => data += c);
      res.on("end", () => {
        if (res.statusCode >= 200 && res.statusCode < 300) resolve({ status: res.statusCode, body: data });
        else reject(new Error(`Slack POST failed: ${res.statusCode} ${data}`));
      });
    });
    req.on("error", reject);
    req.write(body);
    req.end();
  });
}

async function main() {
  const args = parseArgs(process.argv);
  if (!args.month || !/^\d{4}-\d{2}$/.test(args.month)) {
    console.error("使い方: node monthly_report.mjs <YYYY-MM> [--out=path] [--slack] [--c-csv=path] [--quiet]");
    process.exit(1);
  }
  const sources = {
    order: readCSVSafe("projects/2026-04-08_月30万自動化/A_ライティング/order_tracker_template.csv"),
    sales: readCSVSafe("projects/2026-04-08_月30万自動化/B_SNS運用代行/sales_pipeline_template.csv"),
    expense: readCSVSafe("CFO/templates/2026-05-19_経費管理シート.csv"),
    cSales: args.cCsv ? readCSVSafe(args.cCsv) : null,
  };
  const { md, totals } = buildReport(args.month, sources);

  if (args.out) {
    const outPath = path.isAbsolute(args.out) ? args.out : path.join(ROOT, args.out);
    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    fs.writeFileSync(outPath, md, "utf8");
    if (!args.quiet) console.log(`written: ${outPath}`);
  } else if (!args.quiet) {
    process.stdout.write(md);
  }

  if (args.slack) {
    const webhook = process.env.SLACK_WEBHOOK_URL;
    if (!webhook) {
      console.error("SLACK_WEBHOOK_URL が未設定です。環境変数で指定してください。");
      process.exit(2);
    }
    try {
      await postSlack(webhook, buildSlackPayload(args.month, totals));
      if (!args.quiet) console.log("slack: posted");
    } catch (e) {
      console.error(`slack: ${e.message}`);
      process.exit(3);
    }
  }
}

main();
