#!/bin/zsh
# mac_full_auto.sh — 完全自動化セットアップ（一発実行）
# 実行: zsh ~/agent-team/mac_full_auto.sh

set -e
AGENT_DIR="$HOME/agent-team"
PYTHON=$(which python3)
LOG_DIR="$AGENT_DIR/logs"
mkdir -p "$LOG_DIR"

echo "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  完全自動化セットアップ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── パッケージ ──────────────────────────────
echo "\n[1/4] パッケージインストール..."
$PYTHON -m pip install requests browser-cookie3 playwright openpyxl \
  --break-system-packages -q 2>/dev/null || \
$PYTHON -m pip install requests browser-cookie3 playwright openpyxl -q 2>/dev/null || true
$PYTHON -m playwright install chromium --with-deps 2>/dev/null || true
echo "  ✅ OK"

# ── BOOTHクッキー取得＆出品 ────────────────
echo "\n[2/4] BOOTH: クッキー取得→出品..."
if [ ! -f "$AGENT_DIR/.sessions/booth_session.json" ]; then
  $PYTHON "$AGENT_DIR/mac_auto_cookie.py" && echo "  ✅ BOOTH出品完了" || echo "  ⚠️  BOOTH出品スキップ（後で再実行）"
else
  echo "  ✅ BOOTHセッション確認済み"
fi

# ── cron登録 ───────────────────────────────
echo "\n[3/4] 全自動スケジュール登録..."

# 既存のagent-team cronを削除
crontab -l 2>/dev/null | grep -v "agent-team" > /tmp/cron_base || true

cat >> /tmp/cron_base << CRON
# ━━━ agent-team 全自動スケジュール ━━━
# BOOTH売上チェック（30分ごと・クッキー自動更新）
*/30 * * * * $PYTHON $AGENT_DIR/mac_check_sales.py >> $LOG_DIR/sales.log 2>&1
# 毎朝8時: 日次レポート通知
0 8 * * * $PYTHON $AGENT_DIR/mac_daily_report.py >> $LOG_DIR/report.log 2>&1
# 毎朝9時: Lancers/CW案件検索→評価→自動応募
0 9 * * 1-5 cd $AGENT_DIR && AUTO_APPLY=1 AUTO_APPLY_THRESHOLD=80 $PYTHON $AGENT_DIR/mac_pipeline.py search >> $LOG_DIR/pipeline.log 2>&1
# 毎夕18時: Lancers/CW案件検索→評価→自動応募（2回目）
0 18 * * 1-5 cd $AGENT_DIR && AUTO_APPLY=1 AUTO_APPLY_THRESHOLD=80 $PYTHON $AGENT_DIR/mac_pipeline.py search >> $LOG_DIR/pipeline.log 2>&1
# 毎週火曜12時: BOOTH商品更新（検索順位維持）
0 12 * * 2 $PYTHON $AGENT_DIR/mac_booth_refresh.py >> $LOG_DIR/refresh.log 2>&1
# 毎週日曜22時: BOOTHクッキー更新
0 22 * * 0 $PYTHON $AGENT_DIR/mac_auto_cookie.py >> $LOG_DIR/cookie.log 2>&1
CRON

crontab /tmp/cron_base
rm /tmp/cron_base
echo "  ✅ スケジュール登録完了"
crontab -l | grep "agent-team" | sed 's/^/  → /'

# ── 初回チェック実行 ────────────────────────
echo "\n[4/4] 動作確認..."
$PYTHON "$AGENT_DIR/mac_check_sales.py"
echo "  ✅ 完了"

echo "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ 完全自動化セットアップ完了"
echo ""
echo "  自動で動くもの:"
echo "    - BOOTH売上監視（30分ごと）"
echo "    - Lancers/CW案件応募（毎日 9時・18時）"
echo "    - 日次レポート（毎朝 8時）"
echo "    - BOOTH商品更新（毎週火曜）"
echo "    - クッキー自動更新（毎週日曜）"
echo ""
echo "  あなたが必要な操作:"
echo "    - BOOTH: 振込口座登録（通知が来たら1回だけ）"
echo "    - Lancers: 初回ログイン（次のステップ）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
