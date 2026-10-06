#!/bin/bash
# 公開したはずの記事が、読者に本当に見えているかを全件確かめる。
# 読み取りだけ。ログインしない（読者とまったく同じ条件で見る）。
set -e
cd "$(dirname "$0")/.."
echo "=== 読者に見えているかを確認（ログアウト状態・読み取りのみ）==="
python3 CDO/outputs/note_publisher/check_public_all.py "$@"
echo ""
echo "=== commit & push ==="
git add -A ops/public_status.tsv 2>/dev/null || true
git commit -q -m "check: 記事が読者に見えているかの確認結果（$(date +%Y-%m-%d_%H%M)）" 2>/dev/null \
  && git push -u origin main 2>&1 | tail -1 || echo "変更なし"
