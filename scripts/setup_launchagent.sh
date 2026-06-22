#!/bin/bash
set -e

# ==================== LaunchAgent セットアップ ====================
# Macで毎日自動実行するための設定
#
# 用途:
#   bash ~/agent-team/scripts/setup_launchagent.sh [install|uninstall|status]
#
# ====================

PLIST_FILE="$HOME/Library/LaunchAgents/com.agentteam.daily-workflow.plist"
PLIST_SOURCE="$HOME/agent-team/scripts/com.agentteam.daily-workflow.plist"

case "${1:-status}" in
  install)
    echo "📦 LaunchAgent をインストール中..."

    # Plistを正しい場所にコピー
    mkdir -p "$HOME/Library/LaunchAgents" 2>/dev/null || true
    cp "$PLIST_SOURCE" "$PLIST_FILE"
    echo "  ✅ Plist コピー完了: $PLIST_FILE"

    # LaunchAgent をロード
    launchctl load "$PLIST_FILE" 2>/dev/null || {
      echo "  ⚠️  既にロード済みまたはエラー。アンロード＆再ロードを試行..."
      launchctl unload "$PLIST_FILE" 2>/dev/null || true
      sleep 1
      launchctl load "$PLIST_FILE"
    }
    echo "  ✅ LaunchAgent ロード完了"

    echo ""
    echo "=========================================="
    echo "✅ セットアップ完了！"
    echo "=========================================="
    echo "実行スケジュール: 毎日 5:30 AM"
    echo "ログ: ~/.claude_daily_YYYYMMDD.log"
    echo ""
    echo "ステータス確認: bash ~/agent-team/scripts/setup_launchagent.sh status"
    echo "手動実行: bash ~/agent-team/scripts/daily_workflow.sh"
    ;;

  uninstall)
    echo "🗑️  LaunchAgent をアンインストール中..."

    if [ -f "$PLIST_FILE" ]; then
      launchctl unload "$PLIST_FILE" 2>/dev/null || echo "  ℹ️  既にアンロード済み"
      rm -f "$PLIST_FILE"
      echo "  ✅ 削除完了"
    else
      echo "  ℹ️  インストール済みではありません"
    fi
    ;;

  status)
    echo "📊 LaunchAgent ステータス"
    echo ""

    if launchctl list | grep -q "com.agentteam.daily-workflow"; then
      echo "  ✅ 状態: アクティブ（自動実行中）"
      echo "  ⏰ 実行時刻: 毎日 5:30 AM"
      echo "  📝 Plist: $PLIST_FILE"
      echo ""
      echo "最新のログ:"
      tail -n 10 ~/.claude_daily_*.log 2>/dev/null || echo "  （ログなし）"
    else
      echo "  ❌ 状態: インストール済みではない"
      echo ""
      echo "インストール: bash ~/agent-team/scripts/setup_launchagent.sh install"
    fi
    ;;

  test)
    echo "🧪 テスト実行（手動ワークフロー）"
    bash "$HOME/agent-team/scripts/daily_workflow.sh"
    ;;

  *)
    echo "使い方: bash ~/agent-team/scripts/setup_launchagent.sh [install|uninstall|status|test]"
    echo ""
    echo "オプション:"
    echo "  install   - LaunchAgent をセットアップ（毎日5:30 AMに自動実行）"
    echo "  uninstall - LaunchAgent を削除"
    echo "  status    - 状態確認＆最新ログ表示"
    echo "  test      - 手動実行してテスト"
    ;;
esac
