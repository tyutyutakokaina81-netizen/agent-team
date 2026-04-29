#!/bin/zsh
# mac_setup_all.sh — Mac上での全自動セットアップ＆初回実行
# 実行: zsh mac_setup_all.sh
set -e
REPO="$HOME/agent-team"
cd "$REPO"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  agent-team 全自動セットアップ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. 依存ライブラリ ──────────────────────────────────
echo "\n[1/6] Python ライブラリ インストール..."
pip3 install --break-system-packages -q \
  playwright \
  browser-cookie3 \
  requests \
  Pillow \
  numpy \
  google-api-python-client \
  google-auth-httplib2 \
  google-auth-oauthlib \
  pyopenjtalk 2>/dev/null || true
python3 -m playwright install chromium 2>/dev/null || true
echo "  ✅ 完了"

# ── 2. Chromeクッキー自動取得 ─────────────────────────
echo "\n[2/6] Chrome セッション取得..."
if python3 mac_auto_cookie_all.py 2>/dev/null; then
  echo "  ✅ セッション取得完了"
else
  echo "  ⚠️  Chrome未起動 or ログイン未確認（後で再実行可）"
fi

# ── 3. キャラクター画像生成 ───────────────────────────
echo "\n[3/6] キャラクター画像生成..."
mkdir -p CMO/assets/announcer
if [ ! -f "CMO/assets/announcer/ai_takaoka_main.png" ]; then
  python3 make_placeholder_char.py
else
  echo "  ✅ 既存（スキップ）"
fi

# ── 4. 音声付き動画生成 ───────────────────────────────
echo "\n[4/6] 音声付き動画生成..."
python3 auto_youtube_produce.py

# ── 5. YouTube セッション取得（Chromeクッキー） ───────────
echo "\n[5/6] YouTube セッション取得..."
python3 -c "
import sys; sys.path.insert(0, '.')
exec(open('auto_youtube_upload.py').read())
extract_youtube_cookies()
" && echo "  ✅ YouTubeセッション準備完了"

# ── 6. LaunchAgent 登録（朝9時 + 夕20時）────────────
echo "\n[6/6] 自動実行スケジュール設定（朝9時・夕20時）..."

make_plist() {
  local name=$1 hour=$2
  local plist="$HOME/Library/LaunchAgents/com.agent-team.${name}.plist"
  cat > "$plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.agent-team.${name}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>$REPO/run_daily_auto.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>${hour}</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
  <key>StandardOutPath</key><string>$REPO/logs/launchd_${name}.log</string>
  <key>StandardErrorPath</key><string>$REPO/logs/launchd_${name}_err.log</string>
  <key>WorkingDirectory</key><string>$REPO</string>
</dict>
</plist>
EOF
  launchctl unload "$plist" 2>/dev/null || true
  launchctl load "$plist"
  echo "  ✅ ${hour}時に自動実行登録完了"
}

make_plist "morning" 9
make_plist "evening" 20

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  セットアップ完了！"
echo ""
echo "  自動実行スケジュール:"
echo "  ・毎朝9時: X投稿 → CW応募 → CW出品"
echo "  ・月・木 9時: YouTube動画生成 → アップロード"
echo ""
echo "  今すぐ手動実行する場合:"
echo "  zsh run_daily_auto.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
