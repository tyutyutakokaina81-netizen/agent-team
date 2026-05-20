#!/usr/bin/env node
// 入金督促・契約更新アラート生成スクリプト
// 依存ゼロ（Node 標準モジュールのみ）
//
// 入力:
//   A受注：projects/2026-04-08_月30万自動化/A_ライティング/order_tracker_template.csv
//          列：案件ID／受注日／クライアント名／金額／納期／ステータス／納品日／請求書No／入金予定日／入金確認
//   取引先：CFO/templates/2026-05-19_取引先マスター_テンプレ.csv
//          列：取引先ID／取引先名／次回更新日／解約予告期間／取引ステータス／適格請求書発行義務／インボイス登録番号
//
// 出力:
//   1. 入金予定日超過の未入金リスト（A 受注 CSV から）
//   2. 契約更新45日以内のクライアント（取引先 CSV から）
//   3. インボイス番号未登録の要対応リスト
//
// 使い方:
//   node CDO/outputs/scripts/payment_alerts.mjs
//   node CDO/outputs/scripts/payment_alerts.mjs --today=2026-05-19
//   node CDO/outputs/scripts/payment_alerts.mjs --slack --quiet
//   node CDO/outputs/scripts/payment_alerts.mjs \
//     --order-csv=CSO/outputs/2026-05_受注実績.csv \
//     --client-csv=CFO/outputs/2026-05-19_取引先マスター.csv

import fs from "node:fs";
import path from "node:path";
import https from "node:https";
import http from "node:http";

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "../../..");

