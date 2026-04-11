#!/bin/zsh
# mac_booth_setup.sh — ChromeのCookieDBから直接取得 → BOOTH出品（DevTools不要）
# 実行: zsh ~/agent-team/mac_booth_setup.sh

set -e

echo "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  BOOTH 自動セットアップ（Mac版）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# パッケージインストール
echo "\n[1/2] パッケージをインストール..."
python3 -m pip install requests browser-cookie3 --break-system-packages -q 2>/dev/null \
  || python3 -m pip install requests browser-cookie3 -q \
  || pip3 install requests browser-cookie3 -q
echo "  ✅ OK"

# 自動取得 → 出品（DevTools不要）
echo "\n[2/2] Chromeからクッキーを自動取得して出品..."
python3 ~/agent-team/mac_auto_cookie.py

echo "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ 完了"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
