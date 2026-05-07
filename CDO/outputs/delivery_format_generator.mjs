#!/usr/bin/env node
/**
 * delivery_format_generator.mjs — 納品形式の自動変換
 *
 * 用途：Markdown 形式の記事を、クライアントが希望する各種形式に変換する。
 *      納品時の手作業を削減し、ヒューマンエラーを防ぐ。
 *
 * 費用ゼロ：Node 標準モジュールのみ
 *
 * 使い方:
 *   node CDO/outputs/delivery_format_generator.mjs <article.md>
 *   node CDO/outputs/delivery_format_generator.mjs <article.md> --format plain
 *   node CDO/outputs/delivery_format_generator.mjs <article.md> --format html
 *   node CDO/outputs/delivery_format_generator.mjs <article.md> --all
 *
 * 出力（--all）:
 *   <article>_plain.txt    プレーンテキスト
 *   <article>_html.html    HTML（WordPress 等の CMS 貼り付け用）
 *   <article>_docs.md      Google Docs 貼り付け用（記号最小化）
 */

import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { resolve, basename, dirname, join, extname } from 'node:path';

function parseArgs(argv) {
  const args = { file: null, format: null, all: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--format') args.format = argv[++i];
    else if (a === '--all') args.all = true;
    else if (a === '--help' || a === '-h') args.help = true;
    else if (!a.startsWith('--') && !args.file) args.file = a;
  }
  return args;
}

function showHelp() {
  console.log(`delivery_format_generator.mjs

USAGE:
  node CDO/outputs/delivery_format_generator.mjs <article.md> [OPTIONS]

OPTIONS:
  --format plain    プレーンテキスト出力
  --format html     HTML 出力
  --format docs     Google Docs 貼り付け用 Markdown 出力
  --all             3形式すべて出力（デフォルト）

費用ゼロ：Node 標準モジュールのみ。
`);
}

