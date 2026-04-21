#!/bin/bash
# 受注チェック自動実行（macOS通知＋ブラウザ自動起動）
# launchd から呼ばれて1日5回自動実行される
#
# 使い方: launchd経由で自動呼び出し。手動でも実行可能
#   ./scripts/deliver/auto_check_orders.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_DIR"

LOG_DIR="$REPO_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/order_check.log"

TIME_NOW=$(date '+%H:%M')
TIME_HOUR=$(date '+%H')
DATE_NOW=$(date '+%Y-%m-%d')

{
    echo ""
    echo "[$DATE_NOW $TIME_NOW] 🔔 自動受注チェック発動"
} >> "$LOG_FILE"

# 時間帯に応じたメッセージ
case "$TIME_HOUR" in
    0[5-9]|10) GREETING="おはようございます。昨夜の新着メッセージを確認しましょう" ;;
    1[1-3]) GREETING="昼休み！メッセージチェックのタイミングです" ;;
    1[4-7]) GREETING="夕方です。午後の新着案件を確認しましょう" ;;
    1[8-9]|2[0-2]) GREETING="夜です。本日最後の受注チェック" ;;
    *) GREETING="受注チェックの時間です" ;;
esac

# macOS通知（クリックするとブラウザが開く）
if command -v osascript &>/dev/null; then
    # 通知を表示
    osascript -e "display notification \"$GREETING\nCrowdWorks・Lancers・ママワークスを自動で開きます\" with title \"📬 受注チェック $TIME_NOW\" sound name \"Ping\""

    # 3サイトを自動で開く（デフォルトブラウザのタブで）
    open 'https://crowdworks.jp/mypage/'
    sleep 1
    open 'https://www.lancers.jp/mypage'
    sleep 1
    open 'https://mamaworks.jp/member/home'

    echo "[$DATE_NOW $TIME_NOW] ✅ 通知送信＆3サイト起動完了" >> "$LOG_FILE"
else
    echo "[$DATE_NOW $TIME_NOW] ⚠️  macOS以外のためosascript使用不可" >> "$LOG_FILE"
fi
