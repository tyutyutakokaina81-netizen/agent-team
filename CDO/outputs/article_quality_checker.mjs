#!/usr/bin/env node
/**
 * article_quality_checker.mjs — 納品前 SEO 記事の品質自動チェック
 *
 * 用途：受注した SEO 記事を納品する前に、機械的にチェックすべき項目を検証。
 * 文字数・見出し構造・メタ情報・NG表現の検出を行う。
 *
 * 費用ゼロ：Node 標準モジュールのみ
 *
 * 使い方:
 *   node CDO/outputs/article_quality_checker.mjs path/to/article.md
 *   node CDO/outputs/article_quality_checker.mjs path/to/article.md --target-words 4000
 *   node CDO/outputs/article_quality_checker.mjs path/to/article.md --keyword "確定申告"
 */

import { readFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';

function parseArgs(argv) {
  const args = { file: null, targetWords: null, keyword: null, verbose: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--target-words') args.targetWords = parseInt(argv[++i]);
    else if (a === '--keyword') args.keyword = argv[++i];
    else if (a === '--verbose') args.verbose = true;
    else if (a === '--help' || a === '-h') args.help = true;
    else if (!a.startsWith('--') && !args.file) args.file = a;
  }
  return args;
}

function showHelp() {
  console.log(`article_quality_checker.mjs — 納品前 SEO 記事の品質チェック

USAGE:
  node CDO/outputs/article_quality_checker.mjs <article.md> [OPTIONS]

OPTIONS:
  --target-words <n>    目標文字数（指定すると ±5%以内に収まっているかチェック）
  --keyword <word>      メインキーワード（含有率をチェック）
  --verbose             詳細出力

費用ゼロ：Node 標準モジュールのみ。
`);
}

const NG_PHRASES = [
  // AI 特有の決まり文句
  'いかがでしたでしょうか',
  'いかがだったでしょうか',
  'お役に立てば幸いです',
  '私が解説します',
  // 煽り表現
  '絶対に',
  '必ず儲かる',
  '誰でも簡単',
  '今すぐ',
  // 弱い表現
  'と思います',
  'たぶん',
  'おそらく',
  'かもしれません',
];

const RESULTS = { pass: [], warn: [], fail: [] };

function check(label, ok, detail) {
  if (ok === true) RESULTS.pass.push({ label, detail });
  else if (ok === 'warn') RESULTS.warn.push({ label, detail });
  else RESULTS.fail.push({ label, detail });
}

function countCharacters(content) {
  // Markdown 装飾・コードブロック・リンクURL を除外して本文のみカウント
  const cleaned = content
    .replace(/```[\s\S]*?```/g, '')                      // コードブロック
    .replace(/`[^`]+`/g, '')                              // インラインコード
    .replace(/!\[[^\]]*\]\([^)]+\)/g, '')                 // 画像
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')              // リンク（テキスト部分は残す）
    .replace(/^#{1,6}\s+/gm, '')                          // 見出し記号
    .replace(/[*_~]/g, '')                                // 強調記号
    .replace(/\s+/g, '');                                 // 空白
  return cleaned.length;
}

function analyzeStructure(content) {
  const h1 = (content.match(/^# [^\n]+/gm) || []).length;
  const h2 = (content.match(/^## [^\n]+/gm) || []).length;
  const h3 = (content.match(/^### [^\n]+/gm) || []).length;
  const lists = (content.match(/^[\s]*[-*+]\s/gm) || []).length;
  const tables = (content.match(/^\|.+\|/gm) || []).length;
  return { h1, h2, h3, lists, tables };
}

function checkMetaDescription(content) {
  const m = content.match(/(メタディスクリプション|meta description)[：:][\s]*\n+([\s\S]*?)(?=\n\n|\n##|$)/i);
  if (!m) return null;
  const text = m[2].replace(/```/g, '').trim();
  return { text, length: text.length };
}

function findNgPhrases(content) {
  const found = [];
  for (const phrase of NG_PHRASES) {
    const matches = content.match(new RegExp(phrase, 'g'));
    if (matches) found.push({ phrase, count: matches.length });
  }
  return found;
}

