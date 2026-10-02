#!/bin/bash
# ops/unpublish.sh — 公開中の note 記事を下書きに戻す（owner の Mac で実行）
#
#   cd ~/agent-team-run && bash ops/unpublish.sh nc7a3522ade60        読むだけ
#   cd ~/agent-team-run && bash ops/unpublish.sh nc7a3522ade60 --go   実際に下げる
#
# 対象は _note_safety.py の DO_NOT_TOUCH に載っている記事だけ。
set -u
cd "$(dirname "$0")/.." 2>/dev/null || exit 1
[ "$#" -lt 1 ] && { echo "usage: bash ops/unpublish.sh <NID> [--go]"; exit 1; }
TS="$(date +%Y-%m-%d_%H%M%S)"; LOG="ops/logs/unpublish_${TS}.log"; mkdir -p ops/logs
git pull --rebase --autostash || echo "⚠️ git pull に失敗。ローカルのまま続行します"
PYBIN=""
for c in "$HOME/.note_venv/bin/python" "$HOME/.note_venv/bin/python3" python3 \
         /opt/homebrew/bin/python3 /usr/local/bin/python3; do
  command -v "$c" >/dev/null 2>&1 || [ -x "$c" ] || continue
  if "$c" -c "import playwright" >/dev/null 2>&1; then PYBIN="$c"; break; fi
done
[ -z "${PYBIN}" ] && { echo "✗ Playwright が入った python が見つかりません。**何もしていません。**"; exit 1; }
set -o pipefail
"${PYBIN}" CDO/outputs/note_publisher/unpublish_article.py "$@" 2>&1 | tee "${LOG}"
RC=${PIPESTATUS[0]}
git add -A ops/logs CDO/outputs/note_publisher/_before_update 2>/dev/null
git diff --cached --quiet || { git commit -qm "unpublish: 取り下げ ${TS}"; git push -q origin main 2>/dev/null && echo "push しました"; }
echo "ログ: ${LOG}"
exit "${RC:-0}"
