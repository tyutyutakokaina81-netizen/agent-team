#!/bin/bash
# ops/fix_header_images.sh — 【B】見出し画像なしで公開された記事に画像を付ける（owner の Mac で実行）
#
#   bash ops/fix_header_images.sh            # ①実測(変更なし) → ②実際に設定して更新
#   bash ops/fix_header_images.sh --probe    # ①実測だけ。何も変更しない
#   bash ops/fix_header_images.sh --only n242960f609cf   # 1本だけ試す
#
# code(Claude Code) は A1 で note を開けない。この結果（ボタン一覧・HTML）が push されて初めて
# publisher のセレクタを直せる。だから成功しても失敗しても必ずログを push する。
set -u
cd "$(dirname "$0")/.." || exit 1
REPO="$(pwd)"
TS="$(date +%Y-%m-%d_%H%M%S)"
LOG="ops/logs/header_fix_${TS}.log"
mkdir -p ops/logs

echo "== 最新を取得 =="
# --autostash: ログが未コミットのままでも pull が止まらない（2026-09-16 にこれで詰まった）
git pull --rebase --autostash || echo "⚠️ git pull に失敗。ローカルのまま続行します"

PROBE_ONLY=0
EXTRA=()
# 2026-09-19: 貼り付けたコマンドの末尾に `]` が混ざり、run_x.sh で引数が一致せず
# **黙って別の動作に流れた**。ここでも末尾の余計な記号を落としてから判定する。
# set -u 下でも空配列を安全に数えられるようにしておく
for a in "$@"; do
  a="$(printf '%s' "$a" | sed -e 's/[^A-Za-z0-9_-]*$//')"
  case "$a" in
    --probe) PROBE_ONLY=1 ;;
    *) EXTRA+=("$a") ;;
  esac
done

{
  echo "### 見出し画像の修復 ${TS}"
  echo "--- 手順1: 今のUIを実測（変更しない・1本だけ） ---"
  # 2026-09-19: 7本ぜんぶ実測すると出力が膨大なうえ、どれも同じ画面なので意味がない。
  # **1本だけ**見て、公開設定画面とエディタ画面のHTML・スクリーンショットを保存する。
  FIRST="$(grep -m1 '^n' ops/header_image_todo.tsv 2>/dev/null | cut -f1)"
  if [ -n "$FIRST" ] && [ ${#EXTRA[@]} -eq 0 ]; then
    python3 CDO/outputs/note_publisher/set_header_image.py --probe --only "$FIRST"
  else
    python3 CDO/outputs/note_publisher/set_header_image.py --probe ${EXTRA[@]+"${EXTRA[@]}"}
  fi
  if [ "$PROBE_ONLY" -eq 0 ]; then
    echo
    echo "--- 手順2: 見出し画像を設定して更新 ---"
    python3 CDO/outputs/note_publisher/set_header_image.py ${EXTRA[@]+"${EXTRA[@]}"}
  else
    echo "（--probe のため手順2はやりません）"
  fi
} 2>&1 | tee "$LOG"

echo
echo "== 結果を code に渡す（commit & push）=="
git add -A ops/logs ops/header_image_todo.tsv 2>/dev/null
if git diff --cached --quiet; then
  echo "（変更なし）"
else
  git commit -q -m "owner: 見出し画像の修復ログ ${TS}" && echo "commit した"
  BR="$(git rev-parse --abbrev-ref HEAD)"
  # detached HEAD のまま push すると "not a full refname" で4回とも失敗する（2026-09-19 実測）。
  if [ "$BR" = "HEAD" ]; then
    echo "⚠️ ブランチから外れているので push しません。git switch main で戻してから、もう一度実行してください。"
  else
    for i in 1 2 3 4; do
      git push -u origin "$BR" && break
      echo "push 失敗、$((2**i))秒待って再試行"; sleep $((2**i))
    done
  fi
fi
echo
echo "ログ: ${REPO}/${LOG}"
echo "→ この内容を Claude に貼ると、publisher のセレクタを直せます。"
