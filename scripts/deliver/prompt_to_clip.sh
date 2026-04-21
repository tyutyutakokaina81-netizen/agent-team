#!/bin/bash
# プロンプトをクリップボードにコピー＆Claude.aiを開く（任意）
# 使い方: ./scripts/deliver/prompt_to_clip.sh <folder_name> <prompt_filename>
#   例: ./scripts/deliver/prompt_to_clip.sh "2026-04-21_..." 1_structure.md

set -e

REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_DIR"

if [[ $# -lt 2 ]]; then
    echo "使い方: $0 <folder_name> <prompt_filename>"
    echo ""
    echo "例:"
    echo "  $0 '2026-04-21_xxx_xxx' 1_structure.md"
    echo "  $0 '2026-04-21_xxx_xxx' 2_body.md"
    exit 1
fi

FOLDER="$1"
PROMPT="$2"
PROMPT_PATH="$REPO_DIR/deliveries/$FOLDER/prompts/$PROMPT"

if [[ ! -f "$PROMPT_PATH" ]]; then
    echo "❌ プロンプトが見つかりません: $PROMPT_PATH"
    exit 1
fi

# クリップボードにコピー
cat "$PROMPT_PATH" | pbcopy

CHARS=$(wc -c < "$PROMPT_PATH" | tr -d ' ')

echo "✅ クリップボードにコピー完了"
echo "   ファイル: prompts/$PROMPT"
echo "   文字数: $CHARS"
echo ""
echo "🎯 次にやること："
echo "   1. Claude.aiを開く（もしくはこのClaude Codeで）"
echo "   2. Cmd+V で貼り付け → 送信"
echo "   3. 返信をコピー（Cmd+A → Cmd+C）"
echo "   4. 以下のコマンドで保存："
echo ""

# 対応するsave先のファイル名を提案
OUT_NAME="${PROMPT}"
[[ "$PROMPT" == "1_structure.md" ]] && OUT_NAME="1_structure.md"
[[ "$PROMPT" == "2_body.md" ]] && OUT_NAME="article.md"

echo "   ./scripts/deliver/save_draft.sh '$FOLDER' '$OUT_NAME'"
echo ""

# Claude.ai を開くかを聞く（任意）
if command -v open &>/dev/null; then
    read -p "   Claude.ai を今ブラウザで開きますか？ (y/N): " OPEN_CLAUDE
    if [[ "$OPEN_CLAUDE" = "y" ]] || [[ "$OPEN_CLAUDE" = "Y" ]]; then
        open "https://claude.ai/new"
    fi
fi
