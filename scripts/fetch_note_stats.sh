#!/bin/zsh
# fetch_note_stats.sh — noteアクセス数を自動取得して push まで一括（Macで実行）
# 使い方： bash scripts/fetch_note_stats.sh
set -e
cd "$(dirname "$0")/.."

echo "== noteアクセス数を取得中（ログイン済みプロファイル利用・初回はpublish_to_note.py --login が必要） =="
python3 CDO/outputs/note_publisher/fetch_note_stats.py "$@"

echo
echo "== 結果を送り返す（commit & push） =="
git add CAO/outputs/note_stats_top20.md CAO/outputs/note_stats_raw.json 2>/dev/null || true
if git diff --cached --quiet; then
  echo "(コミットする変更なし)"
else
  git commit -m "note統計を自動取得"
  git push && echo "✅ pushしました。リモートAIが次回pullして分析します。"
fi
