#!/bin/bash
# ops/backfill_follow.sh — 公開済み記事の末尾に **フォロー導線＋あわせて読む3本** を足す
#
#   cd ~/agent-team-run && bash ops/backfill_follow.sh              対象を数えるだけ
#   cd ~/agent-team-run && bash ops/backfill_follow.sh --go         既定 8本ずつ
#   cd ~/agent-team-run && bash ops/backfill_follow.sh --go --limit 20
#
# なぜ（2026-10-02）: 公開210本のうち他記事へのリンクがあるのは10本(4%)、
#   フォローの一言があるのは7本(3%)。読んだ人が次へ行く道も、フォローする理由も無かった。
#
# 安全: 本文は置換しない（末尾に足すだけ＝写真が消えない）。すでに導線がある記事は触らない。
#       押すのは「更新する」だけ。1本ずつ記録するので途中で止めて再開できる。
set -u
cd "$(dirname "$0")/.." 2>/dev/null || exit 1
GO=""; LIMIT=8; NOGIT=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --go) GO="--go" ;;
    --limit) shift; LIMIT="${1:-8}" ;;
    --nogit) NOGIT="1" ;;
  esac
  shift
done
TS="$(date +%Y-%m-%d_%H%M%S)"; LOG="ops/logs/backfill_follow_${TS}.log"; mkdir -p ops/logs
DONE="ops/follow_backfill_done.tsv"
[ -f "$DONE" ] || printf '# NID\t結果\t日時\n' > "$DONE"

if [ -z "${NOGIT}" ]; then
  git pull --rebase --autostash || echo "⚠️ git pull に失敗。ローカルのまま続行します"
fi
python3 ops/build_follow_blocks.py | tail -3

PENDING=$(python3 - <<'PY'
import os
done=set()
if os.path.exists("ops/follow_backfill_done.tsv"):
    for l in open("ops/follow_backfill_done.tsv",encoding="utf-8"):
        c=l.rstrip("\n").split("\t")
        if len(c)>=2 and c[1] in ("UPDATED","SKIP"): done.add(c[0])
rows=[l.split("\t")[0] for l in open("ops/follow_blocks.tsv",encoding="utf-8")
      if l.strip() and not l.startswith("#")]
print(len([r for r in rows if r not in done]))
PY
)
echo "まだ導線を入れていない記事: ${PENDING}本"

if [ -z "$GO" ]; then
  echo ""
  echo "DRY-RUN: 何も変更していません。実行するなら --go を付けてください"
  exit 0
fi

PYBIN=""
for c in "$HOME/.note_venv/bin/python" "$HOME/.note_venv/bin/python3" python3 \
         /opt/homebrew/bin/python3 /usr/local/bin/python3; do
  command -v "$c" >/dev/null 2>&1 || [ -x "$c" ] || continue
  if "$c" -c "import playwright" >/dev/null 2>&1; then PYBIN="$c"; break; fi
done
[ -z "${PYBIN}" ] && { echo "✗ Playwright が入った python が見つかりません。**何もしていません。**"; exit 1; }

OK=0; SKIP=0; NG=0; N=0
while IFS=$'\t' read -r NID STEM BLK; do
  case "$NID" in ""|\#*) continue ;; esac
  grep -q "^${NID}	\(UPDATED\|SKIP\)	" "$DONE" && continue
  [ "$N" -ge "$LIMIT" ] && break
  N=$((N + 1))
  echo ""
  echo "---- [${N}/${LIMIT}] ${NID}  ${STEM:0:44}"
  OUT="$("${PYBIN}" CDO/outputs/note_publisher/append_follow_footer.py "$NID" --go 2>&1)"
  echo "$OUT" >> "${LOG}"
  echo "$OUT" | tail -2
  if echo "$OUT" | grep -q "SKIP_HAS_FOOTER"; then R="SKIP"; SKIP=$((SKIP+1))
  elif echo "$OUT" | grep -q "^結果: UPDATED"; then R="UPDATED"; OK=$((OK+1))
  else R="FAILED"; NG=$((NG+1)); fi
  printf '%s\t%s\t%s\n' "$NID" "$R" "$(date +%F_%H%M%S)" >> "$DONE"
done < ops/follow_blocks.tsv

echo ""
echo "== 結果: 追記 ${OK}本 / すでにある ${SKIP}本 / 失敗 ${NG}本 =="
if [ -n "${NOGIT}" ]; then echo "ログ: ${LOG}"; exit 0; fi
git add -A ops/follow_backfill_done.tsv ops/logs CDO/outputs/note_publisher/_before_update 2>/dev/null
if ! git diff --cached --quiet; then
  git commit -qm "update: 公開済み記事にフォロー導線を追記 ${TS}（追記${OK}/SKIP${SKIP}/失敗${NG}）"
  for i in 1 2 3; do
    git push -q origin main && { echo "push 成功"; break; }
    git pull --rebase -q origin main || true; sleep $((i*2))
  done
fi
echo "ログ: ${LOG}"
