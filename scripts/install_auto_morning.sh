#!/bin/bash
# Mac launchd に毎朝8時の自動実行を登録するインストーラ
# 使い方: ./scripts/install_auto_morning.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

PLIST_TEMPLATE="$SCRIPT_DIR/com.user.agent-team.morning.plist.template"
PLIST_DEST="$HOME/Library/LaunchAgents/com.user.agent-team.morning.plist"

echo "========================================"
echo "🔧 自動デイリールーティン インストーラ（毎日20:00）"
echo "========================================"

# LaunchAgents ディレクトリ作成
mkdir -p "$HOME/Library/LaunchAgents"

# テンプレートに REPO_DIR を埋め込んで plist 生成
echo "📝 plistファイル生成: $PLIST_DEST"
sed "s|{{REPO_DIR}}|$REPO_DIR|g" "$PLIST_TEMPLATE" > "$PLIST_DEST"

# 既存の登録があれば外す
if launchctl list | grep -q "com.user.agent-team.morning"; then
    echo "🔄 既存登録を削除..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
fi

# 登録
echo "✅ launchd に登録..."
launchctl load "$PLIST_DEST"

# 確認
if launchctl list | grep -q "com.user.agent-team.morning"; then
    echo ""
    echo "========================================"
    echo "🎉 インストール完了"
    echo "========================================"
    echo ""
    echo "📅 毎日20:00に自動実行されます"
    echo "（その時刻PCが寝てても、次回起動時にキャッチアップ）"
    echo "📂 ログ: $REPO_DIR/logs/cron.log"
    echo ""
    echo "【確認コマンド】"
    echo "  launchctl list | grep agent-team"
    echo ""
    echo "【テスト実行（手動で今すぐ走らせる）】"
    echo "  launchctl start com.user.agent-team.morning"
    echo ""
    echo "【解除（自動実行をやめる）】"
    echo "  launchctl unload ~/Library/LaunchAgents/com.user.agent-team.morning.plist"
else
    echo "❌ 登録失敗。plistの内容を確認してください："
    cat "$PLIST_DEST"
    exit 1
fi
