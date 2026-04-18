#!/usr/bin/env node
/**
 * post_to_note.mjs — note.com 完全自動投稿スクリプト
 *
 * 実行：
 *   node post_to_note.mjs <記事ファイル.md>           # フル自動投稿（デフォルト）
 *   node post_to_note.mjs <記事ファイル.md> --review  # 公開直前で止める
 *   node post_to_note.mjs <記事ファイル.md> --dry-run # 入力のみ・公開しない
 *
 * 自動化範囲：
 *   1. 新規投稿ページを開く
 *   2. タイトル入力
 *   3. 本文入力
 *   4. ハッシュタグ追加
 *   5. 「公開設定」クリック
 *   6. 「公開」ボタン押下（--review/--dry-run 指定時はスキップ）
 *
 * 入力ファイル形式（frontmatter）：
 *   ---
 *   title: 記事タイトル
 *   tags:
 *     - Claude
 *     - AI
 *   ---
 *   本文ここから...
 *
 * ⚠ 注意：
 *   - 投稿後に typo 等あれば note 上で編集/削除可能
 *   - noteの利用規約上、自動投稿は明示禁止されていないが、過度な利用はBANリスク
 */

import { chromium } from 'playwright';
import { readFileSync, existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const AUTH_FILE = join(__dirname, 'auth-state.json');

// ─────────────────────────────────────────────
// frontmatter パーサ
// ─────────────────────────────────────────────
function parseFrontmatter(content) {
  const match = content.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/);
  if (!match) return { meta: {}, body: content.trim() };

  const meta = {};
  const lines = match[1].split(/\r?\n/);
  let currentKey = null;

  for (const line of lines) {
    const kv = line.match(/^([a-zA-Z_]+):\s*(.*)$/);
    if (kv) {
      currentKey = kv[1];
      const value = kv[2].trim();
      meta[currentKey] = value === '' ? [] : value.replace(/^["']|["']$/g, '');
    } else if (currentKey && Array.isArray(meta[currentKey])) {
      const item = line.match(/^\s*-\s+(.+)$/);
      if (item) meta[currentKey].push(item[1].trim().replace(/^["']|["']$/g, ''));
    }
  }
  return { meta, body: match[2].trim() };
}

// ─────────────────────────────────────────────
// 引数パース
// ─────────────────────────────────────────────
const args = process.argv.slice(2);
const flags = {
  review:  args.includes('--review'),
  dryRun:  args.includes('--dry-run'),
};
const filePath = args.find((a) => !a.startsWith('--'));

if (!filePath) {
  console.error('使い方: node post_to_note.mjs <記事ファイル.md> [--review | --dry-run]');
  process.exit(1);
}

if (!existsSync(AUTH_FILE)) {
  console.error('❌ auth-state.json が見つかりません。');
  console.error('   先に: npm run login を実行してください。');
  process.exit(1);
}

const absPath = resolve(filePath);
if (!existsSync(absPath)) {
  console.error(`❌ ファイルが見つかりません: ${absPath}`);
  process.exit(1);
}

const content = readFileSync(absPath, 'utf-8');
const { meta, body } = parseFrontmatter(content);

if (!meta.title) {
  console.error('❌ frontmatter に title: が必要です');
  process.exit(1);
}

const tags = Array.isArray(meta.tags) ? meta.tags : [];
const mode = flags.dryRun ? 'DRY-RUN（入力のみ・公開しない）'
           : flags.review ? 'REVIEW（公開直前で停止）'
           : '⚠ FULL-AUTO（公開ボタンまで自動押下）';

console.log('');
console.log('📝 投稿準備');
console.log('================================');
console.log(`タイトル: ${meta.title}`);
console.log(`タグ:     ${tags.join(', ') || '（なし）'}`);
console.log(`本文長:   ${body.length} 文字`);
console.log(`モード:   ${mode}`);
console.log('');

// ─────────────────────────────────────────────
// ヘルパー
// ─────────────────────────────────────────────
async function waitForFirst(page, selectors, timeoutPerSelector = 5000) {
  for (const sel of selectors) {
    try {
      const el = await page.waitForSelector(sel, {
        state: 'visible',
        timeout: timeoutPerSelector,
      });
      if (el) return { el, selector: sel };
    } catch {}
  }
  return null;
}

async function clickByText(page, texts, timeout = 10000) {
  for (const text of texts) {
    try {
      const button = page.getByRole('button', { name: text }).first();
      await button.waitFor({ state: 'visible', timeout });
      await button.click();
      return true;
    } catch {}
  }
  return false;
}

// ─────────────────────────────────────────────
// メイン処理
// ─────────────────────────────────────────────
const browser = await chromium.launch({ headless: false });
const context = await browser.newContext({ storageState: AUTH_FILE });
const page = await context.newPage();

try {
  console.log('🌐 noteの新規投稿ページを開いています...');
  await page.goto('https://note.com/notes/new', { waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});

  // goto でホーム等にリダイレクトされた場合の救済：投稿リンクをクリックして編集画面へ
  if (!page.url().includes('/notes/new') && !page.url().includes('/new')) {
    console.log(`ℹ️  URLがリダイレクトされました: ${page.url()}`);
    console.log('   「投稿」リンクを探してクリックします...');
    const newLink = await waitForFirst(page, [
      'a[href*="/notes/new"]',
      'a[href="/new"]',
      'a[href*="editor.note.com"]',
    ], 5000);
    if (newLink) {
      await newLink.el.click();
      await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    }
  }

  // ─── タイトル入力 ───
  console.log('✏️  タイトルを入力中...');
  const titleMatch = await waitForFirst(page, [
    'textarea[placeholder="記事タイトル"]',
    'textarea[placeholder*="タイトル"]',
    'textarea[aria-label*="タイトル"]',
    'input[placeholder*="タイトル"]',
    '[contenteditable="true"][aria-label*="タイトル"]',
  ], 10000);
  if (!titleMatch) {
    throw new Error(`タイトル欄が見つかりません。URL: ${page.url()}`);
  }
  console.log(`   使用セレクタ: ${titleMatch.selector}`);
  await titleMatch.el.click();
  try { await titleMatch.el.fill(meta.title); }
  catch { await page.keyboard.type(meta.title, { delay: 10 }); }

  // ─── 本文入力 ───
  console.log('✏️  本文を入力中...（やや時間がかかります）');
  const bodyMatch = await waitForFirst(page, [
    'div.ProseMirror[contenteditable="true"][role="textbox"]',
    'div[contenteditable="true"].ProseMirror',
    '.ProseMirror[contenteditable="true"]',
    'div[contenteditable="true"][aria-label*="本文"]',
    'div[contenteditable="true"][role="textbox"]:not([aria-label*="タイトル"])',
  ], 10000);
  if (!bodyMatch) {
    throw new Error(`本文欄が見つかりません。URL: ${page.url()}`);
  }
  console.log(`   使用セレクタ: ${bodyMatch.selector}`);
  await bodyMatch.el.click();

  const paragraphs = body.split(/\n\n+/);
  for (let i = 0; i < paragraphs.length; i++) {
    const p = paragraphs[i].replace(/\n/g, ' ').trim();
    if (!p) continue;
    await page.keyboard.type(p, { delay: 2 });
    if (i < paragraphs.length - 1) {
      await page.keyboard.press('Enter');
    }
  }

  await page.waitForTimeout(3000); // 自動保存待機

  if (flags.dryRun) {
    console.log('');
    console.log('✨ DRY-RUN 完了。入力までで停止します。');
    console.log('   ブラウザは開いたままです。Ctrl+C で終了。');
    await new Promise(() => {});
  }

  // ─── 公開設定ページへ進む ───
  console.log('📤 「公開設定」へ進みます...');
  const movedToPublish = await clickByText(page, ['公開設定', '公開に進む']);
  if (!movedToPublish) throw new Error('「公開設定」ボタンが見つかりません');
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(2000);

  // ─── ハッシュタグ追加 ───
  if (tags.length) {
    console.log(`🏷  ハッシュタグを追加中: ${tags.join(', ')}`);
    const tagInput = await page.$('input[placeholder*="ハッシュタグ"]')
                  || await page.$('input[placeholder*="タグ"]')
                  || await page.$('input[type="text"][aria-label*="タグ"]');
    if (tagInput) {
      for (const tag of tags) {
        await tagInput.click();
        await page.keyboard.type(tag, { delay: 20 });
        await page.keyboard.press('Enter');
        await page.waitForTimeout(500);
      }
    } else {
      console.warn('⚠  タグ入力欄が見つかりません。手動で追加してください。');
    }
  }

  if (flags.review) {
    console.log('');
    console.log('✨ REVIEW モード：公開直前で停止します。');
    console.log('   内容を確認してから手動で「公開」ボタンを押してください。');
    console.log('   ブラウザはこのまま。Ctrl+C で終了。');
    await new Promise(() => {});
  }

  // ─── 公開ボタンクリック ───
  console.log('🚀 公開ボタンを押下中...');
  const published = await clickByText(page, ['投稿する', '公開する', '公開', '有料エリアありで公開']);
  if (!published) throw new Error('「公開」ボタンが見つかりません');

  await page.waitForTimeout(5000);

  // ─── 公開後URL取得 ───
  const finalUrl = page.url();
  console.log('');
  console.log('==================================================');
  console.log('✅ 公開完了');
  console.log('==================================================');
  console.log(`URL: ${finalUrl}`);
  console.log('');
  console.log('5秒後にブラウザを閉じます...');
  await page.waitForTimeout(5000);
  await browser.close();
  process.exit(0);

} catch (err) {
  console.error('');
  console.error('❌ エラー:', err.message);
  const shotPath = join(__dirname, `error_${Date.now()}.png`);
  await page.screenshot({ path: shotPath, fullPage: true }).catch(() => {});
  console.error(`スクショ保存: ${shotPath}`);
  console.error('ブラウザは開いたままです。手動で続行するか Ctrl+C で終了。');
  await new Promise(() => {});
}
