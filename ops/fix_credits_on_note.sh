#!/bin/bash
# 公開済み記事のクレジット行の直しを、note 側へ少しずつ反映する。
# 直した内容: 出典URLをパーセント符号から戻す／クレジットを英語要約の前へ移す。
# 既定は1回6本（update_article.sh を1本ずつ呼ぶ）。
set -u
cd "$(dirname "$0")/.."
git pull --rebase --autostash origin main || echo "⚠️ git pull に失敗。手元のまま続行します"
TODO="ops/credit_update_todo.tsv"
DONE="ops/credit_update_done.tsv"
LIMIT="${1:-6}"
[ -f "$TODO" ] || { echo "✗ ${TODO} が無い"; exit 1; }
touch "$DONE"
n=0
while IFS=$'\t' read -r nid md title; do
  case "$nid" in \#*|note_id|"") continue;; esac
  grep -q "^${nid}" "$DONE" && continue
  [ "$n" -ge "$LIMIT" ] && break
  echo "--- ${nid}  ${title}"
  if python3 CDO/outputs/note_publisher/update_article.py "$nid" "$md" --go 2>/dev/null \
     || bash ops/update_article.sh "$nid" "$md" --go; then
    echo "${nid}	$(date +%F_%H%M)" >> "$DONE"
    n=$((n+1))
  else
    echo "  ⚠️ 失敗。次へ進みます"
  fi
done < "$TODO"
echo ""
echo "== 今回 ${n}本 / 残り $(( $(grep -c '^n' "$TODO") - $(grep -c '^n' "$DONE") ))本 =="
# 差し替え前の本文は必ず repo に残す（後から「何が消えたか」を確かめられるようにする）
git add -A ops/credit_update_done.tsv CDO/outputs/note_publisher/_before_update 2>/dev/null || true
git commit -q -m "credit: note 側へ反映 $(date +%F_%H%M)" 2>/dev/null && git push -u origin main 2>&1|tail -1 || echo "変更なし"