function keywordDensity(content, keyword) {
  if (!keyword) return null;
  const matches = content.match(new RegExp(keyword, 'g'));
  const count = matches ? matches.length : 0;
  const totalChars = countCharacters(content);
  const density = totalChars > 0 ? (count * keyword.length) / totalChars : 0;
  return { count, density };
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) { showHelp(); return; }
  if (!args.file) {
    console.error('使い方: node article_quality_checker.mjs <article.md>');
    process.exit(1);
  }

  const filePath = resolve(args.file);
  if (!existsSync(filePath)) {
    console.error(`ファイルが見つかりません: ${filePath}`);
    process.exit(1);
  }

  const content = readFileSync(filePath, 'utf-8');

  console.log('━━━━━━━━━━━━━━━━━━━━━━━');
  console.log(`📄 品質チェック：${filePath.split('/').pop()}`);
  console.log('━━━━━━━━━━━━━━━━━━━━━━━');

  // 1. 文字数チェック
  const wordCount = countCharacters(content);
  console.log(`\n[文字数] ${wordCount}字`);
  if (args.targetWords) {
    const lower = args.targetWords * 0.95;
    const upper = args.targetWords * 1.05;
    if (wordCount < lower) {
      check('文字数', false, `${wordCount}字（目標 ${args.targetWords}字 -5%下限 ${lower}字）`);
    } else if (wordCount > upper) {
      check('文字数', 'warn', `${wordCount}字（目標 ${args.targetWords}字 +5%上限 ${upper}字）`);
    } else {
      check('文字数', true, `${wordCount}字（目標 ${args.targetWords}字 ±5%以内）`);
    }
  }

  // 2. 構造チェック
  const struct = analyzeStructure(content);
  console.log(`[構造] H1=${struct.h1} H2=${struct.h2} H3=${struct.h3} 箇条書き=${struct.lists} 表=${struct.tables}`);
  check('H1 タイトル', struct.h1 === 1, struct.h1 === 1 ? '1個' : `${struct.h1}個（1個必須）`);
  check('H2 見出し', struct.h2 >= 3 ? true : 'warn', `${struct.h2}個（推奨 3個以上）`);
  check('箇条書き or 表', struct.lists + struct.tables >= 1 ? true : 'warn',
    `箇条書き${struct.lists}＋表${struct.tables}（推奨 計1個以上）`);

  // 3. メタディスクリプション
  const meta = checkMetaDescription(content);
  if (meta) {
    console.log(`[メタディスクリプション] ${meta.length}字`);
    if (meta.length < 80) check('メタ長さ', 'warn', `${meta.length}字（推奨 120〜160字）`);
    else if (meta.length > 200) check('メタ長さ', 'warn', `${meta.length}字（長すぎ）`);
    else check('メタ長さ', true, `${meta.length}字`);
  } else {
    check('メタディスクリプション', 'warn', '未検出（記事末尾に追加推奨）');
  }

  // 4. NG表現
  const ng = findNgPhrases(content);
  if (ng.length === 0) {
    check('NG表現', true, 'なし');
  } else {
    check('NG表現', 'warn', ng.map(n => `「${n.phrase}」×${n.count}`).join(' / '));
  }

  // 5. キーワード密度
  if (args.keyword) {
    const kd = keywordDensity(content, args.keyword);
    const pct = (kd.density * 100).toFixed(2);
    console.log(`[キーワード] 「${args.keyword}」 ${kd.count}回 / 密度 ${pct}%`);
    if (kd.density < 0.005) check('キーワード密度', 'warn', `${pct}%（推奨 1〜3%）`);
    else if (kd.density > 0.05) check('キーワード密度', 'warn', `${pct}%（高すぎ・スパム判定リスク）`);
    else check('キーワード密度', true, `${pct}%`);
  }

  // 結果サマリ
  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━');
  console.log(`PASS: ${RESULTS.pass.length} / WARN: ${RESULTS.warn.length} / FAIL: ${RESULTS.fail.length}`);
  console.log('━━━━━━━━━━━━━━━━━━━━━━━');

  if (RESULTS.fail.length > 0) {
    console.log('\n🔴 FAIL（納品前に必ず修正）:');
    RESULTS.fail.forEach(r => console.log(`  - ${r.label}: ${r.detail}`));
  }
  if (RESULTS.warn.length > 0) {
    console.log('\n🟡 WARN（納品前に確認推奨）:');
    RESULTS.warn.forEach(r => console.log(`  - ${r.label}: ${r.detail}`));
  }
  if (args.verbose && RESULTS.pass.length > 0) {
    console.log('\n🟢 PASS:');
    RESULTS.pass.forEach(r => console.log(`  - ${r.label}: ${r.detail}`));
  }

  console.log('');
  process.exit(RESULTS.fail.length > 0 ? 1 : 0);
}

main();
