#!/bin/bash
# フォロワーを増やす（富山/氷見/高岡/お取り寄せ などの発信者に フォロー＋スキ）。
# コメントは付けない＝同一文面の連投を構造的に起こさない（A5）。
# フォロワー数を ops/follower_log.tsv に1行残す＝測らないと効いたか分からない。
set -u
cd "$(dirname "$0")/.."
. "$(dirname "$0")/_pybin.sh"   # ブラウザを開くものは playwright 入りの python で動かす
# ★2026-10-07: **コメントをくれた人を先にフォローする**。
#   わざわざ名前を出して反応してくれた相手で、いちばんフォローバックが期待できる。
#   これまではタグ検索で見つけた人だけを見ていて、ここを素通りしていた。
"$PYBIN" ops/follow_commenters.py --go || echo "⚠️ コメント主のフォローでつまずきました"

# ★2026-10-08: **自分の記事にスキを付けた人**を追う。
#   これまではタグ検索で見つけた知らない人だけを見ていて、
#   **すでに反応してくれた人**を素通りしていた。実ページで確認したら、
#   1本に17スキ付いている記事があった＝17人が関心を示している。
#   関心の強い順に追う: コメント > スキ > タグ検索。
"$PYBIN" ops/follow_likers.py --go || echo "⚠️ スキをくれた人のフォローでつまずきました"


OUT="$("$PYBIN" CDO/outputs/note_publisher/_cowork_growth.py --discover --go 2>&1 || true)"
echo "$OUT" | tail -8
AFTER="$(echo "$OUT" | sed -n 's/^FOLLOWERS_AFTER:: *//p' | tail -1)"
# ★2026-11-09: AFTER は**この script の最後**に出る。途中で打ち切られると空になり、
#   フォロワー数が1行も記録されない。実際 11-07〜11-09 の3便がそうなっていた
#   （cowork_run.sh に付けた 600秒の上限で、この工程が切られていた＝**こちらの入れた上限が原因**）。
#   BEFORE は**最初**に出るので、AFTER が無ければそちらを使う。
#   数えられた分だけでも残す＝「測っていない日」を作らない。
if [ -z "${AFTER}" ]; then
  AFTER="$(echo "$OUT" | sed -n 's/^FOLLOWERS_BEFORE:: *//p' | tail -1)"
  [ -n "${AFTER}" ] && echo "※ 途中で終わったので、開始時点の値を記録します（AFTER が無い）"
fi
# 画面に見えていた『フォロワー』の行（read_followers が外したときに出す）も残す
echo "$OUT" | grep -a '^FOLLOWERS_RAW_LINES::' | tail -2 || true
N="$(echo "$OUT" | grep -c '^DONE ')"
# ★2026-10-07: **0人でも「実行した」と報告されるのがいちばん危ない。**
#   セレクタが全滅していた（note の Next.js 移行でクラス名が消えた）ことに
#   70日気づかなかったのと同じ型。**0件は失敗として鳴らす**。
FOLLOWED="$(echo "$OUT" | grep -c 'followed')"
NOBTN="$(echo "$OUT" | grep -c 'no-follow-btn')"
NOAUTH="$(echo "$OUT" | grep -c 'no-author-follow-btn')"
if [ "${NOAUTH}" -gt 0 ]; then
  echo ""
  echo "❌ 著者のフォローボタンを特定できませんでした（${NOAUTH}件）。"
  echo "   別人を誤ってフォローしないよう、押さずに止めています。"
  echo "   ボタンの一覧を ops/logs/follow_buttons.json に保存しました。これを push すれば直せます。"
fi
if [ "${NOBTN}" -gt 0 ]; then
  echo ""
  echo "❌ フォローのボタンが ${NOBTN} 件で見つかりませんでした＝note の画面が変わっています。"
  echo "   ボタンの一覧を ops/logs/follow_buttons.json に保存しました。"
  echo "   これを push すれば、こちらで直せます（code は note を見られないため）。"
fi
if [ "${FOLLOWED}" = "0" ]; then
  echo "⚠️ 今回フォローできた人は0人です。上の理由を確認してください。"
  # ★2026-11-10: cowork_run.sh が既定で `tail -4` しか残さないため、
  #   **なぜ0人なのかが毎日ログから消えていた**（10-25 以降ずっと0人だったのに気づけなかった）。
  #   0人のときだけ、1人ずつの結果をここで出す＝次の便で原因を決められるようにする。
  echo "---- フォローできなかった理由（1人ずつ・最大14行）----"
  echo "$OUT" | grep -a '^DONE ' | tail -14 || echo "（DONE の行が1つも無い＝対象を1人も開けていない）"
  echo "---- ここまで ----"
fi
# ★2026-11-10 修正: ここは ${N}（＝DONE の行数＝**試した人数**）を
#   「今回フォロー」として記録・報告していた。**実際にフォローできた人数ではない。**
#   そのため、毎日「今回フォロー 14人」と出ていたのに、同じ run が
#   「⚠️ 今回フォローできた人は0人です」も出していた＝**同じ便の中で数字が矛盾していた**。
#   10-25 以降の記録を数えたら、**0人警告が出ていない日が1日も無い**
#   （11-07〜09 は上限で切られて警告まで届いていないだけ）。
#   ＝**16日以上、1人もフォローできていない**のに、台帳には毎日 14 と入っていた。
#   フォロワーが増えないのは当然で、R41 はその結果を見ていた。
#   → **成功した人数を記録する**。試した人数は別の欄に残す（0/14 のように見える）。
if [ -n "${AFTER}" ]; then
  [ -f ops/follower_log.tsv ] || printf '# note フォロワー数の推移\n# new_follows は**実際にフォローできた人数**（2026-11-10 以前は「試した人数」が入っている＝あてにしない）\ndate\tfollowers_raw\tnew_follows\ttried\n' > ops/follower_log.tsv
  printf '%s\t%s\t%s\t%s\n' "$(date +%F)" "${AFTER}" "${FOLLOWED}" "${N}" >> ops/follower_log.tsv
  echo "記録: $(date +%F) ${AFTER} / 今回フォローできた ${FOLLOWED}人（試した ${N}人）"
else
  echo "⚠️ フォロワー数が読めなかった（ログインが切れている可能性）"
fi
