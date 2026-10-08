#!/bin/bash
# フォロワーを増やす（富山/氷見/高岡/お取り寄せ などの発信者に フォロー＋スキ）。
# コメントは付けない＝同一文面の連投を構造的に起こさない（A5）。
# フォロワー数を ops/follower_log.tsv に1行残す＝測らないと効いたか分からない。
set -u
cd "$(dirname "$0")/.."
# ★2026-10-07: **コメントをくれた人を先にフォローする**。
#   わざわざ名前を出して反応してくれた相手で、いちばんフォローバックが期待できる。
#   これまではタグ検索で見つけた人だけを見ていて、ここを素通りしていた。
python3 ops/follow_commenters.py --go || echo "⚠️ コメント主のフォローでつまずきました"

# ★2026-10-08: **自分の記事にスキを付けた人**を追う。
#   これまではタグ検索で見つけた知らない人だけを見ていて、
#   **すでに反応してくれた人**を素通りしていた。実ページで確認したら、
#   1本に17スキ付いている記事があった＝17人が関心を示している。
#   関心の強い順に追う: コメント > スキ > タグ検索。
python3 ops/follow_likers.py --go || echo "⚠️ スキをくれた人のフォローでつまずきました"


OUT="$(python3 CDO/outputs/note_publisher/_cowork_growth.py --discover --go 2>&1 || true)"
echo "$OUT" | tail -8
AFTER="$(echo "$OUT" | sed -n 's/^FOLLOWERS_AFTER:: *//p' | tail -1)"
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
fi
if [ -n "${AFTER}" ]; then
  [ -f ops/follower_log.tsv ] || printf '# note フォロワー数の推移\ndate\tfollowers_raw\tnew_follows\n' > ops/follower_log.tsv
  printf '%s\t%s\t%s\n' "$(date +%F)" "${AFTER}" "${N}" >> ops/follower_log.tsv
  echo "記録: $(date +%F) ${AFTER} / 今回フォロー ${N}人"
else
  echo "⚠️ フォロワー数が読めなかった（ログインが切れている可能性）"
fi
