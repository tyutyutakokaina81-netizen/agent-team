#!/bin/bash
# agent-team 定期実行ラッパー（cron から呼ばれる）
REPO=/home/user/agent-team
cd $REPO
LOG="$REPO/logs/cron_$(date +%Y-%m-%d_%H%M).log"
mkdir -p "$REPO/logs"

echo "=== $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$LOG"

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
run "自己評価"           auto_self_eval.py

echo "=== 完了 $(date '+%H:%M:%S') ===" >> "$LOG"
