#!/bin/bash
# いま来ているコメントを取りに行く（見直しも含めて全記事）。
# 読み取りだけ。note 側は変更しない。
set -e
cd "$(dirname "$0")/.."
echo "=== コメントを取りに行く（全記事・見直し込み）==="
python3 CDO/outputs/note_publisher/fetch_note_comments.py --rescan --limit 0 --debug
echo ""
echo "=== 仕分け ==="
python3 ops/draft_comment_replies.py --write || true
echo ""
echo "=== commit & push ==="
git add -A ops/comments 2>/dev/null || true
git commit -q -m "comments: 取得結果（$(date +%Y-%m-%d_%H%M)）" 2>/dev/null \
  && git push -u origin main 2>&1 | tail -1 || echo "新しいコメントは無し"
echo ""
echo "※ 本文が取れなかった記事があれば、保存HTMLも一緒に push されます。"
echo "   その場合は『コメントきてる』ともう一度言ってください。保存HTMLから返信文を書きます。"
