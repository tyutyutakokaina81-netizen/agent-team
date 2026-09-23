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

VPY="$HOME/.agent_venv/bin/python3"
[ -x "$VPY" ] || VPY="python3"

echo "== 実行 =="
"$VPY" CDO/outputs/note_publisher/set_tags.py "$@" 2>&1 | tee "$LOG"

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
