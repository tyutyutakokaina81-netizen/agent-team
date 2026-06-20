#!/bin/bash
# Solo CEO OS — Gumroad自動出品スクリプト
# Macのターミナルで実行してください

set -e

# ============================================================
# ここだけ書き換える（APIトークンとzipファイルのパス）
# ============================================================
ACCESS_TOKEN="ここにGumroadのアクセストークンを貼る"
ZIP_PATH="$HOME/Downloads/Solo_CEO_OS.zip"
# ============================================================

if [ "$ACCESS_TOKEN" = "ここにGumroadのアクセストークンを貼る" ]; then
  echo "エラー: ACCESS_TOKEN を設定してください"
  echo "取得方法: Gumroad → Settings → Advanced → Create application"
  exit 1
fi

if [ ! -f "$ZIP_PATH" ]; then
  echo "エラー: $ZIP_PATH が見つかりません"
  echo "Solo_CEO_OS.zip のパスを確認してください"
  exit 1
fi

echo "=== Solo CEO OS を Gumroad に出品します ==="
echo ""

# 商品を作成
echo "[1/3] 商品を作成中..."
RESPONSE=$(curl -s -X POST "https://api.gumroad.com/v2/products" \
  -d "access_token=$ACCESS_TOKEN" \
  -d "name=Solo CEO OS — Run your business like a company, with AI executives" \
  -d "price=1900" \
  -d "description=Stop using AI as one overworked assistant. Solo CEO OS turns your AI into six specialized executives — Marketing, Product, Finance, Sales, Tech, and Analytics — each with its own role, memory, and output.

What's inside:
• 6 ready-to-paste AI officer prompts (CMO, CPO, CFO, CSO, CDO, CAO)
• The Company Operating System — the rules that make them work as one team
• The folder + memory template that lets each officer build on its past work
• A 4-role document team prompt (Plan → Draft → Summarize → Review)
• A quick-start guide and day-one examples

Works with Claude, ChatGPT, and any capable AI. No install. One-time payment, lifetime updates, 30-day money-back guarantee.

Built and battle-tested running a real one-person business — not invented for a course." \
  -d "tags[]=ai" \
  -d "tags[]=productivity" \
  -d "tags[]=templates" \
  -d "tags[]=solopreneur" \
  -d "tags[]=prompts" \
  -d "tags[]=business" \
  -d "tags[]=chatgpt")

# 商品IDを取得
PRODUCT_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['product']['id'])" 2>/dev/null)

if [ -z "$PRODUCT_ID" ]; then
  echo "エラー: 商品の作成に失敗しました"
  echo "レスポンス: $RESPONSE"
  exit 1
fi

echo "  商品ID: $PRODUCT_ID"

# zipファイルをアップロード
echo "[2/3] Solo_CEO_OS.zip をアップロード中..."
UPLOAD_RESPONSE=$(curl -s -X PUT "https://api.gumroad.com/v2/products/$PRODUCT_ID" \
  -F "access_token=$ACCESS_TOKEN" \
  -F "product_file=@$ZIP_PATH")

UPLOAD_OK=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('success','false'))" 2>/dev/null)

if [ "$UPLOAD_OK" != "True" ]; then
  echo "警告: アップロードの確認ができませんでした"
  echo "レスポンス: $UPLOAD_RESPONSE"
fi

# 商品を公開
echo "[3/3] 商品を公開中..."
PUBLISH_RESPONSE=$(curl -s -X PUT "https://api.gumroad.com/v2/products/$PRODUCT_ID" \
  -d "access_token=$ACCESS_TOKEN" \
  -d "published=true")

PRODUCT_URL=$(echo "$PUBLISH_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['product']['short_url'])" 2>/dev/null)

echo ""
echo "=== 完了！ ==="
echo ""
echo "商品ページ: $PRODUCT_URL"
echo ""
echo "このURLをコピーして教えてください。"
echo "ランディングページに自動で埋め込みます。"
