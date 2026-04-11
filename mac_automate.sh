#!/bin/zsh
# mac_automate.sh — Mac上でBOOTH監視・自動更新をcronで設定
# 実行: zsh ~/agent-team/mac_automate.sh

set -e

AGENT_DIR="$HOME/agent-team"
LOG_DIR="$AGENT_DIR/logs"
mkdir -p "$LOG_DIR"

echo "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Mac 自動化セットアップ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 依存パッケージ
echo "\n[1/3] パッケージ確認..."
python3 -m pip install requests browser-cookie3 --break-system-packages -q 2>/dev/null || true
echo "  ✅ OK"

# cronジョブ登録
echo "\n[2/3] 自動化スケジュールを登録..."

PYTHON=$(which python3)

# 既存のagent-teamのcronを削除して再登録
crontab -l 2>/dev/null | grep -v "agent-team" > /tmp/crontab_clean || true

cat >> /tmp/crontab_clean << CRON
# agent-team 自動化
# 30分ごとにBOOTH売上チェック（クッキー自動更新つき）
*/30 * * * * $PYTHON $AGENT_DIR/mac_check_sales.py >> $LOG_DIR/cron_sales.log 2>&1
# 毎朝8時に日次レポート
0 8 * * * $PYTHON $AGENT_DIR/mac_daily_report.py >> $LOG_DIR/cron_report.log 2>&1
# 毎週火曜12時にBOOTH商品を更新（検索順位維持）
0 12 * * 2 $PYTHON $AGENT_DIR/mac_booth_refresh.py >> $LOG_DIR/cron_refresh.log 2>&1
CRON

crontab /tmp/crontab_clean
rm /tmp/crontab_clean
echo "  ✅ cronジョブ登録完了"
crontab -l | grep "agent-team" | while IFS= read -r line; do
  echo "  → $line"
done

echo "\n[3/3] 初回売上チェックを実行..."
$PYTHON "$AGENT_DIR/mac_check_sales.py"

echo "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ 自動化完了"
echo "  売上があればターミナル通知でお知らせします"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
