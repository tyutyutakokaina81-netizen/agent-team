#!/bin/bash
# ops/go.sh — オーナーが Mac で叩く1本。これだけで通る。
#
#   cd ~/agent-team-run 2>/dev/null || cd ~/agent-team && bash ops/go.sh
#
# ★`bash: ops/go.sh: No such file or directory` と出たら、**リポジトリの外にいる**。
#   go.sh はリポジトリの中のファイルなので、ホームからは見えない（2026-09-23 に3度目）。
#   毎回 cd を書くのが面倒なら、**1回だけ**これを実行しておくと `go` だけで通る:
#     echo 'alias go="cd ~/agent-team-run 2>/dev/null || cd ~/agent-team; bash ops/go.sh"' >> ~/.zshrc
#     source ~/.zshrc
#   ※クローン先が `~/agent-team-run` と `~/agent-team` のどちらでも通るようにしてある。
#     ドキュメント側が長く `~/agent-team` と書いていたが、ワーカーが使っているのは
#     `~/agent-team-run` で、**書いてある通りに打つと cd から失敗していた**。
#
# ★先に `git pull` を付けないこと（2026-09-22）。
#   手元に未コミットの変更があると `git pull` は
#   「cannot pull with rebase: You have unstaged changes」で失敗し、
#   **それを処理できる go.sh まで到達しない**。
#   go.sh は 1) で退避コミット → pull --rebase --autostash までやるので、pull は不要。
#
# やること（上から順に。途中で止まっても、どこで止まったか画面に出る）:
#   0) 安全確認（git の残骸・中断した rebase/merge・detached HEAD）
#   1) 手元の変更を退避コミットして push  ★publish が main を巻き戻すので、先に逃がす
#   2) 最新を取得
#   3) **公開**（drafts/queue の記事を note へ）
#   4) X を1本（APIキー不要・文面を出してクリップボードへ）
#   5) 残っている作業を、そのとき数えた実数で表示
#
# 引数:
#   （なし）  本日分を公開して X を1本
#   --all     キューにある分を全部公開する
#   --login   先に note ログインしてから公開する（初回・セッション切れ時）
#   --no-x    X を飛ばす（公開だけしたいとき）
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

ARG_RAW="${1:-}"
ARG="$(printf '%s' "${ARG_RAW}" | sed -e 's/[^A-Za-z-]*$//')"
if [ -n "${ARG_RAW}" ] && [ "${ARG}" != "${ARG_RAW}" ]; then
  echo "（引数に余計な文字が付いていました: '${ARG_RAW}' → '${ARG}' として扱います）"
fi
case "${ARG}" in
  ""|--all|--login|--no-x) : ;;
  *) echo "✗ 知らない引数です: '${ARG_RAW}'"
     echo "   使えるのは:  （なし） / --all / --login / --no-x"
     exit 1 ;;
esac

echo "==================== 0) 安全確認 ===================="
# ★2026-09-25 修正: ここは「git が動いていたら即 exit」だった。
#   ところが `git pull` の直後は macOS の git が **自動メンテナンス(gc --auto)** を
#   バックグラウンドで走らせるため、**いちばん実行したいタイミングで必ず弾かれる**
#   （実測: pull 直後に git が9個走っていて止まった）。
#   ガード本来の目的は「生きている git の下でロックファイルを消さない」ことなので、
#   **止めるのはロック削除だけ**にして、あとは進める。少し待てば大抵は終わる。
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
    echo "git の残骸を消します（ロックファイルだけ。コミットや作業ファイルには触れません）:"
    echo "${LOCKS}"
    find .git -maxdepth 3 -name '*.lock*' -delete
  else
    echo "残骸なし"
  fi
fi
# ★2026-09-19 の事故: rebase が衝突で止まっている最中に自動コミットして、
#   コンフリクト記号ごと .py をコミットし、python が全部 SyntaxError になった。
#   中断中は絶対に自動コミットしない。ここで止めて人に判断してもらう。
if [ -d .git/rebase-merge ] || [ -d .git/rebase-apply ] || [ -f .git/MERGE_HEAD ]; then
  echo "★ rebase / merge が中断したままです。**自動では触りません**。"
  git status --short | head -20
  echo "   この画面を Claude に貼ってください。（自分で戻すなら: git rebase --abort）"
  exit 1
fi
BR="$(git rev-parse --abbrev-ref HEAD)"
if [ "${BR}" = "HEAD" ]; then
  echo "★ ブランチから外れています（detached HEAD）。**自動では触りません**。"
  echo "   この画面を Claude に貼ってください。（自分で戻すなら: git switch main）"
  exit 1
fi
echo "ブランチ: ${BR}"

