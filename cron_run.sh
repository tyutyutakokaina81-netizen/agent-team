#!/bin/bash
# agent-team 定期実行ラッパー（cron から呼ばれる）
REPO=/home/user/agent-team
cd $REPO
LOG="$REPO/logs/cron_$(date +%Y-%m-%d_%H%M).log"
mkdir -p "$REPO/logs"

echo "=== $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$LOG"

# 常に最新コードで実行
BRANCH=$(git -C "$REPO" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "claude/add-claude-documentation-Wipf0")
git -C "$REPO" fetch origin "$BRANCH" --quiet >> "$LOG" 2>&1
git -C "$REPO" reset --hard "origin/$BRANCH" --quiet >> "$LOG" 2>&1
echo "[git] $(git -C "$REPO" log --oneline -1)" >> "$LOG"

run() {
  echo "[$(date +%H:%M)] $1" >> "$LOG"
  python3 "$REPO/$2" >> "$LOG" 2>&1 && echo "  OK" >> "$LOG" || echo "  NG" >> "$LOG"
}

# 常時実行（コンテンツ生成・評価）
run "写真取得"           auto_wikimedia_photos.py
run "アフィリエイト"     auto_affiliate.py
run "横断変換"           auto_repurpose.py
run "コンテンツループ"   auto_content_loop.py
run "Shorts生成"         auto_youtube_shorts.py
run "動画生成"           auto_youtube_produce.py

# X API直接投稿（認証情報があればChrome不要でサーバーから投稿）
run "X投稿(API)"         auto_x_api_post.py

run "自己評価"           auto_self_eval.py

echo "=== 完了 $(date '+%H:%M:%S') ===" >> "$LOG"
