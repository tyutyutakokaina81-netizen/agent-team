#!/bin/bash
# クリップボードの内容を drafts/ に自動保存
# 使い方: ./scripts/deliver/save_draft.sh <folder_name> <filename>
#   例: ./scripts/deliver/save_draft.sh "2026-04-21_クライアント_案件" article.md

set -e

# agent-team ルートに絶対パスで移動
REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_DIR"

if [[ $# -lt 2 ]]; then
    echo "使い方: $0 <folder_name> <filename>"
    echo ""
    echo "例:"
    echo "  $0 '2026-04-21_xxx_xxx' structure.md"
    echo "  $0 '2026-04-21_xxx_xxx' article.md"
    exit 1
fi

FOLDER="$1"
FILENAME="$2"
DRAFTS_DIR="$REPO_DIR/deliveries/$FOLDER/drafts"

if [[ ! -d "$REPO_DIR/deliveries/$FOLDER" ]]; then
    echo "❌ 案件フォルダが見つかりません: deliveries/$FOLDER"
    exit 1
fi

mkdir -p "$DRAFTS_DIR"

# クリップボードから取得
if ! command -v pbpaste &>/dev/null; then
    echo "❌ pbpaste が使えません（Mac以外）"
    exit 1
fi

CONTENT=$(pbpaste)

if [[ -z "$CONTENT" ]]; then
    echo "❌ クリップボードが空です"
    echo "   Claudeの返信をコピーしてから再実行してください"
    exit 1
fi

# 保存
OUT_PATH="$DRAFTS_DIR/$FILENAME"
echo "$CONTENT" > "$OUT_PATH"

# 確認
CHARS=$(echo "$CONTENT" | wc -c | tr -d ' ')
LINES=$(echo "$CONTENT" | wc -l | tr -d ' ')

echo "✅ 保存完了: deliveries/$FOLDER/drafts/$FILENAME"
echo "   文字数: $CHARS"
echo "   行数: $LINES"
echo ""
echo "次のステップ："
echo "  python3 scripts/deliver/quality_check.py '$FOLDER'"
