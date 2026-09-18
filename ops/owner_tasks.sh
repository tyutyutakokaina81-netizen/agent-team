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
# 2026-09-16 判明: 日次実行は **新着10本 + backlog5本** の2回に分けて回しており、
# セレクタ外れ6件は **backlog 側（古い記事）** で出ている。新着側は20本回して外れ0だった。
# なので切り分けは backlog を厚めに回す方が確実。
echo "[新着]"
"$PYBIN" CDO/outputs/note_publisher/fetch_note_comments.py --debug --limit 10
# 2026-09-16: 公開202本のうち**巡回済みは115本＝56%**で、87本は一度も見ていない。
# 「コメントは無い」と言うには被覆が足りないので、backlog を厚く回して全件を埋める。
echo "[backlog＝未巡回の古い記事を厚めに回す（全件を見るまで『コメント無し』と言えないため）]"
"$PYBIN" CDO/outputs/note_publisher/fetch_note_comments.py --debug --backlog --limit 45
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
SWEEP_LINE="$(grep -h '=== 結果: 巡回' "${OUT}" | tr '\n' ' ')"
THUMB_ERR="$(grep -h 'サムネ自動設定に失敗' "${LATEST_LOG}" 2>/dev/null | head -3)"
"$PYBIN" ops/process_inbox.py post --from cowork --to code --type report \
  --title "owner_tasks 実行結果 ${TS}" \
  --body "コメント巡回: ${SWEEP_LINE:-（結果行が取れなかった。ログ ${OUT} を参照）}

サムネ設定失敗の例外:
${THUMB_ERR:-（該当なし。対象ログ: ${LATEST_LOG:-なし}）}

全出力: ${OUT}（このログは追跡対象になったので一緒に push されます）"

# ---------------------------------------------------------------
# 手作業が要るもの（ここからは自動化できない）
# ---------------------------------------------------------------
cat <<'MANUAL'

==========================================================
 ここからは手作業です（ブラウザ / キー投入）
==========================================================

[A] 見出し画像なしで公開された5本に画像を付ける ★最優先（自動化済み・貼るだけ）
      bash ops/fix_header_images.sh
    ①今のエディタUIを実測（何も変更しない）→ ②画像を設定して更新、を続けて実行します。
    ボタン名に頼らず input[type=file] へ直接入れる方法から試すので、note のUI変更に強い。
    失敗しても画面のボタン一覧とHTMLを ops/logs/_thumb_debug/ に保存して push します
    （＝code がセレクタを直せる材料になる。手で「検証」を開く必要はもうありません）。
    様子だけ見たいとき:  bash ops/fix_header_images.sh --probe

[B] X(Twitter)投稿を動かす（40スレッドが未投稿のまま滞留）
      bash ops/run_x.sh            # 診断＋DRY-RUN（投稿しない。何が足りないか出ます）
      bash ops/run_x.sh --setup    # キーの置き場所 ~/.x_keys.env を作る（値は自分で書く）
      bash ops/run_x.sh --install  # tweepy を入れる
      bash ops/run_x.sh --go       # 先頭1スレッドだけ投稿（連投しません）
    キーは ~/.x_keys.env（リポジトリの外）にだけ置きます。値は画面にも git にも出ません。

[C] 公開済み2本に権利クレジットを追記する（CC BY / CC BY-SA の表示義務）
    対象は ops/inbox/2026-09-08_004 に記載。本文末尾にクレジット行を足すだけです。

[D] 「冷やしトマト」の記事が note 上で下書きのままでないか確認する
    下書きなら公開してください（ops/inbox/2026-09-09_003）。

[E] （[B] に統合しました）X の API キー投入は bash ops/run_x.sh --setup でやります。

==========================================================
MANUAL
echo "ログ: ${OUT}"

# ここで初めて commit する。以前はこの上でコミットしていたため、
# **コミット後も手作業一覧をログに書き足していて**、実行のたびにログが未コミットの差分として残り、
# 次回の `git pull` が「unstaged changes」で止まっていた（2026-09-16 発覚）。
git add -A
git commit -m "owner_tasks: ${TS}" || true
for i in 1 2 3 4; do git push origin "$(git rev-parse --abbrev-ref HEAD)" && break || sleep $((2**i)); done

