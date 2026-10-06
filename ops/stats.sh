#!/bin/bash
# note の閲覧数を取ってきて、何が読まれているかを出す。
# 読み取りだけ。note 側は一切変更しない（公開・下書き・スキ・フォローに触らない）。
set -e
cd "$(dirname "$0")/.."
echo "=== 1/3 note のダッシュボードから閲覧数を取る ==="
python3 CDO/outputs/note_publisher/fetch_note_stats.py --go --all || {
  echo ""
  echo "取れなかった。ログインが切れている可能性が高い:"
  echo "  python3 CDO/outputs/note_publisher/publish_to_note.py --login"
  echo "画面の実物は ops/logs/note_stats_dump.json に残っている（これを見て直せる）"
  exit 1
}
echo ""
echo "=== 2/3 記事の作り方と突き合わせる ==="
python3 ops/analyze_stats.py || true
echo ""
echo "=== 3/3 commit & push ==="
git add -A ops/note_stats.tsv ops/logs/note_stats_dump.json CAO/outputs 2>/dev/null || true
git commit -q -m "stats: note 閲覧数を取得（$(date +%Y-%m-%d_%H%M)）" 2>/dev/null \
  && git push -u origin main 2>&1 | tail -1 || echo "変更なし"
