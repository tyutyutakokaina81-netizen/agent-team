#!/bin/bash
# 拡張子なし launcher（チャット→ターミナル時の markdown 自動リンク化を回避）
# 使い方:
#   bash go            # フル実行（セットアップ済みなら公開＋告知へ進む）
#   bash go setup      # セットアップのみ（venv＋Playwright インストール）
#   bash go session    # セッション設定のみ
#   bash go note       # note 公開のみ
#   bash go x          # X 投稿のみ

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
AUTO_DIR="$ROOT/projects/2026-04-08_月30万自動化/automation"

CMD="${1:-all}"

case "$CMD" in
  setup)
    bash "$AUTO_DIR/setup.sh"
    ;;
  session)
    bash "$AUTO_DIR/start.sh" setup
    ;;
  note)
    bash "$AUTO_DIR/start.sh" note
    ;;
  x)
    bash "$AUTO_DIR/start.sh" x
    ;;
  all)
    # venv なければセットアップから走る
    if [ ! -d "$AUTO_DIR/.venv" ]; then
      echo "[INFO] venv 未作成。セットアップから実行します。"
      bash "$AUTO_DIR/setup.sh"
    fi
    bash "$AUTO_DIR/start.sh" all
    ;;
  *)
    echo "使い方: bash go [setup|session|note|x|all]"
    exit 1
    ;;
esac
