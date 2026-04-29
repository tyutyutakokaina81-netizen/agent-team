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

# ── 5. YouTube OAuth 認証 ─────────────────────────────
echo "\n[5/6] YouTube 認証..."
SECRETS="$REPO/.sessions/yt_client_secrets.json"
if [ ! -f "$SECRETS" ]; then
  echo ""
  echo "  ┌─────────────────────────────────────────┐"
  echo "  │  YouTube アップロードに1回だけ手動設定が必要  │"
  echo "  └─────────────────────────────────────────┘"
  echo ""
  echo "  以下を実行してください（所要約3分）:"
  echo "  1. 下記URLをブラウザで開く"
  echo "     → https://console.cloud.google.com/"
  echo "  2. 新規プロジェクト作成"
  echo "  3. 「APIとサービス」→「ライブラリ」→ YouTube Data API v3 を有効化"
  echo "  4. 「認証情報」→「認証情報を作成」→「OAuthクライアントID」"
  echo "     → アプリの種類:「デスクトップアプリ」→ 作成"
  echo "  5. JSONをダウンロード → 以下に保存:"
  echo "     $SECRETS"
  echo ""
  echo "  保存後、もう一度このスクリプトを実行してください:"
  echo "  zsh mac_setup_all.sh"
  echo ""
  open "https://console.cloud.google.com/" 2>/dev/null || true
else
  python3 auto_youtube_upload.py --setup && echo "  ✅ YouTube認証完了"
fi

# ── 6. LaunchAgent 登録（毎朝9時自動実行）────────────
echo "\n[6/6] 毎日9時の自動実行を設定..."
PLIST="$HOME/Library/LaunchAgents/com.agent-team.daily.plist"
cat > "$PLIST" << PLIST_EOF
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
  <string>$REPO/logs/launchd_stdout.log</string>
  <key>StandardErrorPath</key>
  <string>$REPO/logs/launchd_stderr.log</string>
  <key>WorkingDirectory</key>
  <string>$REPO</string>
</dict>
</plist>
PLIST_EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "  ✅ 毎朝9時に自動実行されます"

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
