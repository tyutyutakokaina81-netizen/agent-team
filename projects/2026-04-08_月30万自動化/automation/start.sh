#!/bin/bash
# 公開自動化の起動スクリプト
# 使い方:
#   bash projects/2026-04-08_月30万自動化/automation/start.sh           # フル実行
#   bash projects/2026-04-08_月30万自動化/automation/start.sh setup     # セッション設定のみ
#   bash projects/2026-04-08_月30万自動化/automation/start.sh note      # note 公開のみ
#   bash projects/2026-04-08_月30万自動化/automation/start.sh x         # X 投稿のみ

set -e

AUTO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$AUTO_DIR"

if [ ! -d .venv ]; then
  echo "[ERROR] venv が存在しません。先に以下を実行してください："
  echo "  bash $AUTO_DIR/setup.sh"
  exit 1
fi

source .venv/bin/activate

CMD="${1:-all}"

case "$CMD" in
  setup)
    python3 00_session_setup.py
    ;;
  note)
    python3 publish_note.py all
    ;;
  x)
    python3 post_x.py all
    ;;
  all)
    # まずセッション状態をチェック
    if [ ! -f .sessions/note_session.json ] || [ ! -f .sessions/x_session.json ]; then
      echo "[INFO] セッション未保存です。セットアップを実行します。"
      python3 00_session_setup.py
    fi
    python3 run_all.py
    ;;
  *)
    echo "使い方: bash start.sh [setup|note|x|all]"
    exit 1
    ;;
esac