function parseArgs(argv) {
  const args = { today: null, slack: false, quiet: false, orderCsv: null, clientCsv: null };
  for (const a of argv.slice(2)) {
    if (a.startsWith("--today=")) args.today = a.slice(8);
    else if (a === "--slack") args.slack = true;
    else if (a === "--quiet") args.quiet = true;
    else if (a.startsWith("--order-csv=")) args.orderCsv = a.slice(12);
    else if (a.startsWith("--client-csv=")) args.clientCsv = a.slice(13);
  }
  if (!args.today) args.today = new Date().toISOString().slice(0, 10);
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

function daysDiff(fromYmd, toYmd) {
  if (!fromYmd || !toYmd) return null;
  const a = new Date(fromYmd + "T00:00:00Z").getTime();
  const b = new Date(toYmd + "T00:00:00Z").getTime();
  if (Number.isNaN(a) || Number.isNaN(b)) return null;
  return Math.floor((b - a) / 86400000);
}

function findOverduePayments(order, today) {
  if (!order) return [];
  return order.rows
    .filter(r => {
      const paid = ["TRUE", "true", "1"].includes(r["入金確認"]);
      const due = r["入金予定日"];
      if (paid || !due) return false;
      const d = daysDiff(due, today);
      return d !== null && d > 0;
    })
    .map(r => ({
      案件ID: r["案件ID"],
      クライアント: r["クライアント名"],
      金額: num(r["金額"]),
      入金予定日: r["入金予定日"],
      経過日数: daysDiff(r["入金予定日"], today),
      請求書No: r["請求書No"]
    }))
    .sort((a, b) => b.経過日数 - a.経過日数);
}

function findUpcomingRenewals(client, today) {
  if (!client) return [];
  return client.rows
    .filter(r => {
      if (r["取引ステータス"] !== "アクティブ") return false;
      const next = r["次回更新日"];
      const d = daysDiff(today, next);
      return d !== null && d >= 0 && d <= 45;
    })
    .map(r => ({
      取引先ID: r["取引先ID"],
      取引先名: r["取引先名"],
      次回更新日: r["次回更新日"],
      残日数: daysDiff(today, r["次回更新日"]),
      契約金額: num(r["契約金額（税込）"]),
      解約予告: r["解約予告期間"]
    }))
    .sort((a, b) => a.残日数 - b.残日数);
}

function findInvoiceIssues(client) {
  if (!client) return [];
  return client.rows
    .filter(r => r["適格請求書発行義務"] === "あり" && !r["インボイス登録番号"])
    .map(r => ({
      取引先ID: r["取引先ID"],
      取引先名: r["取引先名"],
      理由: "インボイス発行義務ありだが登録番号未記録"
    }));
}

function buildMarkdown(today, overdue, renewals, invoices) {
  let md = `# 入金督促・契約更新アラート（${today}）\n\n`;
  md += `生成元：CDO/outputs/scripts/payment_alerts.mjs\n\n`;
  md += `---\n\n`;

  md += `## 1. 入金予定日超過（未入金）\n\n`;
  if (overdue.length === 0) {
    md += `_該当なし。問題ありません。_\n\n`;
  } else {
    md += `合計 ${overdue.length}件・${yen(overdue.reduce((s, r) => s + r.金額, 0))}\n\n`;
    md += `| 経過日数 | 案件ID | クライアント | 金額 | 入金予定日 | 請求書No |\n`;
    md += `|---------|--------|------------|------|----------|---------|\n`;
    for (const r of overdue) {
      md += `| ${r.経過日数}日 | ${r.案件ID} | ${r.クライアント} | ${yen(r.金額)} | ${r.入金予定日} | ${r.請求書No || "—"} |\n`;
    }
    md += `\n→ 経過5日以内：1回目リマインドメール、5〜14日：2回目督促、15日以上：電話・契約再確認\n\n`;
  }

  md += `## 2. 契約更新 45日以内\n\n`;
  if (renewals.length === 0) {
    md += `_該当なし。_\n\n`;
  } else {
    md += `合計 ${renewals.length}件\n\n`;
    md += `| 残日数 | 取引先 | 次回更新日 | 月額 | 解約予告 |\n`;
    md += `|--------|--------|----------|------|---------|\n`;
    for (const r of renewals) {
      md += `| ${r.残日数}日 | ${r.取引先名} | ${r.次回更新日} | ${yen(r.契約金額)} | ${r.解約予告 || "—"} |\n`;
    }
    md += `\n→ 残14日以内は更新交渉を完了させる。CSOへ引き継ぎ。\n\n`;
  }

  md += `## 3. インボイス対応が必要な取引先\n\n`;
  if (invoices.length === 0) {
    md += `_該当なし。_\n\n`;
  } else {
    md += `合計 ${invoices.length}件\n\n`;
    md += `| 取引先ID | 取引先名 | 理由 |\n`;
    md += `|---------|--------|------|\n`;
    for (const r of invoices) {
      md += `| ${r.取引先ID} | ${r.取引先名} | ${r.理由} |\n`;
    }
    md += `\n→ CFOで登録番号を確認・記録。未対応の場合は仕入税額控除に影響。\n\n`;
  }

  return md;
}

function buildSlackPayload(today, overdue, renewals, invoices) {
  const lines = [];
  if (overdue.length > 0) {
    const tot = overdue.reduce((s, r) => s + r.金額, 0);
    lines.push(`*入金督促*：${overdue.length}件 / ¥${tot.toLocaleString("ja-JP")}`);
    for (const r of overdue.slice(0, 5)) {
      lines.push(`  • ${r.経過日数}日経過 ${r.クライアント} ¥${r.金額.toLocaleString("ja-JP")}`);
    }
  } else {
    lines.push(`*入金督促*：該当なし`);
  }
  if (renewals.length > 0) {
    lines.push(`*契約更新*：${renewals.length}件（45日以内）`);
    for (const r of renewals.slice(0, 5)) {
      lines.push(`  • 残${r.残日数}日 ${r.取引先名}`);
    }
  } else {
    lines.push(`*契約更新*：該当なし`);
  }
  if (invoices.length > 0) {
    lines.push(`*インボイス対応*：${invoices.length}件`);
  }
  return {
    text: `アラート ${today}`,
    blocks: [
      { type: "header", text: { type: "plain_text", text: `アラート ${today}` } },
      { type: "section", text: { type: "mrkdwn", text: lines.join("\n") } },
      { type: "context", elements: [{ type: "mrkdwn", text: `生成: CDO/outputs/scripts/payment_alerts.mjs` }] }
    ]
  };
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
        if (res.statusCode >= 200 && res.statusCode < 300) resolve();
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
  if (!/^\d{4}-\d{2}-\d{2}$/.test(args.today)) {
    console.error("--today は YYYY-MM-DD 形式で指定してください");
    process.exit(1);
  }
  const order = readCSVSafe(args.orderCsv || "projects/2026-04-08_月30万自動化/A_ライティング/order_tracker_template.csv");
  const client = readCSVSafe(args.clientCsv || "CFO/templates/2026-05-19_取引先マスター_テンプレ.csv");

  const overdue = findOverduePayments(order, args.today);
  const renewals = findUpcomingRenewals(client, args.today);
  const invoices = findInvoiceIssues(client);

  const md = buildMarkdown(args.today, overdue, renewals, invoices);

  if (!args.quiet) process.stdout.write(md);

  if (args.slack) {
    const webhook = process.env.SLACK_WEBHOOK_URL;
    if (!webhook) {
      console.error("SLACK_WEBHOOK_URL が未設定です。");
      process.exit(2);
    }
    try {
      await postSlack(webhook, buildSlackPayload(args.today, overdue, renewals, invoices));
      if (!args.quiet) console.log("slack: posted");
    } catch (e) {
      console.error(`slack: ${e.message}`);
      process.exit(3);
    }
  }

  // 終了コード：要対応件数が0なら0、それ以外は10（cronで条件判定可能）
  const hasIssue = overdue.length > 0 || invoices.length > 0;
  process.exit(hasIssue ? 10 : 0);
}

main();
