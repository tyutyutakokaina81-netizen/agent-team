#!/usr/bin/env node
// 契約書自動生成スクリプト
// 依存ゼロ（Node 標準モジュールのみ）
//
// 入力:
//   - 取引先マスターCSV（CFO/templates/2026-05-19_取引先マスター_テンプレ.csv）
//   - 契約書テンプレ（テンプレ_YYYY-MM-DD_業務委託契約書ひな形.md）
//
// 出力:
//   - クライアント別の Markdown 契約書（プレースホルダ置換済）
//   - 同じ内容の HTML 版（ブラウザ「印刷→PDF」で日本語フォント維持のままPDF化可能）
//
// 使い方:
//   node CDO/outputs/scripts/contract_generator.mjs <取引先ID>
//   例: node CDO/outputs/scripts/contract_generator.mjs CL-001
//
//   node CDO/outputs/scripts/contract_generator.mjs CL-001 \
//     --template=CFO/templates/2026-05-19_業務委託契約書ひな形.md \
//     --client-csv=CFO/outputs/2026-05-19_取引先マスター.csv \
//     --outdir=CFO/outputs/clients
//
//   node CDO/outputs/scripts/contract_generator.mjs --all
//   （アクティブな全取引先について再生成）

import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "../../..");

function parseArgs(argv) {
  const args = { id: null, all: false, template: null, clientCsv: null, outdir: null };
  for (const a of argv.slice(2)) {
    if (a === "--all") args.all = true;
    else if (a.startsWith("--template=")) args.template = a.slice(11);
    else if (a.startsWith("--client-csv=")) args.clientCsv = a.slice(13);
    else if (a.startsWith("--outdir=")) args.outdir = a.slice(9);
    else if (!a.startsWith("--") && !args.id) args.id = a;
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

function readFileSafe(rel) {
  const p = path.isAbsolute(rel) ? rel : path.join(ROOT, rel);
  if (!fs.existsSync(p)) return null;
  return fs.readFileSync(p, "utf8");
}

function sanitizeFolderName(s) {
  return String(s || "")
    .replace(/[\\/:*?"<>|]/g, "_")
    .replace(/\s+/g, "_")
    .slice(0, 64);
}

function formatJapaneseDate(ymd) {
  if (!ymd || !/^\d{4}-\d{2}-\d{2}/.test(ymd)) return ymd || "";
  const [y, m, d] = ymd.slice(0, 10).split("-");
  return `${y}年${Number(m)}月${Number(d)}日`;
}

function yen(n) {
  const x = Number(String(n || "").replace(/[,¥\s]/g, ""));
  if (Number.isNaN(x)) return "0";
  return x.toLocaleString("ja-JP");
}

// テンプレ中の以下プレースホルダを置換する
//   [甲：クライアント名] → 取引先名
//   [乙：受託者名]      → 環境変数 OUR_NAME か空文字
//   月額¥XX,XXX        → 取引先マスターの契約金額（税込）
//   YYYY年MM月DD日     → 取引期間から算出
//   [Instagram / X / Facebook] → 環境変数 MEDIA か空のまま
function buildContract(template, client, opts = {}) {
  const ourName = opts.ourName || process.env.OUR_NAME || "[乙：受託者名]";
  const ourAddress = opts.ourAddress || process.env.OUR_ADDRESS || "[乙の住所]";
  const media = opts.media || process.env.MEDIA || "[Instagram / X / Facebook]";

  const period = String(client["契約期間"] || "");
  let startYmd = "", endYmd = "";
  const m = period.match(/^(\d{4}-\d{2}-\d{2})[〜~](\d{4}-\d{2}-\d{2})$/);
  if (m) { startYmd = m[1]; endYmd = m[2]; }

  const monthlyTax = yen(client["契約金額（税込）"]);
  const monthlyNoTax = yen(client["契約金額（税抜）"]);
  const trial = opts.trial || "";

  let body = template;

  // 甲・乙の差し替え
  body = body.replace(/\[甲：クライアント名\]/g, client["取引先名"] || "");
  body = body.replace(/\[乙：受託者名\]/g, ourName);

  // 金額
  body = body.replace(/月額¥XX,XXX（税込）/g, `月額¥${monthlyTax}（税込／税抜¥${monthlyNoTax}）`);
  body = body.replace(/¥XX,XXX（税込）/g, `¥${monthlyTax}（税込）`);

  // 期間
  if (startYmd) body = body.replace(/業務開始日：YYYY年MM月DD日/g, `業務開始日：${formatJapaneseDate(startYmd)}`);
  if (startYmd && endYmd) {
    body = body.replace(
      /本契約の有効期間はYYYY年MM月DD日からYYYY年MM月DD日までの\[X\]ヶ月間とする。/g,
      `本契約の有効期間は${formatJapaneseDate(startYmd)}から${formatJapaneseDate(endYmd)}までとする。`
    );
  }

  // 媒体
  body = body.replace(/\[Instagram \/ X \/ Facebook\]/g, media);

  // 投稿数（テンプレに月XX本とあるなら、--posts オプションがない場合は据え置き）
  if (opts.posts) {
    body = body.replace(/SNS投稿文（月XX本）の作成/g, `SNS投稿文（月${opts.posts}本）の作成`);
  }

  // フッタ
  const today = new Date().toISOString().slice(0, 10);
  body = body.replace(/YYYY年MM月DD日$/m, formatJapaneseDate(today));

  // 住所
  body = body.replace(/^　　住所：$/m, `　　住所：${client["住所"] || ""}`);
  body = body.replace(/^　　住所：\n　　代表者/m, `　　住所：${client["住所"] || ""}\n　　代表者`);

  // 乙の住所
  body = body.replace(/^乙：\[受託者名\]\n　　住所：$/m, `乙：${ourName}\n　　住所：${ourAddress}`);

  // 注釈（自動生成由来）を末尾に
  body += `\n\n---\n\n_この契約書は contract_generator.mjs で自動生成されました（${today}）。最終確認の上、署名・押印してください。_\n`;

  return body;
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function markdownToHtml(md) {
  // 最小限の md → html。見出し・段落・改行のみ対応（依存ゼロ）。
  const lines = md.split("\n");
  let html = "";
  let inPre = false;
  for (const line of lines) {
    if (/^```/.test(line)) {
      if (!inPre) { html += "<pre>"; inPre = true; }
      else { html += "</pre>\n"; inPre = false; }
      continue;
    }
    if (inPre) { html += escapeHtml(line) + "\n"; continue; }
    const trimmed = line.trim();
    if (trimmed === "") { html += "<br>\n"; continue; }
    if (/^# /.test(trimmed)) { html += `<h1>${escapeHtml(trimmed.slice(2))}</h1>\n`; continue; }
    if (/^## /.test(trimmed)) { html += `<h2>${escapeHtml(trimmed.slice(3))}</h2>\n`; continue; }
    if (/^### /.test(trimmed)) { html += `<h3>${escapeHtml(trimmed.slice(4))}</h3>\n`; continue; }
    if (/^---$/.test(trimmed)) { html += "<hr>\n"; continue; }
    html += `<p>${escapeHtml(line).replace(/  +/g, "&nbsp;&nbsp;")}</p>\n`;
  }
  return html;
}

function wrapHtml(title, bodyHtml) {
  return `<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>${escapeHtml(title)}</title>
<style>
  body { font-family: "Hiragino Mincho ProN", "Yu Mincho", "MS Mincho", serif; max-width: 720px; margin: 40px auto; padding: 0 20px; line-height: 1.8; color: #222; }
  h1 { font-size: 22px; text-align: center; margin: 30px 0; border-bottom: 2px solid #333; padding-bottom: 10px; }
  h2 { font-size: 16px; margin-top: 28px; border-left: 4px solid #333; padding-left: 8px; }
  h3 { font-size: 14px; margin-top: 20px; }
  p { margin: 6px 0; }
  pre { background: #f5f5f5; padding: 10px; white-space: pre-wrap; word-break: break-word; }
  hr { border: none; border-top: 1px solid #ccc; margin: 24px 0; }
  @media print {
    body { margin: 0; max-width: none; }
    h1 { page-break-after: avoid; }
  }
</style>
</head>
<body>
${bodyHtml}
<p style="margin-top:30px;font-size:11px;color:#888;">ブラウザの「印刷 → PDFとして保存」でPDF化できます。日本語フォントはOS標準のものを使用します。</p>
</body>
</html>`;
}

function generateOne(template, client, outdir) {
  const id = client["取引先ID"] || "UNKNOWN";
  const name = sanitizeFolderName(client["取引先名"] || "unknown");
  const folder = path.join(outdir, `${id}_${name}`);
  fs.mkdirSync(folder, { recursive: true });

  const body = buildContract(template, client);
  const today = new Date().toISOString().slice(0, 10);
  const mdPath = path.join(folder, `${today}_契約書_${name}.md`);
  const htmlPath = path.join(folder, `${today}_契約書_${name}.html`);

  fs.writeFileSync(mdPath, body, "utf8");
  fs.writeFileSync(htmlPath, wrapHtml(`契約書_${name}`, markdownToHtml(body)), "utf8");

  return { id, mdPath, htmlPath };
}

function main() {
  const args = parseArgs(process.argv);
  if (!args.id && !args.all) {
    console.error("使い方: node contract_generator.mjs <取引先ID> | --all");
    process.exit(1);
  }
  const templatePath = args.template || "CFO/templates/2026-05-19_業務委託契約書ひな形.md";
  const clientCsvPath = args.clientCsv || "CFO/templates/2026-05-19_取引先マスター_テンプレ.csv";
  const outdir = args.outdir || "CFO/outputs/clients";

  const template = readFileSafe(templatePath);
  if (!template) {
    console.error(`テンプレが見つかりません: ${templatePath}`);
    process.exit(2);
  }
  const csvText = readFileSafe(clientCsvPath);
  if (!csvText) {
    console.error(`取引先CSVが見つかりません: ${clientCsvPath}`);
    process.exit(3);
  }
  const csv = parseCSV(csvText);

  const targets = args.all
    ? csv.rows.filter(r => r["取引ステータス"] === "アクティブ" || r["取引ステータス"] === "")
    : csv.rows.filter(r => r["取引先ID"] === args.id);

  if (targets.length === 0) {
    console.error(args.all ? "対象クライアントなし。" : `取引先ID "${args.id}" が見つかりません。`);
    process.exit(4);
  }

  const outdirAbs = path.isAbsolute(outdir) ? outdir : path.join(ROOT, outdir);
  for (const client of targets) {
    const result = generateOne(template, client, outdirAbs);
    console.log(`生成: ${result.id}`);
    console.log(`  md:   ${result.mdPath}`);
    console.log(`  html: ${result.htmlPath}`);
  }
  console.log(`\n合計 ${targets.length} 件の契約書を生成しました。`);
  console.log(`PDF化：HTMLをブラウザで開き「印刷 → PDFとして保存」してください。`);
}

main();
