#!/bin/bash
# agent-team 定期実行ラッパー（cron から呼ばれる）
REPO=/home/user/agent-team
cd $REPO
LOG="$REPO/logs/cron_$(date +%Y-%m-%d_%H%M).log"
mkdir -p "$REPO/logs"

# .env 読み込み（X API等の認証情報）
if [ -f "$REPO/.env" ]; then
  set -a; source "$REPO/.env"; set +a
fi

echo "=== $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$LOG"

# 常に最新コードで実行
BRANCH=$(git -C "$REPO" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "claude/add-claude-documentation-Wipf0")
git -C "$REPO" fetch origin "$BRANCH" --quiet >> "$LOG" 2>&1
git -C "$REPO" reset --hard "origin/$BRANCH" --quiet >> "$LOG" 2>&1
echo "[git] $(git -C "$REPO" log --oneline -1)" >> "$LOG"

# ── ディスパッチャー経由で全タスクを実行 ──────────────────
# 月曜のみ weekly モード（全エージェント+稟議+統括）
# それ以外は daily モード（優先度1-2のみ）
if [ "$(date +%u)" = "1" ]; then
  MODE="weekly"
else
  MODE="daily"
fi

echo "[$(date +%H:%M)] dispatch[$MODE]" >> "$LOG"
python3 "$REPO/agent_dispatch.py" "$MODE" >> "$LOG" 2>&1 \
  && echo "  OK" >> "$LOG" || echo "  NG" >> "$LOG"

# X API 直接投稿（認証情報があればサーバーから投稿）
echo "[$(date +%H:%M)] X投稿(API)" >> "$LOG"
python3 "$REPO/auto_x_api_post.py" >> "$LOG" 2>&1 \
  && echo "  OK" >> "$LOG" || echo "  NG" >> "$LOG"

echo "=== 完了 $(date '+%H:%M:%S') ===" >> "$LOG"
