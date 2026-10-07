#!/bin/bash
# ops/all_now.sh — これ1本で全部やる（owner の Mac で実行）
#
#   cd ~/agent-team && bash ops/all_now.sh
#
# 設計（2026-10-07 に作り直し）:
#   オーナーから「一発で決まるコードを書け・エラー多すぎ」。そのとおりなので、
#   **途中で何が失敗しても最後まで走り切り、最後に結果だけ出す**形にした。
#   - set -u / set -e は使わない。未定義変数や1つの失敗で止まらないようにする。
#   - git のロック残りは最初に自分で片付ける（2回詰まった実績がある）。
#   - 各段は失敗しても次へ進む。失敗は最後の一覧にまとめて出す。
#   - tty が無くても動く（tee /dev/tty を使わない）。
set +e
set +u
cd "$(dirname "$0")/.." 2>/dev/null || exit 1

FAILED=""
note_fail() { FAILED="${FAILED}
  - $1"; }

echo "########## 0) 準備（git の詰まりを自分で片付ける） ##########"
if ! pgrep -x git >/dev/null 2>&1; then
  rm -f .git/index.lock .git/HEAD.lock .git/refs/heads/main.lock 2>/dev/null
fi
git rebase --abort >/dev/null 2>&1
git pull --rebase --autostash origin main || { echo "pull に失敗。手元のまま続けます"; note_fail "git pull"; }

echo ""
echo "########## 1) キューの記事を公開する ##########"
bash ops/go.sh --all || note_fail "公開 (go.sh)"

echo ""
echo "########## 2) クレジット・英語・フォロー導線を note へ反映する ##########"
for i in 1 2 3 4 5 6; do
  OUT_C="$(bash ops/fix_credits_on_note.sh 20 2>&1)"
  echo "$OUT_C" | tail -3
  LEFT="$(echo "$OUT_C" | sed -n 's/.*残り \([0-9]*\)本.*/\1/p' | tail -1)"
  [ -z "$LEFT" ] && { note_fail "note への反映 (${i}周目で止まった)"; break; }
  [ "$LEFT" = "0" ] && break
done

echo ""
echo "########## 3) コメントを取りに行く ##########"
bash ops/comments_now.sh || note_fail "コメント取得"

echo ""
echo "########## 4) コメントに返信する ##########"
python3 ops/auto_reply_comments.py --go || note_fail "返信の下書き"
python3 CDO/outputs/note_publisher/post_comment_replies.py --go || note_fail "返信の投稿"

echo ""
echo "########## 5) フォロワーを増やす（目標 1日ひとり） ##########"
bash ops/growth_now.sh || note_fail "集客"

echo ""
echo "########## 6) 固定記事（まだなら1回だけ） ##########"
if [ -f ops/.pinned_done ]; then
  echo "設定済みなので飛ばします"
else
  bash ops/pin_article.sh na096464584e5 --go && touch ops/.pinned_done || note_fail "固定記事"
fi

echo ""
echo "########## 7) 片付けて push ##########"
git add -A 2>/dev/null
git commit -q -m "all_now: $(date +%F_%H%M)" 2>/dev/null
if ! pgrep -x git >/dev/null 2>&1; then rm -f .git/index.lock 2>/dev/null; fi
git pull --rebase --autostash -q origin main >/dev/null 2>&1
PUSH_OUT="$(git push -u origin main 2>&1)"; PUSH_RC=$?
echo "$PUSH_OUT" | tail -1
[ "$PUSH_RC" != "0" ] && note_fail "push"

QUEUE="$(ls drafts/queue/*.md 2>/dev/null | wc -l | tr -d ' ')"
TODO="$(grep -c '^n[0-9a-f]\{12\}' ops/credit_update_todo.tsv 2>/dev/null)"; TODO="${TODO:-0}"
DONE="$(grep -c '^n[0-9a-f]\{12\}' ops/credit_update_done.tsv 2>/dev/null)"; DONE="${DONE:-0}"
CMT="$(wc -l < ops/comments/pending.tsv 2>/dev/null)"; CMT=$(( ${CMT:-1} - 1 ))
POSTED="$(grep -c 'POSTED' ops/comments/replies.tsv 2>/dev/null)"; POSTED="${POSTED:-0}"
FOL="$(tail -1 ops/follower_log.tsv 2>/dev/null | grep -v '^#' | grep -v '^date' | awk -F'\t' '{print $1" "$2" / 今回フォロー "$3"人"}')"

echo ""
echo "================ 結果 ================"
echo "公開キューの残り      : ${QUEUE} 本"
echo "note へ未反映          : $(( TODO - DONE )) 本"
echo "取れたコメント        : ${CMT} 件"
echo "投稿した返信          : ${POSTED} 件"
echo "フォロワー            : ${FOL:-記録できず}   目標 1日ひとり"
if [ -n "$FAILED" ]; then
  echo ""
  echo "うまくいかなかったもの:${FAILED}"
  echo ""
  echo "この画面をそのまま Claude に貼ってください。原因を特定して直します。"
else
  echo ""
  echo "全部通りました。"
fi
