#!/bin/bash
# note 送客 ワンコマンド起動スクリプト（オーナーのMacで実行）
#
#   bash go.sh
#
# これ1つで：①必要ならセットアップ → ②必要ならnoteログイン → ③1本目を下書き保存
# まで面倒を見る。2回目以降は、もう setup/login はスキップされる。

set -e
cd "$(dirname "$0")"   # このスクリプトのある場所(note_publisher)へ移動

echo "════════════════════════════════════════"
echo " note 送客スクリプト ワンコマンド起動"
echo "════════════════════════════════════════"

# ── ① セットアップ（Playwright が無ければ入れる）──
if ! python3 -c "import playwright" 2>/dev/null; then
  echo ""
  echo "▶ 初回セットアップ（Playwright＋Chromeを入れます。数分かかります）…"
  python3 -m pip install --upgrade playwright
  python3 -m playwright install chromium
else
  echo "✓ セットアップ済み（Playwrightあり）"
fi

# ── ② note ログイン（プロファイルが無ければログイン）──
PROFILE="$HOME/.note_publisher_profile"
if [ ! -d "$PROFILE" ] || [ -z "$(ls -A "$PROFILE" 2>/dev/null)" ]; then
  echo ""
  echo "▶ noteへの初回ログインを行います。"
  echo "  ブラウザが開くので note にログイン → 完了したらターミナルで Enter。"
  python3 publish_to_note.py --login
else
  echo "✓ note ログイン済み（プロファイルあり）"
fi

# ── ③ 1本目を下書き保存（安全） ──
echo ""
echo "▶ 配信キットの内容を確認します："
python3 publish_share_notes.py --list

echo ""
echo "▶ 1本目を『下書き保存』します（公開はしません）。"
echo "  ブラウザにタイトル・本文が入った状態で止まります。"
echo "  → みんなのフォトギャラリーで画像を選び、自分で『公開』を押してください。"
echo ""
read -r -p "始めるには Enter（やめるには Ctrl+C）..." _
python3 publish_share_notes.py --post 1

echo ""
echo "════════════════════════════════════════"
echo " 完了。うまく入ったか確認してください。"
echo " 次の本：python3 publish_share_notes.py --post 2"
echo " 全部下書き：python3 publish_share_notes.py --all"
echo "════════════════════════════════════════"
