#!/bin/bash
set -euo pipefail

# SessionStart hook: 永続メモリをセッション開始時のコンテキストへ流し込む。
# stdout は SessionStart の追加コンテキストとして取り込まれる。
# 依存インストールは行わない（このリポジトリの「実行して」=note記事作成に不要）。

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
STATE_FILE="$PROJECT_DIR/context/STATE.md"

# 肥大化ガード（2026-07-15 追加）：STATE.md が大きすぎると SessionStart の出力上限を超え、
# 記憶が truncate されて実質ロードされなくなる。閾値を超えたら先頭で警告を出す。
STATE_MAX_BYTES=20000

echo "================ 記憶ロード: context/STATE.md ================"
if [ -f "$STATE_FILE" ]; then
  STATE_BYTES=$(wc -c < "$STATE_FILE" | tr -d ' ')
  if [ "$STATE_BYTES" -gt "$STATE_MAX_BYTES" ]; then
    echo "⚠️ 警告: context/STATE.md が ${STATE_BYTES} バイト（上限 ${STATE_MAX_BYTES}）。"
    echo "⚠️ このままでは SessionStart 出力が truncate され記憶がロードされない恐れ。"
    echo "⚠️ 古い項目を context/STATE_ARCHIVE.md へ退避し、STATE.md を軽量化すること。"
    echo ""
  fi
  cat "$STATE_FILE"
else
  echo "(context/STATE.md が見つかりません。新規作成してください)"
fi
echo "================ 記憶ロードここまで ================"
echo ""
echo "リマインド: オーナーが「実行して」と言ったら、上記プロトコルに従い今日のnote記事を作成し、完了時に無確認で自動commit&pushすること。"
echo "詳細な過去の経緯・全決定ログは context/STATE_ARCHIVE.md にある（自動ロードはされない）。"

exit 0
