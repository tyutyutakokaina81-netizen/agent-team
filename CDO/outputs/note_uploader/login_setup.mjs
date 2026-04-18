#!/usr/bin/env node
/**
 * login_setup.mjs — 初回ログイン用スクリプト
 *
 * 実行：node login_setup.mjs
 *
 * 動作：
 *   1. Chromium ブラウザを起動して note.com のログインページを開く
 *   2. オーナーが手動でログイン（メール/パスワード/2FA も可）
 *   3. ログイン成功（/login から離脱）を検知してセッションを auth-state.json に保存
 *   4. 以降の post_to_note.mjs はこのセッションを使ってログイン状態で動く
 */

import { chromium } from 'playwright';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const AUTH_FILE = join(__dirname, 'auth-state.json');

console.log('');
console.log('🔐 note.com ログインセットアップ');
console.log('================================');
console.log('ブラウザが開きます。note.com にログインしてください。');
console.log('（メール/パスワード/2FA いずれもOK）');
console.log('');
console.log('ログイン完了を自動検知します。最大10分待機します。');
console.log('');

const browser = await chromium.launch({ headless: false });
const context = await browser.newContext();
const page = await context.newPage();

await page.goto('https://note.com/login');

try {
  await page.waitForURL(
    (url) => !url.toString().includes('/login'),
    { timeout: 10 * 60 * 1000 }
  );

  console.log('✅ ログイン検知。セッションを保存中...');
  await context.storageState({ path: AUTH_FILE });
  console.log(`✅ 保存完了: ${AUTH_FILE}`);
  console.log('');
  console.log('次は実投稿を試してください：');
  console.log('  node post_to_note.mjs <記事ファイル.md>');
} catch (err) {
  console.error('❌ ログインがタイムアウトしました（10分）。再度お試しください。');
} finally {
  await browser.close();
}
