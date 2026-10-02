#!/bin/bash
# ops/backfill_english.sh — 公開済み記事の **末尾に英語要約を足す**（owner の Mac で実行）
#
#   cd ~/agent-team-run && bash ops/backfill_english.sh              # 対象を数えるだけ
#   cd ~/agent-team-run && bash ops/backfill_english.sh --go         # 既定 10本ずつ
#   cd ~/agent-team-run && bash ops/backfill_english.sh --go --limit 30
#
# なぜ必要か（2026-09-30）:
#   publisher は「## 本文」直下の ``` ブロックだけを note に貼る。英語要約はブロックの外に
#   書いていたので、md には英語があるのに **note 上は日本語だけ**で公開されていた。
#   North Star は「海外読者に読まれる」。書いた英語がそのまま捨てられていた。
#   md は ops/inline_english.py で直した。ここは **すでに公開した分の note 側**を直す。
#
# 安全:
#   - 本文は置換しない。**末尾に足すだけ**（写真・見出し画像・タイトル・タグは触らない）。
#   - すでに英文がある記事は開いても SKIP して何もしない。
#   - 押すのは「更新する」だけ。下書きなら押さずに止まる。
#   - 1本ずつ ops/english_backfill_done.tsv に記録するので、途中で止めて再開できる。
set -u
cd "$(dirname "$0")/.." 2>/dev/null || exit 1
GO=""; LIMIT=10; NOGIT=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --go) GO="--go" ;;
    --limit) shift; LIMIT="${1:-10}" ;;
    --nogit) NOGIT="1" ;;   # go.sh の中から呼ぶとき（git は go.sh 側が面倒を見る）
  esac
  shift
done
TS="$(date +%Y-%m-%d_%H%M%S)"
LOG="ops/logs/backfill_english_${TS}.log"
mkdir -p ops/logs

if [ -z "${NOGIT}" ]; then
  echo "== 最新を取得 =="
  git pull --rebase --autostash || echo "⚠️ git pull に失敗。ローカルのまま続行します"
fi

python3 ops/build_english_todo.py || exit 1
TODO="ops/english_backfill_todo.tsv"
DONE="ops/english_backfill_done.tsv"
[ -f "$DONE" ] || echo "# NID	結果	日時	タイトル" > "$DONE"

if [ -z "$GO" ]; then
  echo ""
  echo "DRY-RUN: 何も変更していません。実行するなら --go を付けてください"
  echo "  cd ~/agent-team-run && bash ops/backfill_english.sh --go --limit ${LIMIT}"
  exit 0
fi

PYBIN=""
for c in "$HOME/.note_venv/bin/python" "$HOME/.note_venv/bin/python3" python3 \
         /opt/homebrew/bin/python3 /usr/local/bin/python3 "$HOME/.agent_venv/bin/python3"; do
  command -v "$c" >/dev/null 2>&1 || [ -x "$c" ] || continue
  if "$c" -c "import playwright" >/dev/null 2>&1; then PYBIN="$c"; break; fi
done
if [ -z "${PYBIN}" ]; then
  echo "✗ Playwright が入った python が見つかりません。**何もしていません。**"
  echo "      cd ~/agent-team-run && bash CDO/outputs/note_publisher/setup.sh"
  exit 1
fi

OK=0; SKIP=0; NG=0; N=0
while IFS=$'\t' read -r NID MD TITLE; do
  case "$NID" in ""|\#*) continue ;; esac
  [ "$N" -ge "$LIMIT" ] && break
  N=$((N + 1))
  echo ""
  echo "---- [${N}/${LIMIT}] ${NID}  ${TITLE}"
  OUT="$("${PYBIN}" CDO/outputs/note_publisher/append_english.py "$NID" "$MD" --go 2>&1)"
  echo "$OUT" | tee -a "${LOG}" >/dev/null
  echo "$OUT" | tail -3
  if echo "$OUT" | grep -q "SKIP_HAS_ENGLISH"; then
    R="SKIP"; SKIP=$((SKIP + 1))
  elif echo "$OUT" | grep -q "^結果: UPDATED"; then
    R="UPDATED"; OK=$((OK + 1))
  else
    R="FAILED"; NG=$((NG + 1))
  fi
  printf '%s\t%s\t%s\t%s\n' "$NID" "$R" "$(date +%F_%H%M%S)" "$TITLE" >> "$DONE"
done < "$TODO"

echo ""
echo "== 結果: 追記 ${OK}本 / すでに英語あり ${SKIP}本 / 失敗 ${NG}本 =="
# ★2026-10-02: todo は実行の**最初**に作るので、go.sh の 5) が**実行前の数**を「残り」として
#   表示していた（8本処理したのに 70本のまま）。終わったら作り直して、残りを本当の数にする。
python3 ops/build_english_todo.py >/dev/null 2>&1 || true
if [ -n "${NOGIT}" ]; then echo "ログ: ${LOG}"; exit 0; fi
echo "== code に渡す（commit & push）=="
git add -A ops/english_backfill_done.tsv ops/logs CDO/outputs/note_publisher/_before_update 2>/dev/null
if git diff --cached --quiet; then
  echo "（変更なし）"
else
  git commit -qm "update: 公開済み記事の末尾に英語要約を追記 ${TS}（追記${OK}/SKIP${SKIP}/失敗${NG}）"
  for i in 1 2 3 4; do
    git push -q origin main && { echo "push 成功"; break; }
    echo "push 失敗（${i}回目）→ 取得し直して再試行"
    git pull --rebase -q origin main
    sleep $((2 ** i))
  done
fi
echo "ログ: ${LOG}"
