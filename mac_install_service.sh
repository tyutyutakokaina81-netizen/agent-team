#!/bin/zsh
# mac_install_service.sh — MacのLaunchAgentとして常駐自動実行を設定
# 実行: zsh ~/agent-team/mac_install_service.sh

set -e
AGENT_DIR="$HOME/agent-team"
PYTHON=$(which python3)
PLIST_DIR="$HOME/Library/LaunchAgents"
mkdir -p "$PLIST_DIR"

echo "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  自動実行サービス インストール"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── BOOTH売上チェック（30分ごと）──────────
cat > "$PLIST_DIR/com.agentteam.sales.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.agentteam.sales</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON</string>
    <string>$AGENT_DIR/mac_check_sales.py</string>
  </array>
  <key>StartInterval</key>
  <integer>1800</integer>
  <key>RunAtLoad</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$AGENT_DIR/logs/sales.log</string>
  <key>StandardErrorPath</key>
  <string>$AGENT_DIR/logs/sales_err.log</string>
</dict>
</plist>
PLIST

# ── 日次レポート（毎朝8時）────────────────
cat > "$PLIST_DIR/com.agentteam.report.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.agentteam.report</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON</string>
    <string>$AGENT_DIR/mac_daily_report.py</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>8</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>$AGENT_DIR/logs/report.log</string>
  <key>StandardErrorPath</key>
  <string>$AGENT_DIR/logs/report_err.log</string>
</dict>
</plist>
PLIST

# ── BOOTH再出品（起動時・毎週日曜22時）────
cat > "$PLIST_DIR/com.agentteam.booth.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.agentteam.booth</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON</string>
    <string>$AGENT_DIR/mac_auto_cookie.py</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key>
    <integer>0</integer>
    <key>Hour</key>
    <integer>22</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$AGENT_DIR/logs/booth.log</string>
  <key>StandardErrorPath</key>
  <string>$AGENT_DIR/logs/booth_err.log</string>
</dict>
</plist>
PLIST

# ── サービス登録 ──────────────────────────
echo "\n[1/2] サービスを登録中..."
for plist in sales report booth; do
  launchctl unload "$PLIST_DIR/com.agentteam.$plist.plist" 2>/dev/null || true
  launchctl load "$PLIST_DIR/com.agentteam.$plist.plist"
  echo "  ✅ com.agentteam.$plist"
done

# ── 即時実行 ──────────────────────────────
echo "\n[2/2] BOOTH出品を今すぐ実行..."
$PYTHON "$AGENT_DIR/mac_auto_cookie.py"

echo "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ インストール完了"
echo "  Mac再起動後も自動で動き続けます"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
