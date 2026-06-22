#!/bin/zsh
# cowork_sync.sh — Cowork(Mac)用：最新を取り込んで連携ボードを表示する
# 使い方： bash scripts/cowork_sync.sh
set -e

# このスクリプトの位置からリポジトリルートへ移動
cd "$(dirname "$0")/.."

echo "== git pull =="
git pull --no-edit

echo
echo "================ context/COWORK_HANDOFF.md ================"
cat context/COWORK_HANDOFF.md
echo "=========================================================="
echo
echo "▶ 次：未処理タスク(□)を実行し、結果欄に記入したら下記で送り返す"
echo "   git add -A && git commit -m '結果記入' && git push"
