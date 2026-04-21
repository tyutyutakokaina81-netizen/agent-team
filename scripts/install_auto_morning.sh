#!/bin/bash
# Mac launchd に毎朝8時の自動実行を登録するインストーラ
# 使い方: ./scripts/install_auto_morning.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

MORNING_TEMPLATE="$SCRIPT_DIR/com.user.agent-team.morning.plist.template"
MORNING_DEST="$HOME/Library/LaunchAgents/com.user.agent-team.morning.plist"
LOGIN_TEMPLATE="$SCRIPT_DIR/com.user.agent-team.login.plist.template"
LOGIN_DEST="$HOME/Library/LaunchAgents/com.user.agent-team.login.plist"

echo "========================================"
echo "🔧 自動デイリールーティン インストーラ"
echo "  ・毎日20:00 自動更新"
echo "  ・Mac起動時 ダッシュボード自動表示"
echo "========================================"

# LaunchAgents ディレクトリ作成
mkdir -p "$HOME/Library/LaunchAgents"
mkdir -p "$REPO_DIR/logs"

# ========== 20:00自動実行 ==========
echo "📝 [1/2] 20:00自動実行 plist 生成..."
sed "s|{{REPO_DIR}}|$REPO_DIR|g" "$MORNING_TEMPLATE" > "$MORNING_DEST"

if launchctl list | grep -q "com.user.agent-team.morning"; then
    launchctl unload "$MORNING_DEST" 2>/dev/null || true
fi
launchctl load "$MORNING_DEST"

# ========== Mac起動時ダッシュボード自動表示 ==========
echo "📝 [2/2] ログイン時ダッシュボード自動表示 plist 生成..."
sed "s|{{REPO_DIR}}|$REPO_DIR|g" "$LOGIN_TEMPLATE" > "$LOGIN_DEST"

if launchctl list | grep -q "com.user.agent-team.login"; then
    launchctl unload "$LOGIN_DEST" 2>/dev/null || true
fi
launchctl load "$LOGIN_DEST"

# 確認
MORNING_OK=$(launchctl list | grep -c "com.user.agent-team.morning" || echo "0")
LOGIN_OK=$(launchctl list | grep -c "com.user.agent-team.login" || echo "0")

if [[ "$MORNING_OK" -gt 0 ]] && [[ "$LOGIN_OK" -gt 0 ]]; then
    echo ""
    echo "========================================"
    echo "🎉 インストール完了"
    echo "========================================"
    echo ""
    echo "📅 毎日20:00に自動更新されます（PC寝てても起動時キャッチアップ）"
    echo "🌐 Mac起動/ログイン時にダッシュボードが自動で開きます"
    echo "📂 ログ: $REPO_DIR/logs/cron.log"
    echo ""
    echo "【確認コマンド】"
    echo "  launchctl list | grep agent-team"
    echo ""
    echo "【今すぐ手動テスト】"
    echo "  launchctl start com.user.agent-team.morning  # デイリールーティン"
    echo "  launchctl start com.user.agent-team.login    # ダッシュボード表示"
    echo ""
    echo "【解除（自動実行をやめる）】"
    echo "  launchctl unload ~/Library/LaunchAgents/com.user.agent-team.morning.plist"
    echo "  launchctl unload ~/Library/LaunchAgents/com.user.agent-team.login.plist"
else
    echo "❌ 登録失敗。"
    [[ "$MORNING_OK" -eq 0 ]] && echo "  morning.plist の登録に失敗"
    [[ "$LOGIN_OK" -eq 0 ]] && echo "  login.plist の登録に失敗"
    exit 1
fi
