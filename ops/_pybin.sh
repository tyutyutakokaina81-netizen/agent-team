# ops/_pybin.sh — ブラウザを開くスクリプトを、playwright が入っている python で動かす
#
# なぜ（2026-10-08）:
#   日次ログ publish_2026-10-08_080005.log に `ModuleNotFoundError: No module named 'playwright'`
#   が出ていた。調べたら **publish_to_note.py だけが $PYBIN（~/.note_venv/bin/python）で呼ばれ、
#   それ以外のブラウザ操作は全部 `python3`（macOS 既定の 3.9）で呼ばれていた**。
#   その結果、以下が毎日「実行はされるが必ず失敗する」状態だった:
#     ・フォロー（follow_commenters / follow_likers / _cowork_growth）＝ オーナーが何度も
#       「フォロワー増やして」と言っていたのに、**0人なのは当然だった**
#     ・コメントの取得と返信の投稿（fetch_note_comments / post_comment_replies）
#     ・閲覧数の取得（fetch_note_stats）＝ 一度も取れていない
#     ・公開状態の確認（check_public_all）
#   公開だけが通っていたので、表からは「動いている」ように見えていた。
#
# 使い方: 各スクリプトの先頭で `. "$(dirname "$0")/_pybin.sh"` し、`"$PYBIN" foo.py` と呼ぶ。
_pick_py() {
  for c in "$HOME/.note_venv/bin/python" "$HOME/.note_venv/bin/python3" python3 python; do
    if [ -x "$c" ] || command -v "$c" >/dev/null 2>&1; then
      if "$c" -c "import playwright" >/dev/null 2>&1; then echo "$c"; return 0; fi
    fi
  done
  echo "python3"
}
PYBIN="${PYBIN:-$(_pick_py)}"
export PYBIN
