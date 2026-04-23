#!/bin/zsh
# run_daily_auto.sh — 毎朝の自動実行マスター（D → A → B）
# 実行: zsh run_daily_auto.sh
# 自動実行: launchctl load ~/Library/LaunchAgents/com.agent-team.daily.plist

set -e
REPO="$HOME/agent-team"
LOG="$REPO/logs/daily_auto_$(date +%Y-%m-%d).log"
mkdir -p "$REPO/logs"

cd "$REPO"

# 最新コードを取得
git fetch origin claude/add-claude-documentation-Wipf0
git reset --hard origin/claude/add-claude-documentation-Wipf0

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG"
echo "  日次自動実行 $(date '+%Y-%m-%d %H:%M')" | tee -a "$LOG"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG"

# ── D: CW案件 5件自動応募 ──────────────────────
echo "\n[D] CW案件自動応募..." | tee -a "$LOG"
python3 "$REPO/auto_d_apply.py" 2>&1 | tee -a "$LOG" && \
  echo "  ✅ D完了" | tee -a "$LOG" || \
  echo "  ⚠️  D失敗（ログ確認: $LOG）" | tee -a "$LOG"

# ── A: SEOサービス出品 ────────────────────────
echo "\n[A] SEOサービス出品..." | tee -a "$LOG"
python3 "$REPO/auto_a_service.py" 2>&1 | tee -a "$LOG" && \
  echo "  ✅ A完了" | tee -a "$LOG" || \
  echo "  ⚠️  A失敗（ログ確認: $LOG）" | tee -a "$LOG"

echo "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG"
echo "  D・A 完了。B（SNS DM）は半自動です。" | tee -a "$LOG"
echo "  python3 $REPO/auto_b_dm.py" | tee -a "$LOG"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG"

# B は半自動（Instagram規約上、完全自動は規約違反）
# ターミナルが開いている場合のみ実行
if [ -t 0 ]; then
  echo "\n[B] SNS DM 起動（今日の3件）..."
  python3 "$REPO/auto_b_dm.py"
else
  echo "\n[B] SNS DMは手動実行: python3 $REPO/auto_b_dm.py" | tee -a "$LOG"
fi
