#!/usr/bin/env bash
# note_post.sh — Vol N の note 投稿をできる限り自動化
#
# 自動でやること：
#   - note の新規投稿ページをブラウザで開く
#   - dist/ フォルダを Finder で開く
#   - タイトルをクリップボードへ（⌘+V で貼付可能）
#   - Enter でステップ進行 → 本文・タグも順次クリップボードへ
#   - 添付ファイル・アイキャッチのパスを案内
#
# 使い方：
#   bash note_post* 7    # Vol.7 を投稿モードで起動

set -e
cd "$(dirname "$0")"

VOL="${1:-7}"
HELPER="./note_copy.sh"

if [ ! -x "$HELPER" ]; then
  echo "❌ $HELPER が見つかりません" >&2
  exit 1
fi

# Vol 別の添付ファイル特定
DIST_DIR="projects/2026-04-08_月30万自動化/C_テンプレ販売/dist"
ATTACH=$(find "$DIST_DIR" -maxdepth 1 -name "Vol${VOL}_*" -type f 2>/dev/null | head -1)
ATTACH_DIR=$(find "$DIST_DIR" -maxdepth 1 -name "Vol${VOL}_*" -type d 2>/dev/null | head -1)
EYECATCH="$DIST_DIR/eyecatch/Vol${VOL}.png"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Vol.${VOL} 投稿アシスタント"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ステップ1：ブラウザと Finder を開く
echo "【ステップ 1/4】 note の新規投稿ページを開きます..."
open "https://note.com/notes/new" 2>/dev/null || echo "  (open コマンド失敗。手動でブラウザを開いてください)"
echo "                Finder で dist フォルダを開きます..."
open "$DIST_DIR" 2>/dev/null || echo "  (open コマンド失敗。手動で開いてください)"
sleep 2
echo ""

# ステップ2：タイトル
echo "【ステップ 2/4】 タイトルをクリップボードに入れます..."
bash "$HELPER" "$VOL" title >/dev/null
echo "  ✅ クリップボード OK"
echo ""
echo "  👉 note のブラウザでタイトル欄をクリック → ⌘+V でペースト"
echo ""
read < /dev/tty -p "  ペーストしたら Enter で次へ（本文）..."
echo ""

# ステップ3：本文
echo "【ステップ 3/4】 本文をクリップボードに入れます..."
bash "$HELPER" "$VOL" body >/dev/null
echo "  ✅ クリップボード OK"
echo ""
echo "  👉 note の本文欄をクリック → ⌘+V でペースト"
echo ""
read < /dev/tty -p "  ペーストしたら Enter で次へ（添付・タグ）..."
echo ""

# ステップ4：添付ファイル案内
echo "【ステップ 4/4】 添付ファイルとタグの設定"
echo ""
if [ -n "$ATTACH" ]; then
  echo "  📎 添付ファイル（本文末にドラッグ）："
  echo "     $ATTACH"
elif [ -n "$ATTACH_DIR" ]; then
  echo "  📎 添付ファイル（Vol.11 はパック・全ファイル添付）："
  ls "$ATTACH_DIR" | sed 's/^/     /'
fi
echo ""
echo "  🖼  アイキャッチ（記事のサムネ画像）："
echo "     $EYECATCH"
echo ""
echo "  🏷  タグ（クリップボードに参考用テキストを入れます）："
bash "$HELPER" "$VOL" tags >/dev/null
echo "     → タグ欄に1つずつ追加。クリップボードの内容を参考に。"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  最終ステップ（オーナー手作業）："
echo "    1. Finder の上記ファイルを note の本文末・アイキャッチ欄にドラッグ"
echo "    2. note の「販売設定」→「有料記事」で価格を入力"
echo "    3. タグを追加"
echo "    4. 「公開」ボタンをクリック"
echo ""
echo "  公開できたら URL を Claude に貼ってください。"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
