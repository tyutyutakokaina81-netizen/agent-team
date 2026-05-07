#!/usr/bin/env node
/**
 * quick_publish_kit_generator.mjs — 30秒公開キット生成
 *
 * 目的：CMO/outputs/ の note 集客記事を「コピペ即公開」できる
 *       スタンドアロン .txt に変換し、CMO/outputs/_publish_ready/ に配置する。
 *
 *       オーナーは：
 *         1. .txt を開く
 *         2. 全選択コピー
 *         3. note 編集画面に貼り付け
 *         4. 公開ボタン
 *       で完了。コードブロック・メタ情報・チェックリストは除外して、
 *       純粋な「note 本文だけ」を抽出する。
 *
 * 費用ゼロ：Node 標準モジュールのみ
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync, readdirSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dir = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dir, '../..');
const OUTPUTS_DIR = join(REPO_ROOT, 'CMO', 'outputs');
const PUBLISH_DIR = join(OUTPUTS_DIR, '_publish_ready');

function safe(fn, fb) { try { return fn(); } catch { return fb; } }

// 集客記事ファイルから「本文（コードブロック内）」を抽出
function extractBody(content) {
  // ## 本文（note にそのまま貼る）の直後のコードブロックを取得
  const match = content.match(/##\s*本文（note にそのまま貼る）\s*\n+```\s*\n([\s\S]*?)\n```/);
  if (match) return match[1].trim();
  // フォールバック：最初の長いコードブロック
  const fallback = content.match(/```\s*\n([\s\S]{500,}?)\n```/);
  return fallback ? fallback[1].trim() : null;
}

// タイトルの抽出
function extractTitle(content) {
  const match = content.match(/##\s*タイトル（コピペ用）\s*\n+```\s*\n(.+?)\n```/);
  if (match) return match[1].trim();
  const h1 = content.match(/^#\s+(.+)/m);
  return h1 ? h1[1].trim() : '（タイトル不明）';
}

// ハッシュタグの抽出
function extractTags(content) {
  const match = content.match(/##\s*ハッシュタグ.*?\n+```\s*\n([\s\S]*?)\n```/);
  return match ? match[1].trim() : '';
}

function buildKit({ title, body, tags, sourceFile }) {
  return `${title}

${body}

${tags ? '\n' + tags : ''}

---
出典：${sourceFile}
※この .txt を開いて全選択 → コピー → note 編集画面に貼り付け → 公開
※[LINK_PLACEHOLDER] や [Vol.X 販売ページのリンクを貼る] は実 URL に置換してください
`;
}

function processFile(filePath) {
  const fileName = filePath.split('/').pop();
  if (!fileName.includes('集客記事')) return null;

  const content = readFileSync(filePath, 'utf-8');
  const title = extractTitle(content);
  const body = extractBody(content);
  const tags = extractTags(content);

  if (!body) return null;

  const slug = fileName.replace(/^\d{4}-\d{2}-\d{2}_note集客記事_/, '').replace(/\.md$/, '');
  const outFile = `${slug}_publish.txt`;
  const kitContent = buildKit({
    title,
    body,
    tags,
    sourceFile: `CMO/outputs/${fileName}`,
  });

  return { outFile, kitContent, title };
}

function main() {
  if (!existsSync(OUTPUTS_DIR)) {
    console.error(`CMO/outputs/ が見つかりません`);
    process.exit(1);
  }

  if (!existsSync(PUBLISH_DIR)) mkdirSync(PUBLISH_DIR, { recursive: true });

  const files = readdirSync(OUTPUTS_DIR)
    .filter(f => f.includes('集客記事') && f.endsWith('.md'))
    .map(f => join(OUTPUTS_DIR, f));

  console.log('━━━━━━━━━━━━━━━━━━━━━━━');
  console.log(`📦 30秒公開キット生成`);
  console.log('━━━━━━━━━━━━━━━━━━━━━━━');
  console.log(`対象記事：${files.length}本`);
  console.log('');

  let success = 0;
  for (const f of files) {
    const result = processFile(f);
    if (!result) {
      console.log(`⚠️ スキップ：${f.split('/').pop()}（本文抽出失敗）`);
      continue;
    }
    const outPath = join(PUBLISH_DIR, result.outFile);
    writeFileSync(outPath, result.kitContent, 'utf-8');
    console.log(`✅ ${result.outFile}`);
    console.log(`   タイトル：${result.title.slice(0, 40)}...`);
    success++;
  }

  // README を生成
  const readme = `# 30秒公開キット

このフォルダの .txt ファイルは **note 編集画面に直接貼り付け可能** な形式です。

## 使い方（30秒）

1. .txt ファイルを開く
2. 全選択（Cmd+A / Ctrl+A）
3. コピー（Cmd+C / Ctrl+C）
4. [note.com](https://note.com) で「記事を書く」
5. タイトル欄に最初の行を貼り付け
6. 本文欄に残りを貼り付け
7. \`[LINK_PLACEHOLDER]\` を Vol.X 販売ページの実 URL に置換
8. アイキャッチを Canva で作成・添付（任意）
9. 公開ボタンを押す

## 含まれるキット（${success}本）

${files.map(f => {
  const r = processFile(f);
  return r ? `- \`${r.outFile}\`` : null;
}).filter(Boolean).join('\n')}

## 自動再生成

このフォルダは \`CDO/outputs/quick_publish_kit_generator.mjs\` で再生成可能：

\`\`\`bash
node CDO/outputs/quick_publish_kit_generator.mjs
\`\`\`

## 費用

¥0（既存ツール内で完結）
`;

  writeFileSync(join(PUBLISH_DIR, 'README.md'), readme, 'utf-8');

  console.log('');
  console.log(`✅ ${success}本の公開キット生成完了`);
  console.log(`   出力先：${PUBLISH_DIR.replace(REPO_ROOT + '/', '')}`);
  console.log('');
  console.log('次の手順：');
  console.log(`  1. CMO/outputs/_publish_ready/ を開く`);
  console.log(`  2. .txt を開いて全選択コピー`);
  console.log(`  3. note 編集画面に貼り付け`);
  console.log(`  4. 公開ボタン`);
}

main();
