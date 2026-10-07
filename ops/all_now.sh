#!/bin/bash
# ops/all_now.sh — いま溜まっている作業を、順番に全部やる（owner の Mac で実行）
#
#   cd ~/agent-team && bash ops/all_now.sh
#
# なぜ（2026-10-07）: 「まとめてターミナルに貼りたい」。
#   これまで公開・クレジット反映・コメント取得・集客を別々のコマンドで渡していて、
#   そのたびに git で詰まっていた。順番と後片付けまで含めて1本にする。
#
# 順番には理由がある:
#   1 公開   … いちばん読まれるのは公開直後。先に出す
#   2 反映   … 英語要約とフォロー導線が未達の記事を note に届ける（フォロワー導線そのもの）
#   3 コメント… 返信のために文面を取る
#   4 集客   … フォロー＋スキ。フォロワー数を記録する
#   5 固定記事… 初めて来た人が最初に見る場所
set -u
cd "$(dirname "$0")/.."
echo "########## 0) 最新を取り込む ##########"
git pull --rebase --autostash origin main || echo "⚠️ pull に失敗。手元のまま続行します"

echo ""
echo "########## 1) キューの記事を公開する ##########"
bash ops/go.sh --all || echo "⚠️ 公開でつまずきました。先へ進みます"

echo ""
echo "########## 2) クレジット・英語要約・フォロー導線を note へ反映する ##########"
for i in 1 2 3 4 5; do
  LEFT="$(bash ops/fix_credits_on_note.sh 20 2>&1 | tee /dev/tty | sed -n 's/.*残り \([0-9]*\)本.*/\1/p' | tail -1)"
  [ -z "${LEFT}" ] && break
  [ "${LEFT}" = "0" ] && break
done

echo ""
echo "########## 3) コメントを取りに行く ##########"
bash ops/comments_now.sh || echo "⚠️ コメント取得でつまずきました。先へ進みます"

echo ""
echo "########## 3.5) コメントに返信する（自動） ##########"
# 下書きを作る→READY だけ投稿する。質問・批判・スパム・短すぎるものは自動では返さない。
python3 ops/auto_reply_comments.py --go || echo "⚠️ 返信の下書きでつまずきました"
python3 CDO/outputs/note_publisher/post_comment_replies.py --go || echo "⚠️ 返信の投稿でつまずきました"

echo ""
echo "########## 4) フォロワーを増やす（目標: 1日ひとり） ##########"
bash ops/growth_now.sh || echo "⚠️ 集客でつまずきました。先へ進みます"

echo ""
echo "########## 5) 固定記事を設定する（まだなら） ##########"
if [ -f ops/.pinned_done ]; then
  echo "設定済みなので飛ばします"
else
  bash ops/pin_article.sh na096464584e5 --go && touch ops/.pinned_done || echo "⚠️ 固定記事の設定でつまずきました"
fi

echo ""
echo "########## 6) 片付けて push ##########"
git add -A ops CDO/outputs/note_publisher/_before_update CMO/outputs ops/logs/follow_buttons.json ops/logs/like_buttons.json 2>/dev/null || true
git commit -q -m "all_now: $(date +%F_%H%M) の実行結果" 2>/dev/null \
  && (git pull --rebase --autostash -q origin main || true) \
  && git push -u origin main 2>&1 | tail -1 || echo "変更なし"

echo ""
echo "================ ここまでの結果 ================"
echo "公開キューの残り   : $(ls drafts/queue/*.md 2>/dev/null | wc -l | tr -d ' ') 本"
echo "note へ未反映の記事 : $(( $(grep -c '^n' ops/credit_update_todo.tsv 2>/dev/null || echo 0) - $(grep -c '^n' ops/credit_update_done.tsv 2>/dev/null || echo 0) )) 本"
echo "取れたコメント      : $(( $(wc -l < ops/comments/pending.tsv 2>/dev/null || echo 1) - 1 )) 件"
echo "フォロワーの記録    : $(tail -1 ops/follower_log.tsv 2>/dev/null || echo 'まだ無し')  ← 目標 1日ひとり"
echo "返信: 投稿済 $(grep -c 'POSTED' ops/comments/replies.tsv 2>/dev/null || echo 0) 件 / 保留 $(grep -c 'HOLD' ops/comments/replies.tsv 2>/dev/null || echo 0) 件"
echo ""
echo "※ コメントが1件以上取れていたら、その行をそのまま Claude に貼ってください。返信文を書きます。"
