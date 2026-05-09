#!/bin/bash
# notify.sh — 応募成功/失敗を Mac 通知で表示し履歴を残す
#
# 使い方:
#   bash scripts/notify.sh success "案件名"
#   bash scripts/notify.sh failure "失敗理由"
#
# 動作:
#   - macOS: osascript で通知センター表示
#   - Linux/その他: 通知はスキップしてログだけ追記
#   - logs/notifications.log に追記（タイムスタンプ + 種別 + メッセージ）

set -e

# 引数チェック
STATUS="${1:-}"
MESSAGE="${2:-}"

if [ -z "$STATUS" ] || [ -z "$MESSAGE" ]; then
  echo "使い方: bash notify.sh {success|failure} \"メッセージ\""
  exit 1
fi

# パス解決（このスクリプトの場所からリポジトリルートを推定）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"
LOG_FILE="$LOG_DIR/notifications.log"

mkdir -p "$LOG_DIR"

# タイムスタンプ
TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"

# 通知タイトルとメッセージを組み立て
case "$STATUS" in
  success)
    ICON="✅"
    TITLE="CrowdWorks応募成功"
    BODY="$MESSAGE"
    ;;
  failure)
    ICON="❌"
    TITLE="CrowdWorks応募失敗"
    BODY="$MESSAGE"
    ;;
  *)
    echo "[ERROR] STATUS は success または failure を指定してください: $STATUS"
    exit 1
    ;;
esac

NOTIFY_TEXT="$ICON $TITLE: $BODY"

# ログに追記
echo "[$TIMESTAMP] [$STATUS] $NOTIFY_TEXT" >> "$LOG_FILE"

# OS 判定して通知
OS_NAME="$(uname -s)"
if [ "$OS_NAME" = "Darwin" ]; then
  # osascript 用にダブルクォートをエスケープ
  ESCAPED_BODY="$(printf '%s' "$BODY" | sed 's/"/\\"/g')"
  ESCAPED_TITLE="$(printf '%s' "$ICON $TITLE" | sed 's/"/\\"/g')"
  osascript -e "display notification \"$ESCAPED_BODY\" with title \"$ESCAPED_TITLE\"" 2>/dev/null || \
    echo "[WARN] osascript の通知発出に失敗しました（ログには記録済）" >&2
else
  # Linux/その他は通知センターが無いのでスキップ（ログ記録のみ）
  echo "[INFO] 非 macOS 環境のため通知はスキップ。ログ記録: $LOG_FILE" >&2
fi

# stdout にも内容を出す（呼び出し元が確認できるように）
echo "$NOTIFY_TEXT"
