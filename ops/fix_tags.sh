#!/bin/bash
# ops/fix_tags.sh — 【D】タグ0個のまま公開された記事に、後からハッシュタグを付ける（owner の Mac で実行）
#
#   cd ~/agent-team-run && bash ops/fix_tags.sh --probe   # まず実測。何も変更しない
#   cd ~/agent-team-run && bash ops/fix_tags.sh           # 実際に付けて更新する
#   cd ~/agent-team-run && bash ops/fix_tags.sh --max 5   # 5本で止める（様子見）
#
# なぜ必要か（2026-09-23）:
#   公開済み196本のうち **39本がタグ0個**で出ていた（2026-08-25〜09-18）。
#   publisher は記事に `## ハッシュタグ` ブロックが無いと黙って0個で公開する仕様で、
#   その時期の記事にブロックが無かった。note ではタグがタグページ・おすすめ経由の
#   主要な発見経路なので、**タグ0個は露出が構造的に落ちる**。
#   見出し画像と同じく、公開後でも後から付けられる。
#
# code は A1 で note を開けないので、結果（成否とログ）が push されて初めて診断できる。
# だから成功しても失敗しても必ずログを push する。
set -u
cd "$(dirname "$0")/.." || exit 1
TS="$(date +%Y-%m-%d_%H%M%S)"
LOG="ops/logs/tag_fix_${TS}.log"
mkdir -p ops/logs

echo "== 最新を取得 =="
git pull --rebase --autostash || echo "⚠️ git pull に失敗。ローカルのまま続行します"

REMAIN="$(grep -vc '^#\|^DONE\|^$' ops/tag_backfill_todo.tsv 2>/dev/null || echo 0)"
echo "== 未処理: ${REMAIN} 本 =="
if [ "${REMAIN}" = "0" ]; then
  echo "対象がありません（全部 DONE）。終了します。"
  exit 0
fi

# ★2026-09-23: 最初 `$HOME/.agent_venv` を決め打ちにしていたが、**あれは X 用(tweepy)の環境で
#   Playwright は入っていない**。run_x.sh から選び方をそのままコピーしたのが原因で、
#   3回叩いて3回とも「Playwright未インストール」で何もせず終わった。
#   決め打ちをやめ、**実際に playwright を import できる python を探す**。
PYBIN=""
#   2026-09-23 実測: owner の Mac では setup.sh が `$HOME/.note_venv` を作っており、
#   中の実体は `python`（python3 ではない）。候補に両方入れる。
for c in "$HOME/.note_venv/bin/python" "$HOME/.note_venv/bin/python3" python3 \
         /opt/homebrew/bin/python3 /usr/local/bin/python3 "$HOME/.agent_venv/bin/python3"; do
  command -v "$c" >/dev/null 2>&1 || [ -x "$c" ] || continue
  if "$c" -c "import playwright" >/dev/null 2>&1; then PYBIN="$c"; break; fi
done
if [ -z "$PYBIN" ]; then
  echo "✗ Playwright が入った python が見つかりません。**何もしていません。**"
  echo "  先にこれを実行してください:"
  echo "      cd ~/agent-team-run && bash CDO/outputs/note_publisher/setup.sh"
  echo "  （見出し画像の修復 ops/fix_header_images.sh と同じ環境を使います）"
  exit 1
fi
echo "== 実行（python: ${PYBIN}）=="
set -o pipefail
"$PYBIN" CDO/outputs/note_publisher/set_tags.py "$@" 2>&1 | tee "$LOG"
RC=$?
if [ "$RC" -ne 0 ]; then
  echo ""
  echo "✗ 途中で失敗しました（終了コード ${RC}）。上のログを見てください。"
fi

echo ""
echo "== 結果を code に渡す（commit & push）=="
git add -A ops/logs ops/tag_backfill_todo.tsv 2>/dev/null
if git diff --cached --quiet; then
  echo "（変更なし）"
else
  git commit -qm "tags: 公開済み記事へのタグ付与 ${TS}"
  for i in 1 2 3 4; do
    git push -q origin main && { echo "push 成功"; break; }
    echo "push 失敗（${i}回目）→ 取得し直して再試行"
    git pull --rebase -q origin main
    sleep $((2 ** i))
  done
fi
echo "ログ: ${LOG}"
exit "${RC:-0}"
