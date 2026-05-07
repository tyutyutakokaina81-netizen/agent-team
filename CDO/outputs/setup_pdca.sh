#!/bin/bash
# setup_pdca.sh — PDCA 日次サイクルのスケジュール自動セットアップ
#
# 対応OS: macOS (launchd) / Linux (cron) / Windows (msg only)
# 費用ゼロ：OS 標準機能のみ使用

set -e

# リポジトリの絶対パスを自動取得
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
NODE_BIN="$(command -v node || echo /usr/local/bin/node)"

# 確認
echo "━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 PDCA スケジュール セットアップ"
echo "━━━━━━━━━━━━━━━━━━━━━━━"
echo "リポジトリ：$REPO_ROOT"
echo "Node：$NODE_BIN"
echo "OS：$(uname -s)"
echo ""

if [ ! -x "$NODE_BIN" ] && [ ! -f "$NODE_BIN" ]; then
  echo "❌ Node が見つかりません。'which node' で確認してください。"
  exit 1
fi

# 確認プロンプト
read -p "毎朝7:30に朝会、夕方17:00にチェックインを自動実行します。続行しますか？ [y/N] " confirm
case "$confirm" in
  [yY]|[yY][eE][sS]) ;;
  *) echo "中止しました。"; exit 0 ;;
esac

case "$(uname -s)" in
  Darwin)
    echo ""
    echo "📱 macOS：launchd で設定します"
    LA_DIR="$HOME/Library/LaunchAgents"
    mkdir -p "$LA_DIR"

    # 朝会 plist
    cat > "$LA_DIR/com.agent-team.morning-meeting.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.agent-team.morning-meeting</string>
    <key>ProgramArguments</key>
    <array>
        <string>$NODE_BIN</string>
        <string>$REPO_ROOT/CDO/outputs/morning_meeting.mjs</string>
    </array>
    <key>WorkingDirectory</key><string>$REPO_ROOT</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key><integer>7</integer>
        <key>Minute</key><integer>30</integer>
    </dict>
    <key>StandardOutPath</key><string>/tmp/agent-team-morning.log</string>
    <key>StandardErrorPath</key><string>/tmp/agent-team-morning.err</string>
</dict>
</plist>
EOF

    # 夕会 plist
    cat > "$LA_DIR/com.agent-team.evening-checkin.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.agent-team.evening-checkin</string>
    <key>ProgramArguments</key>
    <array>
        <string>$NODE_BIN</string>
        <string>$REPO_ROOT/CDO/outputs/evening_checkin.mjs</string>
    </array>
    <key>WorkingDirectory</key><string>$REPO_ROOT</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key><integer>17</integer>
        <key>Minute</key><integer>0</integer>
    </dict>
    <key>StandardOutPath</key><string>/tmp/agent-team-evening.log</string>
    <key>StandardErrorPath</key><string>/tmp/agent-team-evening.err</string>
</dict>
</plist>
EOF

    # 既存をアンロードしてから登録
    launchctl unload "$LA_DIR/com.agent-team.morning-meeting.plist" 2>/dev/null || true
    launchctl unload "$LA_DIR/com.agent-team.evening-checkin.plist" 2>/dev/null || true
    launchctl load "$LA_DIR/com.agent-team.morning-meeting.plist"
    launchctl load "$LA_DIR/com.agent-team.evening-checkin.plist"

    echo "✅ launchd 登録完了"
    echo "    朝会：毎朝 7:30"
    echo "    夕会：毎夕 17:00"
    echo ""
    echo "確認：launchctl list | grep agent-team"
    echo "解除：bash $REPO_ROOT/CDO/outputs/setup_pdca.sh --unload"
    ;;

  Linux)
    echo ""
    echo "🐧 Linux：crontab で設定します"

    # 既存の Agent Team 関連エントリを削除
    CRON_TMP=$(mktemp)
    crontab -l 2>/dev/null | grep -v "agent-team" > "$CRON_TMP" || true

    # 新エントリ追加
    cat >> "$CRON_TMP" <<EOF
