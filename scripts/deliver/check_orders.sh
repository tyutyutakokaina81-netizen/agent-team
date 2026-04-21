#!/bin/bash
# 受注チェック デイリールーティン（手動実行推奨）
# 朝・昼・夕に3回これを実行すれば受注機会を逃さない
#
# 使い方:
#   ./scripts/deliver/check_orders.sh
#
# 動作:
# 1. 各プラットフォームのURLを表示＆ブラウザで開く
# 2. メッセージ来てるか？の確認プロンプト
# 3. 来てたらクリップボードにコピー→精査ツール起動

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_DIR"

echo "========================================"
echo "📬 受注チェック $(date '+%Y-%m-%d %H:%M')"
echo "========================================"
echo ""
echo "今から以下3サイトのメッセージ/案件をチェックします:"
echo ""
echo "  1. クラウドワークス: https://crowdworks.jp/mypage"
echo "  2. ランサーズ:       https://www.lancers.jp/mypage"
echo "  3. ママワークス:     https://mamaworks.jp/member/home"
echo ""

# Macならブラウザで開く
if command -v open &>/dev/null; then
    read -p "各サイトをブラウザで開きますか？ (y/N): " OPEN_BROWSER
    if [[ "$OPEN_BROWSER" = "y" ]] || [[ "$OPEN_BROWSER" = "Y" ]]; then
        open 'https://crowdworks.jp/mypage'
        open 'https://www.lancers.jp/mypage'
        open 'https://mamaworks.jp/member/home'
        echo "✅ ブラウザで開きました"
        echo ""
        echo "各サイトで未読メッセージ・新着案件を確認してください。"
        echo ""
    fi
fi

echo "========================================"
echo "📋 チェックリスト"
echo "========================================"
echo "  □ 未返信メッセージ"
echo "  □ 選考中案件の進捗"
echo "  □ 新着マッチング案件"
echo "  □ 検収依頼/入金通知"
echo ""

read -p "新規メッセージ/受注連絡はありましたか？ (y/N): " HAS_ORDER
if [[ "$HAS_ORDER" = "y" ]] || [[ "$HAS_ORDER" = "Y" ]]; then
    echo ""
    echo "========================================"
    echo "📝 内容の精査"
    echo "========================================"
    echo ""
    echo "メッセージの内容をコピー（Cmd+C）してから以下を実行："
    echo ""
    echo "  ./scripts/deliver/auto_process.sh"
    echo ""
    read -p "今すぐ精査しますか？ (y/N): " DO_NOW
    if [[ "$DO_NOW" = "y" ]] || [[ "$DO_NOW" = "Y" ]]; then
        "$SCRIPT_DIR/auto_process.sh"
    fi
else
    echo ""
    echo "📭 新規メッセージなし。次の時間にまたチェック。"
fi

echo ""
echo "========================================"
echo "✅ 受注チェック完了"
echo "========================================"
echo ""
echo "次のチェック推奨タイミング："
HOUR=$(date +%H)
if [[ "$HOUR" -lt 12 ]]; then
    echo "  🕐 昼休み（12-13時）"
    echo "  🕒 夕方（17-18時）"
elif [[ "$HOUR" -lt 17 ]]; then
    echo "  🕒 夕方（17-18時）"
    echo "  🌙 夜（20-22時）"
elif [[ "$HOUR" -lt 21 ]]; then
    echo "  🌙 夜（20-22時）"
    echo "  ☀️ 明日朝（8-9時）"
else
    echo "  ☀️ 明日朝（8-9時）"
    echo "  🕐 昼休み（12-13時）"
fi
