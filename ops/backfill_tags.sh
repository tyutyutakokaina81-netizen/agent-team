#!/bin/bash
# ops/backfill_tags.sh — 公開済み記事に **#毎日note** を足す（owner の Mac／朝の便で実行）
#
#   cd ~/agent-team-run && bash ops/backfill_tags.sh            対象を数えるだけ
#   cd ~/agent-team-run && bash ops/backfill_tags.sh --go       既定 6本ずつ
#
# なぜ（2026-10-02 に数えて分かったこと）:
#   公開207本のタグを集計したら **#毎日note が0本**だった。
#   note でいちばん大きいタグ面のひとつで、しかも**一日2本・231本公開という事実に合っている**。
#   タグページは note の主要な発見経路なので、ここに載らないのは取りこぼし。
#   ※ 中身に合わないタグは付けない。合うものだけを足す（#今日の学び などは付けない）。
set -u
cd "$(dirname "$0")/.." 2>/dev/null || exit 1
GO=""; LIMIT=6; NOGIT=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --go) GO="--go" ;;
    --limit) shift; LIMIT="${1:-6}" ;;
    --nogit) NOGIT="1" ;;
  esac
  shift
done
TS="$(date +%Y-%m-%d_%H%M%S)"; LOG="ops/logs/backfill_tags_${TS}.log"; mkdir -p ops/logs
LEFT=$(grep -vc '^\(#\|DONE\)' ops/tag_mainichi_todo.tsv 2>/dev/null || echo 0)
echo "#毎日note をまだ足していない公開記事: ${LEFT}本"
if [ -z "$GO" ]; then
  echo ""; echo "DRY-RUN: 何も変更していません。実行するなら --go を付けてください"; exit 0
fi
PYBIN=""
for c in "$HOME/.note_venv/bin/python" "$HOME/.note_venv/bin/python3" python3 \
         /opt/homebrew/bin/python3 /usr/local/bin/python3; do
  command -v "$c" >/dev/null 2>&1 || [ -x "$c" ] || continue
  if "$c" -c "import playwright" >/dev/null 2>&1; then PYBIN="$c"; break; fi
done
[ -z "${PYBIN}" ] && { echo "✗ Playwright が入った python が見つかりません。**何もしていません。**"; exit 1; }
set -o pipefail
"${PYBIN}" CDO/outputs/note_publisher/set_tags.py --todo ops/tag_mainichi_todo.tsv --max "$LIMIT" 2>&1 | tee "${LOG}" | tail -12
[ -n "${NOGIT}" ] && { echo "ログ: ${LOG}"; exit 0; }
git add -A ops/tag_mainichi_todo.tsv ops/logs 2>/dev/null
git diff --cached --quiet || {
  git commit -qm "tags: #毎日note を公開済み記事に追記 ${TS}"
  for i in 1 2 3; do git push -q origin main && break; git pull --rebase -q origin main || true; sleep $((i*2)); done
}
echo "ログ: ${LOG}"
