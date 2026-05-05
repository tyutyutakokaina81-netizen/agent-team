#!/bin/zsh
# iPhone 連携の初回セットアップを1コマンドで:
#   - AI_AUTO_TOKEN を生成して .env に追記（既存なら保持）
#   - サーバーを LAN 公開モードで起動
#   - mac の IP・トークン・URL を表示
#
# 使い方:
#   ~/ai-auto/quick_start.sh
#   ~/ai-auto/quick_start.sh local     # mac 内のみ（127.0.0.1）
#   ~/ai-auto/quick_start.sh stop      # サーバー停止

set -e
cd "$HOME/ai-auto"

case "${1:-lan}" in
  stop)
    bash run_server.sh stop
    exit 0
    ;;
esac

# 1) AI_AUTO_TOKEN を確認・生成
if [ ! -f .env ]; then
  echo "ERROR: ~/ai-auto/.env がありません。先に install.sh を実行してください："
  echo "    bash ~/agent-team/projects/2026-05-05_AI自動収益化引き継ぎ/deploy/install.sh"
  exit 1
fi

if grep -q '^AI_AUTO_TOKEN=.\+' .env; then
  echo "✓ 既存の AI_AUTO_TOKEN を使用"
else
  TOKEN="$(openssl rand -hex 24)"
  if grep -q '^AI_AUTO_TOKEN=' .env; then
    sed -i.bak "s|^AI_AUTO_TOKEN=.*|AI_AUTO_TOKEN=$TOKEN|" .env && rm -f .env.bak
  else
    echo "AI_AUTO_TOKEN=$TOKEN" >> .env
  fi
  echo "✓ AI_AUTO_TOKEN を生成しました"
fi

TOKEN_VALUE="$(grep '^AI_AUTO_TOKEN=' .env | cut -d= -f2-)"
PORT="$(grep '^AI_AUTO_PORT=' .env 2>/dev/null | cut -d= -f2- || echo 8765)"
PORT="${PORT:-8765}"

# 2) IP取得
if command -v ipconfig >/dev/null 2>&1; then
  IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo '127.0.0.1')"
else
  IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
  IP="${IP:-127.0.0.1}"
fi

# 3) サーバー起動
case "${1:-lan}" in
  local)
    bash run_server.sh
    BIND_DESC="mac内のみ（127.0.0.1）"
    URL="http://127.0.0.1:${PORT}"
    ;;
  *)
    bash run_server.sh lan
    BIND_DESC="LAN公開（同一Wi-Fi）"
    URL="http://${IP}:${PORT}"
    ;;
esac

# 4) iPhone 設定情報を表示
echo ""
echo "============================================"
echo "  iPhone ショートカット設定情報"
echo "============================================"
echo ""
echo "  ベース URL : $URL"
echo "  トークン   : $TOKEN_VALUE"
echo "  モード     : $BIND_DESC"
echo ""
echo "  動作確認 (mac):"
echo "    curl '$URL/health'"
echo "    curl '$URL/kpi?token=$TOKEN_VALUE'"
echo ""
echo "  iPhone のショートカットアプリで4本のレシピを作成："
echo "    詳細: ~/ai-auto/iphone_shortcuts.md"
echo ""
echo "  外出先からも使う場合："
echo "    Tailscale をインストール（mac+iPhone両方）"
echo "    URL の IP を Tailscale の 100.x.y.z に置き換える"
echo ""
echo "  サーバー停止: ~/ai-auto/quick_start.sh stop"
echo "============================================"