// ─────────────────────────────────────────────
// プレーンテキスト変換
// ─────────────────────────────────────────────
function toPlainText(md) {
  return md
    .replace(/^#{1,6}\s+/gm, '')                              // 見出し記号削除
    .replace(/\*\*([^*]+)\*\*/g, '$1')                        // 太字
    .replace(/\*([^*]+)\*/g, '$1')                            // イタリック
    .replace(/~~([^~]+)~~/g, '$1')                            // 取り消し
    .replace(/`([^`]+)`/g, '$1')                              // インラインコード
    .replace(/```[a-z]*\n([\s\S]*?)\n```/g, '$1')             // コードブロック
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, '[画像: $1]')         // 画像
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '$1（$2）')          // リンク
    .replace(/^>\s+/gm, '> ')                                 // 引用は維持
    .replace(/^[\s]*[-*+]\s/gm, '・')                         // 箇条書き
    .replace(/^[\s]*(\d+)\.\s/gm, '$1. ')                     // 番号リスト
    .replace(/\n{3,}/g, '\n\n');                              // 連続改行整理
}

// ─────────────────────────────────────────────
// HTML 変換（WordPress / 一般 CMS 用）
// ─────────────────────────────────────────────
function toHtml(md) {
  let html = md;

  // コードブロック（先に処理して中身を保護）
  const codeBlocks = [];
  html = html.replace(/```([a-z]*)\n([\s\S]*?)\n```/g, (_, lang, code) => {
    codeBlocks.push({ lang, code });
    return `\x00CODEBLOCK${codeBlocks.length - 1}\x00`;
  });

  // インラインコード
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // 見出し
  html = html.replace(/^###### (.+)$/gm, '<h6>$1</h6>');
  html = html.replace(/^##### (.+)$/gm, '<h5>$1</h5>');
  html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

  // 強調
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  html = html.replace(/~~([^~]+)~~/g, '<del>$1</del>');

  // 画像・リンク
  html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1">');
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');

  // 表（| ... | 形式）
  html = html.replace(/((?:^\|.+\|\n?)+)/gm, (table) => {
    const rows = table.trim().split('\n').filter(Boolean);
    if (rows.length < 2) return table;
    const isAligns = (r) => /^\|[\s|:-]+\|$/.test(r);
    const headRow = rows[0];
    const alignRow = rows[1];
    const bodyRows = isAligns(alignRow) ? rows.slice(2) : rows.slice(1);
    const parseRow = (r) => r.replace(/^\||\|$/g, '').split('|').map(c => c.trim());
    const head = `<thead><tr>${parseRow(headRow).map(c => `<th>${c}</th>`).join('')}</tr></thead>`;
    const body = `<tbody>${bodyRows.map(r => `<tr>${parseRow(r).map(c => `<td>${c}</td>`).join('')}</tr>`).join('')}</tbody>`;
    return `<table>${head}${body}</table>\n`;
  });

  // 箇条書き
  html = html.replace(/((?:^[\s]*[-*+]\s+.+\n?)+)/gm, (list) => {
    const items = list.trim().split('\n').map(l => l.replace(/^[\s]*[-*+]\s+/, '')).filter(Boolean);
    return `<ul>${items.map(i => `<li>${i}</li>`).join('')}</ul>\n`;
  });

  // 番号リスト
  html = html.replace(/((?:^[\s]*\d+\.\s+.+\n?)+)/gm, (list) => {
    const items = list.trim().split('\n').map(l => l.replace(/^[\s]*\d+\.\s+/, '')).filter(Boolean);
    return `<ol>${items.map(i => `<li>${i}</li>`).join('')}</ol>\n`;
  });

  // 引用
  html = html.replace(/^>\s+(.+)$/gm, '<blockquote>$1</blockquote>');

  // 段落（連続する非タグ行を <p> でくくる）
  html = html.split(/\n{2,}/).map(block => {
    block = block.trim();
    if (!block) return '';
    if (/^<(h[1-6]|ul|ol|table|blockquote|pre|img|hr)/i.test(block)) return block;
    return `<p>${block.replace(/\n/g, '<br>')}</p>`;
  }).join('\n\n');

  // コードブロック復元
  html = html.replace(/\x00CODEBLOCK(\d+)\x00/g, (_, idx) => {
    const { lang, code } = codeBlocks[parseInt(idx)];
    const escaped = code
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
    return `<pre><code${lang ? ` class="language-${lang}"` : ''}>${escaped}</code></pre>`;
  });

  return html;
}

// ─────────────────────────────────────────────
// Google Docs 貼り付け用 Markdown
// （Google Docs は基本的な Markdown を解釈するが、装飾を最小化した方が崩れにくい）
// ─────────────────────────────────────────────
function toGoogleDocsMd(md) {
  return md
    .replace(/```[a-z]*\n([\s\S]*?)\n```/g, '\n[コード]\n$1\n[/コード]\n')  // コードブロックをラベル化
    .replace(/`([^`]+)`/g, '$1')                                            // インラインコードを地の文に
    .replace(/~~([^~]+)~~/g, '$1')                                          // 取り消し線（Google Docs 解釈なし）
    .replace(/\n{3,}/g, '\n\n');
}

// ─────────────────────────────────────────────
// メイン
// ─────────────────────────────────────────────
function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) { showHelp(); return; }
  if (!args.file) {
    console.error('使い方: node delivery_format_generator.mjs <article.md>');
    process.exit(1);
  }

  const filePath = resolve(args.file);
  if (!existsSync(filePath)) {
    console.error(`ファイルが見つかりません: ${filePath}`);
    process.exit(1);
  }

  const md = readFileSync(filePath, 'utf-8');
  const ext = extname(filePath);
  const base = basename(filePath, ext);
  const dir = dirname(filePath);

  const formats = args.all || !args.format
    ? ['plain', 'html', 'docs']
    : [args.format];

  console.log('━━━━━━━━━━━━━━━━━━━━━━━');
  console.log(`📦 納品形式変換：${base}${ext}`);
  console.log('━━━━━━━━━━━━━━━━━━━━━━━');

  for (const fmt of formats) {
    let outContent;
    let outName;
    if (fmt === 'plain') {
      outContent = toPlainText(md);
      outName = `${base}_plain.txt`;
    } else if (fmt === 'html') {
      outContent = toHtml(md);
      outName = `${base}_html.html`;
    } else if (fmt === 'docs') {
      outContent = toGoogleDocsMd(md);
      outName = `${base}_docs.md`;
    } else {
      console.error(`未知の形式: ${fmt}`);
      continue;
    }
    const outPath = join(dir, outName);
    writeFileSync(outPath, outContent, 'utf-8');
    const sizeKB = (Buffer.byteLength(outContent) / 1024).toFixed(1);
    console.log(`✅ ${fmt.padEnd(5)}: ${outName}  (${sizeKB} KB)`);
  }

  console.log('');
  console.log('次の手順：');
  console.log('  1. クライアント希望形式のファイルを開く');
  console.log('  2. 内容を確認（Markdown 装飾が崩れていないか）');
  console.log('  3. クライアントへ送付');
}

main();
