#!/bin/zsh
# AI自動収益化パイプライン日次ランナー
# - cron / launchd から呼び出すメイン実行ファイル
# - 個別失敗があってもプロセスは止めない（generate_daily_outputs.py 側で吸収）
# - 終了コードは「全件成功=0／いずれか失敗=1」
set -u

SCRIPT_DIR="${0:A:h}"
PROJECT_DIR="${SCRIPT_DIR:h}"
cd "${PROJECT_DIR}"

mkdir -p logs outputs

LOG="logs/run.log"
echo "===== RUN $(date -Iseconds) =====" >> "${LOG}"

# Python が見つからない環境でも壊れないようにフォールバック
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "$(date -Iseconds) ERROR python not found" >> "${LOG}"
  exit 127
fi

"${PY}" "${SCRIPT_DIR}/generate_daily_outputs.py"
RC=$?

echo "$(date -Iseconds) exit=${RC}" >> "${LOG}"
exit "${RC}"
