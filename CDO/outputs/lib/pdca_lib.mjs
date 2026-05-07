/**
 * pdca_lib.mjs — PDCA スクリプト共通ユーティリティ
 *
 * 重複していた以下の関数を集約：
 *   - today(): YYYY-MM-DD 形式の今日の日付
 *   - dayOfWeekJa(): 日本語の曜日 1文字
 *   - safe(fn, fallback): try/catch ラッパー
 *   - sh(cmd, opts): シェルコマンド実行（失敗時は空文字）
 *
 * 費用ゼロ：Node 標準モジュールのみ
 */

import { execSync } from 'node:child_process';

export function today() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

export function dayOfWeekJa() {
  return ['日', '月', '火', '水', '木', '金', '土'][new Date().getDay()];
}

export function safe(fn, fallback) {
  try { return fn(); } catch { return fallback; }
}

export function sh(cmd, opts = {}) {
  return safe(() => execSync(cmd, { encoding: 'utf-8', ...opts }).trim(), '');
}
