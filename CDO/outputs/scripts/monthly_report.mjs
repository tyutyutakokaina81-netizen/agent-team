#!/usr/bin/env node
// 月次レポート生成スクリプト
// 依存ゼロ（Node 標準モジュールのみ使用）
// 用途：A受注 / B営業パイプライン / 経費 の3CSVを読んで月次サマリmdを出力
//
// 使い方:
//   node CDO/outputs/scripts/monthly_report.mjs <YYYY-MM> [--out=path]
// 例:
//   node CDO/outputs/scripts/monthly_report.mjs 2026-05
//   node CDO/outputs/scripts/monthly_report.mjs 2026-05 --out=CFO/outputs/2026-05_月次サマリ.md
//
// 入力ファイル（存在しない場合はそのセクションをスキップ）:
//   projects/2026-04-08_月30万自動化/A_ライティング/order_tracker_template.csv
//   projects/2026-04-08_月30万自動化/B_SNS運用代行/sales_pipeline_template.csv
//   CFO/templates/2026-05-19_経費管理シート.csv
//
// 実運用では templates ではなく CFO/outputs/ 配下の実データCSVを指す。

import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "../../..");

function parseArgs(argv) {
  const args = { month: null, out: null };
  for (const a of argv.slice(2)) {
    if (a.startsWith("--out=")) args.out = a.slice(6);
    else if (!args.month) args.month = a;
  }
  return args;
}

function parseCSV(text) {
  // シンプルなCSVパーサ（カンマ区切り、ダブルクオートエスケープ対応、改行は LF/CRLF）
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
  const p = path.join(ROOT, rel);
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
  if (!csv) return "_（受注トラッカーCSVが見つかりません）_\n";
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
  const paid = rows.filter(r => r["入金確認"] === "TRUE" || r["入金確認"] === "true" || r["入金確認"] === "1");
  const paidTotal = paid.reduce((s, r) => s + num(r["金額"]), 0);

  let out = "";
  out += `- 受注件数：${rows.length}本\n`;
  out += `- 請求ベース売上：${yen(total)}\n`;
  out += `- 入金確認済み：${paid.length}本 / ${yen(paidTotal)}\n`;
  if (Object.keys(byPlan).length > 0) {
    out += `- プラン別本数：\n`;
    for (const [k, v] of Object.entries(byPlan)) out += `  - ${k}：${v}本\n`;
  }
  if (Object.keys(byStatus).length > 0) {
    out += `- ステータス別本数：\n`;
    for (const [k, v] of Object.entries(byStatus)) out += `  - ${k}：${v}本\n`;
  }
  return out;
}

function buildSalesSection(month, csv) {
  if (!csv) return "_（営業パイプラインCSVが見つかりません）_\n";
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

  let out = "";
  out += `- アプローチ送信：${sent.length}件\n`;
  out += `- 返信獲得：${replied.length}件（返信率 ${replyRate}%）\n`;
  out += `- 商談実施：${meeting.length}件（商談化率 ${meetingRate}%）\n`;
  out += `- 受注：${won.length}社 / ${yen(wonTotal)}（成約率 ${winRate}%）\n`;
  if (Object.keys(byIndustry).length > 0) {
    out += `- 業種別アプローチ数：\n`;
    for (const [k, v] of Object.entries(byIndustry)) out += `  - ${k}：${v}件\n`;
  }
  const lostReasons = csv.rows
    .filter(r => r["ステータス"] === "失注" && inMonth(r["商談日"], month) && r["失注理由"])
    .map(r => r["失注理由"]);
  if (lostReasons.length > 0) {
    out += `- 失注理由（${lostReasons.length}件）：\n`;
    for (const reason of lostReasons) out += `  - ${reason}\n`;
  }
  return out;
}

function buildExpenseSection(month, csv) {
  if (!csv) return "_（経費管理CSVが見つかりません）_\n";
  const rows = csv.rows.filter(r => inMonth(r["日付"], month));
  if (rows.length === 0) return "_（当月の経費レコードなし）_\n";
  const byAccount = {};
  let total = 0;
  for (const r of rows) {
    const acc = r["科目"] || "未設定";
    const amount = num(r["金額"]);
    const ratio = String(r["事業按分"] || "100%").replace("%", "");
    const ratioNum = num(ratio) / 100;
    const calc = amount * ratioNum;
    byAccount[acc] = (byAccount[acc] || 0) + calc;
    total += calc;
  }
  let out = "";
  out += `- 当月経費合計（按分後）：${yen(total)}\n`;
  out += `- 科目別内訳：\n`;
  for (const [k, v] of Object.entries(byAccount)) out += `  - ${k}：${yen(v)}\n`;
  return out;
}

function buildReport(month, sources) {
  const now = new Date().toISOString().slice(0, 10);
  let md = "";
  md += `# 月次サマリ（${month}）\n\n`;
  md += `生成日：${now}\n`;
  md += `生成元：CDO/outputs/scripts/monthly_report.mjs\n\n`;
  md += `---\n\n`;
  md += `## A：ライティング受注\n\n`;
  md += buildOrderSection(month, sources.order);
  md += `\n## B：SNS運用代行 営業パイプライン\n\n`;
  md += buildSalesSection(month, sources.sales);
  md += `\n## 経費\n\n`;
  md += buildExpenseSection(month, sources.expense);
  md += `\n## 損益（簡易）\n\n`;
  const orderTotal = sources.order
    ? sources.order.rows.filter(r => inMonth(r["受注日"], month)).reduce((s, r) => s + num(r["金額"]), 0)
    : 0;
  const salesTotal = sources.sales
    ? sources.sales.rows.filter(r => inMonth(r["契約開始日"], month)).reduce((s, r) => s + num(r["受注金額"]), 0)
    : 0;
  const expenseTotal = sources.expense
    ? sources.expense.rows.filter(r => inMonth(r["日付"], month)).reduce((s, r) => {
        const amount = num(r["金額"]);
        const ratio = num(String(r["事業按分"] || "100%").replace("%", "")) / 100;
        return s + amount * ratio;
      }, 0)
    : 0;
  const revenue = orderTotal + salesTotal;
  const profit = revenue - expenseTotal;
  md += `- A売上（請求ベース）：${yen(orderTotal)}\n`;
  md += `- B売上（契約開始月）：${yen(salesTotal)}\n`;
  md += `- 売上合計：${yen(revenue)}\n`;
  md += `- 経費合計：${yen(expenseTotal)}\n`;
  md += `- 当月利益：${yen(profit)}\n\n`;
  md += `_注：C テンプレ販売（note/BOOTH）の売上は別途プラットフォームから取得し、CFO/outputs/ の月次サマリに手動追記してください。_\n`;
  return md;
}

function main() {
  const args = parseArgs(process.argv);
  if (!args.month || !/^\d{4}-\d{2}$/.test(args.month)) {
    console.error("使い方: node monthly_report.mjs <YYYY-MM> [--out=path]");
    process.exit(1);
  }
  const sources = {
    order: readCSVSafe("projects/2026-04-08_月30万自動化/A_ライティング/order_tracker_template.csv"),
    sales: readCSVSafe("projects/2026-04-08_月30万自動化/B_SNS運用代行/sales_pipeline_template.csv"),
    expense: readCSVSafe("CFO/templates/2026-05-19_経費管理シート.csv"),
  };
  const md = buildReport(args.month, sources);
  if (args.out) {
    const outPath = path.isAbsolute(args.out) ? args.out : path.join(ROOT, args.out);
    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    fs.writeFileSync(outPath, md, "utf8");
    console.log(`written: ${outPath}`);
  } else {
    process.stdout.write(md);
  }
}

main();
