#!/bin/bash
# ops/go.sh — オーナーが Mac で叩く1本。これだけで通る。
#
#   cd ~/agent-team && bash ops/go.sh
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
# ★2026-09-25: `pgrep -f "git "` は**コマンドライン全体に "git " を含むだけ**の
#   無関係なプロセスにも当たる（実測: git を一度も呼んでいない bash に当たった）。
#   見たいのは「git が走っているか」なので、プロセス名で厳密に一致させる。
if pgrep -x git >/dev/null 2>&1; then
  echo "⚠️ 動いている git プロセスがあります。終わるのを待ってから、もう一度実行してください。"
  pgrep -lx git
  exit 1
fi
LOCKS="$(find .git -maxdepth 3 -name '*.lock*' 2>/dev/null)"
if [ -n "${LOCKS}" ]; then
  echo "git の残骸を消します（ロックファイルだけ。コミットや作業ファイルには触れません）:"
  echo "${LOCKS}"
  find .git -maxdepth 3 -name '*.lock*' -delete
else
  echo "残骸なし"
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
bash ops/publish_today.sh ${PUBARGS}
PUB_RC=$?
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
LATEST_LOG="$(ls -t ops/logs/publish_*.log 2>/dev/null | head -1)"
QUEUE_LEFT=$(ls drafts/queue/*.md 2>/dev/null | wc -l | tr -d ' ')
X_POSTED=$([ -f ops/logs/x_posted.tsv ] && grep -c . ops/logs/x_posted.tsv || echo 0)
X_PENDING=$(grep -c '^=== ' ops/x_queue.txt 2>/dev/null || echo "?")
echo "公開キューの残り : ${QUEUE_LEFT} 本"
echo "X の投稿実績     : ${X_POSTED} 件 ／ 未投稿スレッド ${X_PENDING} 本"
if [ -n "${LATEST_LOG}" ]; then
  echo ""
  echo "今回の公開ログ: ${LATEST_LOG}"
  grep -E "公開しました|https://note.com|✗|失敗" "${LATEST_LOG}" | tail -12
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

 この画面をそのまま Claude に貼れば、続きをこちらで処理します。
MANUAL
