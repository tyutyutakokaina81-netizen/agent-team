#!/usr/bin/env node
/**
 * login_setup.mjs — 初回ログイン用スクリプト（Enter 待機方式）
 *
 * 実行：node login_setup.mjs
 *
 * 動作：
 *   1. Chromium ブラウザを起動して note.com のログインページを開く
 *   2. オーナーが手動でログイン
 *   3. ターミナルで Enter を押すとセッションを auth-state.json に保存
 *   4. 以降の post_to_note.mjs はこのセッションを使う
 */

import { chromium } from 'playwright';
import readline from 'node:readline';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const AUTH_FILE = join(__dirname, 'auth-state.json');

console.log('');
console.log('🔐 note.com ログインセットアップ');
console.log('================================');
console.log('ブラウザが開きます。noteに **メールアドレス+パスワード** でログインしてください。');
console.log('（Google/Twitterログインは自動化検知で弾かれることが多いので避ける）');
console.log('');

const browser = await chromium.launch({
  headless: false,
  args: [
    '--disable-blink-features=AutomationControlled',
    '--disable-infobars',
    '--no-default-browser-check',
  ],
});
const context = await browser.newContext({
  userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36',
  viewport: { width: 1280, height: 800 },
  locale: 'ja-JP',
  timezoneId: 'Asia/Tokyo',
});
await context.addInitScript(() => {
  Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
});
const page = await context.newPage();

await page.goto('https://note.com/login');

console.log('⚠ 重要：ログイン完了するまでブラウザを閉じないでください');
console.log('');
console.log('✋ ログインが完全に完了したら（マイページが表示された状態で）、');
console.log('   このターミナルで Enter キーを押してください');
console.log('');

const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
await new Promise((resolve) => {
  rl.question('→ 完了したら Enter: ', () => {
    rl.close();
    resolve();
  });
});

try {
  console.log('');
  console.log(`📍 現在のURL: ${page.url()}`);
  console.log('📝 セッションを保存中...');
  await context.storageState({ path: AUTH_FILE });
  console.log(`✅ 保存完了: ${AUTH_FILE}`);
  console.log('');
  console.log('次は実投稿を試してください：');
  console.log('  node post_to_note.mjs <記事ファイル.md>');
} catch (err) {
  console.error('❌ 保存エラー:', err.message);
} finally {
  await browser.close();
  process.exit(0);
}
