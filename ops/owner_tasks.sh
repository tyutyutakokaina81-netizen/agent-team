#!/bin/bash
# オーナーがMacで実行する「code にはできない作業」のまとめ。
#   使い方:  cd ~/agent-team && git pull && bash ops/owner_tasks.sh
#
# このスクリプトは**自動でできることだけ**やり、結果を ops/outbox に書いて push する。
# ブラウザ操作が要るものは最後に一覧で出すだけで、勝手には触らない。
set -uo pipefail
cd "$(dirname "$0")/.."
PYBIN="${PYBIN:-python3}"
TS="$(date +%Y-%m-%d_%H%M%S)"
OUT="ops/logs/owner_tasks_${TS}.log"
mkdir -p ops/logs
exec > >(tee -a "$OUT") 2>&1

echo "=== owner_tasks ${TS} (branch=$(git rev-parse --abbrev-ref HEAD)) ==="
git pull --rebase --autostash || true

# ---------------------------------------------------------------
# 1) コメント巡回の「セレクタ外れ」を切り分ける（6件で止まっている）
#    前例では、外れの正体は**記事が note 上で下書きのままだった**こと。
#    --debug で外れたページのHTMLを保存する。
# ---------------------------------------------------------------
echo ""
echo "--- [1/3] コメント巡回（--debug でHTML保存） ---"
"$PYBIN" CDO/outputs/note_publisher/fetch_note_comments.py --debug --limit 20 --rescan
SWEEP_RC=$?
echo "(終了コード: ${SWEEP_RC})"

# ---------------------------------------------------------------
# 2) 直近の公開ログから「サムネ自動設定に失敗」の例外メッセージを抜く
#    ＝なぜ見出し画像が付かなかったのかを知りたい。
#    ※ログは今まで .gitignore の *.log で無視されていて code に届いていなかった。
#      修正済みなので、今後はこのファイルごと push される。
# ---------------------------------------------------------------
echo ""
echo "--- [2/3] 直近の公開ログからサムネ失敗の原因を抽出 ---"
LATEST_LOG="$(ls -t ops/logs/publish_*.log 2>/dev/null | head -1)"
if [ -n "${LATEST_LOG}" ]; then
  echo "対象ログ: ${LATEST_LOG}"
  grep -n "サムネ自動設定に失敗" -A 2 "${LATEST_LOG}" || echo "（このログにサムネ失敗の行は無し）"
else
  echo "（ops/logs/ に publish ログが見つからない）"
fi

# ---------------------------------------------------------------
# 3) 結果を outbox に書いて push する（code がここを読んで続きをやる）
# ---------------------------------------------------------------
echo ""
echo "--- [3/3] 結果を ops/outbox に投函して push ---"
SWEEP_LINE="$(grep -h '=== 結果: 巡回' "${OUT}" | tail -1)"
THUMB_ERR="$(grep -h 'サムネ自動設定に失敗' "${LATEST_LOG}" 2>/dev/null | head -3)"
"$PYBIN" ops/process_inbox.py post --from cowork --to code --type report \
  --title "owner_tasks 実行結果 ${TS}" \
  --body "コメント巡回: ${SWEEP_LINE:-（結果行が取れなかった。ログ ${OUT} を参照）}

サムネ設定失敗の例外:
${THUMB_ERR:-（該当なし。対象ログ: ${LATEST_LOG:-なし}）}

全出力: ${OUT}（このログは追跡対象になったので一緒に push されます）"

git add -A
git commit -m "owner_tasks: ${TS}" || true
for i in 1 2 3 4; do git push origin "$(git rev-parse --abbrev-ref HEAD)" && break || sleep $((2**i)); done

# ---------------------------------------------------------------
# 手作業が要るもの（ここからは自動化できない）
# ---------------------------------------------------------------
cat <<'MANUAL'

==========================================================
 ここからは手作業です（ブラウザ / キー投入）
==========================================================

[A] 見出し画像が付いていない公開済み2本に、手で画像を設定する ★最優先
    note の編集画面を開いて、下の jpg を見出し画像に設定してください。
      新蕎麦  https://note.com/safe_canna441/n/n242960f609cf
        → CDO/outputs/note_publisher/thumbnails/2026-09-16_note記事_新蕎麦_秋になると幟が立つが違いが分かるかは別の話.jpg
      赤とんぼ https://note.com/safe_canna441/n/nc9bda3191cc5
        → CDO/outputs/note_publisher/thumbnails/2026-09-16_note記事_赤とんぼ_山で夏を過ごして秋に降りてくる.jpg

[B] 見出し画像エリアのボタンの現在の名前を調べて教えてください
    note の編集画面で見出し画像の「+」あたりを右クリック →「検証」。
    その button の aria-label とテキストをコピーして貼ってください。
    （publisher のセレクタがこれで直せます。いま2本連続で失敗しています）

[C] 公開済み2本に権利クレジットを追記する（CC BY / CC BY-SA の表示義務）
    対象は ops/inbox/2026-09-08_004 に記載。本文末尾にクレジット行を足すだけです。

[D] 「冷やしトマト」の記事が note 上で下書きのままでないか確認する
    下書きなら公開してください（ops/inbox/2026-09-09_003）。

[E] X(Twitter) API の Free tier キーを環境変数に入れる
    これが入るまで note→X の自動投稿はゼロのままです（恒常要件 R5 が BLOCKED）。
      export X_API_KEY=...
      export X_API_SECRET=...
      export X_ACCESS_TOKEN=...
      export X_ACCESS_SECRET=...

==========================================================
MANUAL
echo "ログ: ${OUT}"
