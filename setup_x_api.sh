#!/bin/bash
# setup_x_api.sh — X API認証情報をインタラクティブに設定
# 使い方: bash setup_x_api.sh
REPO="$(cd "$(dirname "$0")" && pwd)"
ENV="$REPO/.env"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  X API 認証情報セットアップ"
echo "  取得先: https://developer.twitter.com"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 既存の値を読み込む
if [ -f "$ENV" ]; then
  source "$ENV" 2>/dev/null
  echo "  既存の .env を検出しました（上書き更新）"
  echo ""
fi

read -p "  API Key          : " key
read -p "  API Key Secret   : " secret
read -p "  Access Token     : " token
read -p "  Access Token Sec : " token_secret

cat > "$ENV" <<EOF
X_API_KEY="$key"
X_API_SECRET="$secret"
X_ACCESS_TOKEN="$token"
X_ACCESS_SECRET="$token_secret"
EOF

echo ""
echo "  .env に保存しました → $ENV"
echo ""
echo "  テスト投稿を実行します..."
echo ""
python3 "$REPO/auto_x_api_post.py"