echo ""
echo "==================== 1) 手元の変更を退避して push ===================="
# ★ここが要点。次の publish が `git checkout -B main origin/main` で main を巻き戻すので、
#   **push していない手元の変更は消える**。先に逃がしてから公開に進む。
git status --short
if [ -n "$(git status --porcelain)" ]; then
  git add -A
  git commit -q -m "mac: 実行前の未コミット分を退避 $(date +%Y-%m-%d_%H%M)" && echo "退避コミットしました"
else
  echo "（コミットするものはありません）"
fi
git pull --rebase --autostash origin main || {
  echo "⚠️ 取得に失敗しました。この画面を Claude に貼ってください。"; exit 1; }
if ! git push origin HEAD:main; then
  echo "⚠️ push に失敗しました。**ここで止めます**（このまま公開すると退避分が消えます）。"
  echo "   この画面を Claude に貼ってください。"
  exit 1
fi

echo ""
echo "==================== 2) 公開 ===================="
PUBARGS=""
[ "${ARG}" = "--all" ]   && PUBARGS="--all"
[ "${ARG}" = "--login" ] && PUBARGS="--login"
# ★2026-09-25: 5) で `ls -t ops/logs/publish_*.log` から拾っていたが、**この実行とは別の
#   ログ（日次デーモンの publish_2026-09-21_080005.log）を掴んで、無関係な行を表示した**。
#   「今回の結果」を名乗るなら、今回の出力そのものを見るしかない。
GO_LOG="ops/logs/go_$(date +%Y-%m-%d_%H%M%S).log"
mkdir -p ops/logs
bash ops/publish_today.sh ${PUBARGS} 2>&1 | tee "${GO_LOG}"
PUB_RC=${PIPESTATUS[0]}
echo "(公開の終了コード: ${PUB_RC})"

echo ""
echo "==================== 3) X（APIキー不要） ===================="
if [ "${ARG}" = "--no-x" ]; then
  echo "（--no-x が指定されたので飛ばします）"
else
  bash ops/run_x.sh --manual
fi

echo ""
echo "==================== 4) 結果を push ===================="
git add -A
git commit -q -m "mac: go.sh 実行結果 $(date +%Y-%m-%d_%H%M)" && echo "コミットしました" \
  || echo "（コミットするものはありません）"
for i in 1 2 3 4; do
  git push origin HEAD:main && { echo "push しました"; break; }
  echo "push 失敗（${i}回目）→ 取得し直して再試行"
  git pull --rebase --autostash origin main || true
  sleep $((i*2))
done

echo ""
echo "==================== 5) 残っている作業 ===================="
# 件数はハードコードしない。**手で書いた数字は必ず古くなる。**
QUEUE_LEFT=$(ls drafts/queue/*.md 2>/dev/null | wc -l | tr -d ' ')
# ★2026-09-25: `$([ -f f ] && grep -c . f || echo 0)` は **ファイルが在って0行のとき
#   grep が「0」を出したうえで終了コード1を返すので、|| echo 0 も走って「0\n0」になる**。
#   実際に画面が "X の投稿実績 : 0 / 0 件" と2行に割れた。数え方は1本道にする。
if [ -f ops/logs/x_posted.tsv ]; then
  X_POSTED=$(grep -c . ops/logs/x_posted.tsv 2>/dev/null)
  [ -z "${X_POSTED}" ] && X_POSTED=0
else
  X_POSTED=0
fi
X_PENDING=$(grep -c '^=== ' ops/x_queue.txt 2>/dev/null)
[ -z "${X_PENDING}" ] && X_PENDING="?"
echo "公開キューの残り : ${QUEUE_LEFT} 本"
echo "X の投稿実績     : ${X_POSTED} 件 ／ 未投稿スレッド ${X_PENDING} 本"
if [ -f "${GO_LOG}" ]; then
  echo ""
  echo "今回の公開結果（${GO_LOG}）:"
  grep -E "^=== 結果:|最終URL|✗ 重複ゲート|この記事は公開できませんでした" "${GO_LOG}" | tail -15
fi
cat <<'MANUAL'

----------------------------------------------------------
 ブラウザでしかできない作業（code は note を開けません・A1）
----------------------------------------------------------
 [1] 誤サムネの差し替え（公開済み・優先「高」11本）
     一覧と理由: CQO/research/2026-09-19_サムネ目視スイープ.md
     note の記事編集 → 見出し画像を削除すれば note 既定に戻ります。
     （誤サムネより無サムネが正・A5）

 [2] X をもう1本出すとき:   bash ops/run_x.sh --manual
     間違えて「投稿した」と答えたとき: bash ops/run_x.sh --undo

 次回も、これ1本だけで通ります（**git pull は付けないこと**）:
     cd ~/agent-team-run 2>/dev/null || cd ~/agent-team && bash ops/go.sh

 この画面をそのまま Claude に貼れば、続きをこちらで処理します。
MANUAL
