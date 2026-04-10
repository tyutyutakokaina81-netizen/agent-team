#!/bin/zsh
# ================================================================
# setup_cron.sh — パイプラインを毎日自動実行する cron を設定
# 使い方: ./setup_cron.sh
# ================================================================
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
LOGFILE="$REPO_DIR/pipeline.log"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ⏰ cron 自動実行セットアップ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 現在の crontab を取得
CURRENT_CRON=$(crontab -l 2>/dev/null || echo "")

# 既に登録済みか確認
if echo "$CURRENT_CRON" | grep -q "agent-team/start.sh"; then
  echo "\n  ✅ 既に cron 登録済みです"
  echo "\n  現在の設定:"
  echo "$CURRENT_CRON" | grep "agent-team"
  echo ""
  exit 0
fi

# cron に追加（毎日 9:00 と 18:00 に実行）
NEW_CRON="$CURRENT_CRON
# agent-team パイプライン（毎日 9:00 と 18:00）
0 9 * * * $REPO_DIR/start.sh >> $LOGFILE 2>&1
0 18 * * * $REPO_DIR/start.sh >> $LOGFILE 2>&1"

echo "$NEW_CRON" | crontab -

echo "\n  ✅ cron に登録しました"
echo "\n  実行スケジュール:"
echo "    毎日 09:00 → パイプライン自動実行"
echo "    毎日 18:00 → パイプライン自動実行"
echo "\n  ログ: $LOGFILE"
echo "\n  停止する場合: crontab -e で該当行を削除"
echo ""
