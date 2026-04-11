#!/bin/zsh
# mac_booth_setup.sh — Mac上でBOOTHクッキー取得→出品まで一発完了
# 実行: zsh ~/agent-team/mac_booth_setup.sh

set -e

echo "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  BOOTH 自動セットアップ（Mac版）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# requests インストール
echo "\n[1/3] requests インストール..."
python3 -m pip install requests --break-system-packages -q 2>/dev/null \
  || python3 -m pip install requests -q \
  || pip3 install requests -q
echo "  ✅ OK"

# Chromeからクッキーを自動取得（BOOTHにログイン済みであること）
echo "\n[2/3] Chromeからクッキーを自動取得..."
COOKIE=$(osascript -e '
tell application "Google Chrome"
  execute front window'"'"'s active tab javascript "document.cookie.split(\";\").find(c=>c.includes(\"_booth_session\"))?.split(\"=\").slice(1).join(\"=\")"
end tell
' 2>/dev/null)

if [[ -z "$COOKIE" ]]; then
  echo "  ⚠️  Chrome自動取得失敗。Safariを試します..."
  COOKIE=$(osascript -e '
  tell application "Safari"
    do JavaScript "document.cookie.split(\";\").find(c=>c.includes(\"_booth_session\"))?.split(\"=\").slice(1).join(\"=\")" in front document
  end tell
  ' 2>/dev/null)
fi

if [[ -z "$COOKIE" ]]; then
  echo "  ❌ 自動取得失敗。クッキーを手動で貼り付けてください:"
  read -r COOKIE
fi

echo "  ✅ クッキー取得完了（先頭20文字: ${COOKIE:0:20}...）"

# 出品実行
echo "\n[3/3] BOOTH に出品中..."
python3 ~/agent-team/booth_requests.py --cookie "$COOKIE"

echo "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ 完了"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
