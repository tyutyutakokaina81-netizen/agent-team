#!/usr/bin/env node
/**
 * notify.mjs — クロスプラットフォーム通知（macOS / Linux / Windows）
 *
 * 費用ゼロ：OS 標準機能（osascript / notify-send / msg）のみ使用
 *
 * 使い方:
 *   node CDO/outputs/notify.mjs "タイトル" "本文" [info|warn|error]
 *   import { notify } from './notify.mjs';
 *   await notify('Agent Team', '今日の朝会が生成されました');
 */

import { execSync } from 'node:child_process';

export function notify(title, body, level = 'info') {
  const safeTitle = (title || 'Agent Team').replace(/"/g, '\\"');
  const safeBody = (body || '').replace(/"/g, '\\"');
  const platform = process.platform;

  try {
    if (platform === 'darwin') {
      // macOS: osascript（標準搭載）
      const sound = level === 'error' ? 'Basso' : level === 'warn' ? 'Glass' : 'Tink';
      execSync(
        `osascript -e 'display notification "${safeBody}" with title "${safeTitle}" sound name "${sound}"'`,
        { stdio: 'ignore' }
      );
    } else if (platform === 'linux') {
      // Linux: notify-send（GNOME / KDE 標準）
      const urgency = level === 'error' ? 'critical' : level === 'warn' ? 'normal' : 'low';
      execSync(
        `notify-send -u ${urgency} "${safeTitle}" "${safeBody}"`,
        { stdio: 'ignore' }
      );
    } else if (platform === 'win32') {
      // Windows: PowerShell の BurntToast 代替として msg コマンド
      execSync(
        `msg * "${safeTitle}: ${safeBody}"`,
        { stdio: 'ignore' }
      );
    }
    return true;
  } catch {
    // 通知失敗は致命的ではないので静かにスキップ
    return false;
  }
}

// CLI 実行時
if (import.meta.url === `file://${process.argv[1]}`) {
  const [title, body, level] = process.argv.slice(2);
  if (!title) {
    console.error('使い方: node notify.mjs "タイトル" "本文" [info|warn|error]');
    process.exit(1);
  }
  const ok = notify(title, body || '', level || 'info');
  console.log(ok ? '✅ 通知送信' : '⚠️ 通知失敗（OS非対応または機能無効）');
}
