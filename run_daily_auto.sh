#!/bin/zsh
# run_daily_auto.sh — 毎朝・毎晩の自動実行マスター
# 朝9時: git pull → note公開×2 → X投稿×2 → D → A → YouTube(月木)
# 夕20時: X投稿×1（同スクリプト）

REPO="$HOME/agent-team"
LOG="$REPO/logs/daily_auto_$(date +%Y-%m-%d_%H%M).log"
mkdir -p "$REPO/logs"
cd "$REPO"

run() {
  local label="$1"; shift
  echo "\n[$label] 開始..." | tee -a "$LOG"
  if python3 "$REPO/$@" 2>&1 | tee -a "$LOG"; then
    echo "  ✅ ${label}完了" | tee -a "$LOG"
  else
    echo "  ⚠️  ${label}失敗（ログ: $LOG）" | tee -a "$LOG"
  fi
}

# 最新コード取得
git fetch origin claude/add-claude-documentation-Wipf0 --quiet
git reset --hard origin/claude/add-claude-documentation-Wipf0 --quiet

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG"
echo "  日次自動実行 $(date '+%Y-%m-%d %H:%M')" | tee -a "$LOG"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG"

HOUR=$(date +%H)

if [ "$HOUR" -lt "15" ]; then
  # ── 朝の実行 ────────────────────────────────────

  # note記事 2本公開（1日2本で7本を4日で出し切る）
  run "note公開①" auto_note_publish.py
  run "note公開②" auto_note_publish.py

  # X投稿 2本（朝）
  run "X投稿①" auto_x_post.py
  run "X投稿②" auto_x_post.py

  # CW案件 新着検索→自動応募
  run "CW応募" auto_d_apply.py

  # CWサービス出品
  run "CW出品" auto_a_service.py

  # BOOTH出品（vol8）
  run "BOOTH" mac_booth_publish.py

  # YouTube動画生成（月・木のみ）
  DOW=$(date +%u)
  if [ "$DOW" = "1" ] || [ "$DOW" = "4" ]; then
    run "YouTube動画生成" auto_youtube_produce.py
    run "YouTubeアップロード" auto_youtube_upload.py
  fi

else
  # ── 夕方の実行（20時）────────────────────────────

  # X投稿 1本（夕方）
  run "X投稿（夕）" auto_x_post.py

fi

echo "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG"
echo "  完了 $(date '+%H:%M')" | tee -a "$LOG"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG"