# Agent Team PDCA - 朝会
30 7 * * * cd $REPO_ROOT && $NODE_BIN CDO/outputs/morning_meeting.mjs >> /tmp/agent-team-morning.log 2>&1
# Agent Team PDCA - 夕会
0 17 * * * cd $REPO_ROOT && $NODE_BIN CDO/outputs/evening_checkin.mjs >> /tmp/agent-team-evening.log 2>&1
EOF

    crontab "$CRON_TMP"
    rm -f "$CRON_TMP"

    echo "✅ crontab 登録完了"
    echo "    朝会：毎朝 7:30"
    echo "    夕会：毎夕 17:00"
    echo ""
    echo "確認：crontab -l | grep agent-team"
    echo "解除：bash $REPO_ROOT/CDO/outputs/setup_pdca.sh --unload"
    ;;

  CYGWIN*|MINGW*|MSYS*)
    echo ""
    echo "🪟 Windows：タスク スケジューラ用 PowerShell スクリプトを生成します"
    cat > "$REPO_ROOT/CDO/outputs/setup_pdca_windows.ps1" <<EOF
# Windows タスク スケジューラ登録
\$action = New-ScheduledTaskAction -Execute "$NODE_BIN" -Argument "$REPO_ROOT\\CDO\\outputs\\morning_meeting.mjs" -WorkingDirectory "$REPO_ROOT"
\$trigger = New-ScheduledTaskTrigger -Daily -At 7:30AM
Register-ScheduledTask -TaskName "AgentTeamMorning" -Action \$action -Trigger \$trigger

\$action2 = New-ScheduledTaskAction -Execute "$NODE_BIN" -Argument "$REPO_ROOT\\CDO\\outputs\\evening_checkin.mjs" -WorkingDirectory "$REPO_ROOT"
\$trigger2 = New-ScheduledTaskTrigger -Daily -At 5:00PM
Register-ScheduledTask -TaskName "AgentTeamEvening" -Action \$action2 -Trigger \$trigger2
EOF
    echo "PowerShell（管理者）で実行してください："
    echo "  powershell -ExecutionPolicy Bypass -File $REPO_ROOT/CDO/outputs/setup_pdca_windows.ps1"
    ;;

  *)
    echo "❌ 未対応の OS：$(uname -s)"
    echo "手動で：node CDO/outputs/morning_meeting.mjs を毎朝、 evening_checkin.mjs を毎夕"
    exit 1
    ;;
esac

# アンロードオプション
if [ "$1" = "--unload" ]; then
  case "$(uname -s)" in
    Darwin)
      launchctl unload "$HOME/Library/LaunchAgents/com.agent-team.morning-meeting.plist" 2>/dev/null
      launchctl unload "$HOME/Library/LaunchAgents/com.agent-team.evening-checkin.plist" 2>/dev/null
      rm -f "$HOME/Library/LaunchAgents/com.agent-team.morning-meeting.plist"
      rm -f "$HOME/Library/LaunchAgents/com.agent-team.evening-checkin.plist"
      echo "✅ 解除完了"
      ;;
    Linux)
      CRON_TMP=$(mktemp)
      crontab -l 2>/dev/null | grep -v "agent-team" > "$CRON_TMP" || true
      crontab "$CRON_TMP"
      rm -f "$CRON_TMP"
      echo "✅ 解除完了"
      ;;
  esac
  exit 0
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ セットアップ完了"
echo "━━━━━━━━━━━━━━━━━━━━━━━"
echo "次の手順："
echo "  1. 動作テスト：node CDO/outputs/morning_meeting.mjs"
echo "  2. ヘルスチェック：node CDO/outputs/pdca_status.mjs"
echo "  3. 数字入力：node CDO/outputs/metrics_input.mjs --quick"
echo ""
echo "費用：¥0（OS 標準機能のみ使用）"
