#!/bin/zsh
# setup_daily_cron.sh — 毎朝9時に run_daily_auto.sh を自動実行するよう登録（初回のみ）
# 実行: zsh setup_daily_cron.sh

PLIST="$HOME/Library/LaunchAgents/com.agent-team.daily.plist"
REPO="$HOME/agent-team"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.agent-team.daily</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/zsh</string>
        <string>$REPO/run_daily_auto.sh</string>
    </array>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>$REPO/logs/launchd_daily.log</string>
    <key>StandardErrorPath</key>
    <string>$REPO/logs/launchd_daily_err.log</string>

    <key>WorkingDirectory</key>
    <string>$REPO</string>
</dict>
</plist>
EOF

launchctl load "$PLIST"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  毎朝9:00 自動実行を登録しました"
echo ""
echo "  確認: launchctl list | grep agent-team"
echo "  停止: launchctl unload $PLIST"
echo "  手動実行テスト: zsh $REPO/run_daily_auto.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
