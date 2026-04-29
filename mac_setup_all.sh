#!/bin/zsh
# mac_setup_all.sh — Mac 全自動セットアップ（初回1回だけ実行）
set -e
REPO="$HOME/agent-team"
cd "$REPO"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  agent-team セットアップ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. 最新コード取得 ──────────────────────────────────
echo "\n[1/5] 最新コード取得..."
git fetch origin claude/add-claude-documentation-Wipf0
git reset --hard origin/claude/add-claude-documentation-Wipf0
echo "  ✅ 完了"

# ── 2. Python ライブラリ（Homebrew Python 対応）──────────
echo "\n[2/5] Python ライブラリ インストール..."
pip3 install playwright browser-cookie3 requests Pillow numpy \
  --break-system-packages -q 2>/dev/null || \
pip3 install playwright browser-cookie3 requests Pillow numpy -q 2>/dev/null || true
python3 -m playwright install chromium 2>/dev/null || true

# pyopenjtalk（音声合成）
pip3 install pyopenjtalk --break-system-packages -q 2>/dev/null || \
pip3 install pyopenjtalk -q 2>/dev/null || true

echo "  ✅ 完了"

# ── 3. キャラクター画像生成 ───────────────────────────
echo "\n[3/5] キャラクター画像生成..."
mkdir -p CMO/assets/announcer
if [ ! -f "CMO/assets/announcer/ai_takaoka_main.png" ]; then
  python3 make_placeholder_char.py && echo "  ✅ 生成完了"
else
  echo "  ✅ 既存（スキップ）"
fi

# ── 4. LaunchAgent 登録（朝9時 + 夕20時）────────────
echo "\n[4/5] 自動実行スケジュール設定..."

make_plist() {
  local name=$1 hour=$2
  local plist="$HOME/Library/LaunchAgents/${name}.plist"
  cat > "$plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>${name}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>$REPO/run_daily_auto.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>${hour}</integer><key>Minute</key><integer>0</integer></dict>
  <key>WorkingDirectory</key><string>$REPO</string>
  <key>StandardOutPath</key><string>$REPO/logs/launchagent_${hour}h.log</string>
  <key>StandardErrorPath</key><string>$REPO/logs/launchagent_${hour}h_err.log</string>
  <key>RunAtLoad</key><false/>
</dict></plist>
PLIST
  launchctl unload "$plist" 2>/dev/null || true
  launchctl load "$plist"
  echo "  ✅ $name (${hour}:00)"
}

mkdir -p "$HOME/Library/LaunchAgents" "$REPO/logs"
make_plist "com.agent-team.morning" 9
make_plist "com.agent-team.evening" 20

# ── 5. 初回コンテンツ生成 ─────────────────────────────
echo "\n[5/5] 初回コンテンツ生成..."
python3 auto_wikimedia_photos.py 2>/dev/null || true
python3 auto_youtube_produce.py 2>/dev/null || true
echo "  ✅ 完了"

echo "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  セットアップ完了！"
echo ""
echo "  次のステップ:"
echo "  1. Chrome で note.com / x.com / studio.youtube.com に"
echo "     ログインしておく"
echo "  2. zsh run_mac.sh で今すぐ公開できます"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
