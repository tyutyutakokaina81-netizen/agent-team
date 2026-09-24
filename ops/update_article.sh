#!/bin/bash
# ops/update_article.sh — 【F】書き直した記事で**公開済みの note 記事を差し替える**（owner の Mac で実行）
#
#   cd ~/agent-team-run && bash ops/update_article.sh <NID> <記事md>         # まず実測。何も変えない
#   cd ~/agent-team-run && bash ops/update_article.sh <NID> <記事md> --go    # 実際に差し替える
#
# なぜ必要か（2026-09-24）:
#   記事を書き直しても、**出す方法が無かった**。タイトルだけ直す道具はあり、
#   publish_to_note.py は新規投稿しかできない。書き直しを新規で出すと
#   **同じ題材が2本**になる（2026-07-04 の氷見牛と同じ事故）。だから「更新」の口を作った。
#
# 安全のために:
#   - 押すのは「更新する」だけ。「投稿する」しか無い＝下書きのときは押さずに止まる。
#   - 差し替える前の本文を CDO/outputs/note_publisher/_before_update/<NID>.txt に保存する。
#   - 本文中の [写真X] は入れない（画像の再挿入は別作業）。
#   - 有料記事の md は受け付けない。
set -u
cd "$(dirname "$0")/.." 2>/dev/null || exit 1
if [ "$#" -lt 2 ]; then
  echo "usage: bash ops/update_article.sh <NID> <記事md> [--go]"
  exit 1
fi
TS="$(date +%Y-%m-%d_%H%M%S)"
LOG="ops/logs/update_article_${TS}.log"
mkdir -p ops/logs

echo "== 最新を取得 =="
git pull --rebase --autostash || echo "⚠️ git pull に失敗。ローカルのまま続行します"

# playwright を import できる python を探す（決め打ちにすると外れる＝fix_magazines.sh と同じ理由）
PYBIN=""
for c in "$HOME/.note_venv/bin/python" "$HOME/.note_venv/bin/python3" python3 \
         /opt/homebrew/bin/python3 /usr/local/bin/python3 "$HOME/.agent_venv/bin/python3"; do
  command -v "$c" >/dev/null 2>&1 || [ -x "$c" ] || continue
  if "$c" -c "import playwright" >/dev/null 2>&1; then PYBIN="$c"; break; fi
done
if [ -z "${PYBIN}" ]; then
  echo "✗ Playwright が入った python が見つかりません。**何もしていません。**"
  echo "  先にこれを実行してください:"
  echo "      cd ~/agent-team-run && bash CDO/outputs/note_publisher/setup.sh"
  exit 1
fi

echo "== 実行（python: ${PYBIN}）=="
set -o pipefail
"${PYBIN}" CDO/outputs/note_publisher/update_article.py "$@" 2>&1 | tee "${LOG}"
RC=$?
if [ "${RC}" -ne 0 ]; then
  echo ""
  echo "✗ 差し替えは完了していません（終了コード ${RC}）。上のログを見てください。"
fi

echo ""
echo "== 結果を code に渡す（commit & push）=="
git add -A ops/logs CDO/outputs/note_publisher/_before_update 2>/dev/null
if git diff --cached --quiet; then
  echo "（変更なし）"
else
  git commit -qm "update: 公開済み記事の差し替え ${TS}"
  for i in 1 2 3 4; do
    git push -q origin main && { echo "push 成功"; break; }
    echo "push 失敗（${i}回目）→ 取得し直して再試行"
    git pull --rebase -q origin main
    sleep $((2 ** i))
  done
fi
echo "ログ: ${LOG}"
exit "${RC:-0}"
