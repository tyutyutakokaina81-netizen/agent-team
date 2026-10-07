#!/bin/bash
# フォロワーを増やす（富山/氷見/高岡/お取り寄せ などの発信者に フォロー＋スキ）。
# コメントは付けない＝同一文面の連投を構造的に起こさない（A5）。
# フォロワー数を ops/follower_log.tsv に1行残す＝測らないと効いたか分からない。
set -u
cd "$(dirname "$0")/.."
OUT="$(python3 CDO/outputs/note_publisher/_cowork_growth.py --discover --go 2>&1 || true)"
echo "$OUT" | tail -8
AFTER="$(echo "$OUT" | sed -n 's/^FOLLOWERS_AFTER:: *//p' | tail -1)"
N="$(echo "$OUT" | grep -c '^DONE ')"
if [ -n "${AFTER}" ]; then
  [ -f ops/follower_log.tsv ] || printf '# note フォロワー数の推移\ndate\tfollowers_raw\tnew_follows\n' > ops/follower_log.tsv
  printf '%s\t%s\t%s\n' "$(date +%F)" "${AFTER}" "${N}" >> ops/follower_log.tsv
  echo "記録: $(date +%F) ${AFTER} / 今回フォロー ${N}人"
else
  echo "⚠️ フォロワー数が読めなかった（ログインが切れている可能性）"
fi
