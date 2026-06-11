#!/bin/bash
set -euo pipefail

# SessionStart hook: 永続メモリをセッション開始時のコンテキストへ流し込む。
# stdout は SessionStart の追加コンテキストとして取り込まれる。
# 依存インストールは行わない（このリポジトリの「実行して」=note記事作成に不要）。

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
STATE_FILE="$PROJECT_DIR/context/STATE.md"

echo "================ 記憶ロード: context/STATE.md ================"
if [ -f "$STATE_FILE" ]; then
  cat "$STATE_FILE"
else
  echo "(context/STATE.md が見つかりません。新規作成してください)"
fi
echo "================ 記憶ロードここまで ================"
echo ""
echo "リマインド: オーナーが「実行して」と言ったら、上記プロトコルに従い今日のnote記事を作成し、完了時に無確認で自動commit&pushすること。"

exit 0
