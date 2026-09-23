#!/bin/bash
# ops/start_here.sh — オーナーが Mac で最初に叩く1本。
#   cd ~/agent-team-run 2>/dev/null || cd ~/agent-team && bash ops/start_here.sh
#
# やること（上から順に、止まらないように）:
#   0) git の残骸（*.lock）を片付ける ※動いている git が無いときだけ
#   1) 未コミットの変更を退避コミット（消さない）
#   2) 最新を取得
#   3) 自動でできる作業（コメント巡回など）を実行 → 結果を push
#   4) 人にしかできない作業を、そのとき数えた実数で一覧表示
#
# 単体で実行しても安全。途中で失敗しても次へ進む（原因は画面に出る）。
set -u
cd "$(dirname "$0")/.." || exit 1

echo "==================== 0) git の残骸を確認 ===================="
# ★2026-09-25: `pgrep -f "git "` は**コマンドライン全体に "git " を含むだけ**の
#   無関係なプロセスにも当たる（実測: git を一度も呼んでいない bash に当たった）。
#   見たいのは「git が走っているか」なので、プロセス名で厳密に一致させる。
# ★2026-09-25 修正: 「git が動いていたら即 exit」だったが、`git pull` の直後は macOS の git が
#   **自動メンテナンス(gc --auto)** をバックグラウンドで走らせるため、
#   **いちばん実行したいタイミングで必ず弾かれる**（実測: pull 直後に git が9個走っていて止まった）。
#   ガード本来の目的は「生きている git の下でロックファイルを消さない」ことなので、
#   **止めるのはロック削除だけ**にして、あとは進める。
GIT_BUSY=0
for _i in 1 2 3 4 5 6; do
  pgrep -x git >/dev/null 2>&1 || { GIT_BUSY=0; break; }
  GIT_BUSY=1
  echo "git が動いています（自動メンテナンスの可能性）。${_i}/6 回目・10秒待ちます…"
  sleep 10
done
if [ "${GIT_BUSY}" = "1" ] && pgrep -x git >/dev/null 2>&1; then
  echo "まだ動いています。**ロックファイルの掃除だけ飛ばして**先に進みます:"
  pgrep -lx git
else
  LOCKS="$(find .git -maxdepth 3 -name '*.lock*' 2>/dev/null)"
  if [ -n "${LOCKS}" ]; then
    echo "残骸を見つけたので消します（ロックファイルだけ。コミットや作業ファイルには触れません）:"
    echo "${LOCKS}"
    find .git -maxdepth 3 -name '*.lock*' -delete
  else
    echo "残骸なし"
  fi
fi

echo ""
echo "==================== 0b) 中断した rebase / merge が無いか ===================="
# ★2026-09-19 の事故: rebase が衝突で中断している最中に `git add -A && git commit` したため、
# **コンフリクト記号(<<<<<<< >>>>>>>)が入ったままのファイルをコミット**してしまい、
# python が SyntaxError で全部落ち、さらに detached HEAD になって push も通らなくなった。
# **中断中は絶対に自動コミットしない。** ここで止めて、人に判断してもらう。
if [ -d .git/rebase-merge ] || [ -d .git/rebase-apply ] || [ -f .git/MERGE_HEAD ]; then
  echo "★ rebase / merge が中断したままです。**自動では触りません**（無理に進めると壊れます）。"
  echo "   いまの状態:"
  git status --short | head -20
  echo ""
  echo "   この画面を Claude に貼ってください。復旧手順を出します。"
  echo "   （自分で戻すなら: git rebase --abort  もしくは  git merge --abort）"
  exit 1
fi
BR="$(git rev-parse --abbrev-ref HEAD)"
if [ "$BR" = "HEAD" ]; then
  echo "★ ブランチから外れています（detached HEAD）。**自動では触りません**。"
  echo "   この画面を Claude に貼ってください。（自分で戻すなら: git switch main）"
  exit 1
fi
echo "ブランチ: $BR ／ 中断した rebase・merge はありません"

echo ""
echo "==================== 1) 未コミットの変更を退避 ===================="
git status --short
git add -A
git commit -q -m "mac: 実行前の未コミット分を退避 $(date +%Y-%m-%d_%H%M)" && echo "退避コミットしました" \
  || echo "（コミットするものはありません）"

echo ""
echo "==================== 2) 最新を取得 ===================="
git pull --rebase --autostash || echo "⚠️ 取得に失敗しました。上のメッセージを Claude に貼ってください。"

echo ""
echo "==================== 3) 自動でできる作業 ===================="
bash ops/owner_tasks.sh
