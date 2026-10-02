#!/bin/bash
# ops/pin_article.sh — 記事をクリエイターページに固定表示する（owner の Mac で実行）
#   cd ~/agent-team-run && bash ops/pin_article.sh na096464584e5        読むだけ
#   cd ~/agent-team-run && bash ops/pin_article.sh na096464584e5 --go   実際に固定する
set -u
cd "$(dirname "$0")/.." 2>/dev/null || exit 1
[ "$#" -lt 1 ] && { echo "usage: bash ops/pin_article.sh <NID> [--go]"; exit 1; }
TS="$(date +%Y-%m-%d_%H%M%S)"; LOG="ops/logs/pin_${TS}.log"; mkdir -p ops/logs
PYBIN=""
for c in "$HOME/.note_venv/bin/python" "$HOME/.note_venv/bin/python3" python3 \
         /opt/homebrew/bin/python3 /usr/local/bin/python3; do
  command -v "$c" >/dev/null 2>&1 || [ -x "$c" ] || continue
  if "$c" -c "import playwright" >/dev/null 2>&1; then PYBIN="$c"; break; fi
done
[ -z "${PYBIN}" ] && { echo "✗ Playwright が入った python が見つかりません。**何もしていません。**"; exit 1; }
set -o pipefail
"${PYBIN}" CDO/outputs/note_publisher/pin_article.py "$@" 2>&1 | tee "${LOG}"
RC=${PIPESTATUS[0]}
echo "ログ: ${LOG}"
exit "${RC:-0}"
