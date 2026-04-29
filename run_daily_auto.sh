#!/bin/zsh
# run_daily_auto.sh — 毎朝の自動実行マスター（note → X → D → A → B）
# 実行: zsh run_daily_auto.sh
# 自動実行: launchctl load ~/Library/LaunchAgents/com.agent-team.daily.plist

REPO="$HOME/agent-team"
LOG="$REPO/logs/daily_auto_$(date +%Y-%m-%d).log"
mkdir -p "$REPO/logs"

cd "$REPO"

run() {
  local label="$1"; shift
  echo "\n[$label] $*..." | tee -a "$LOG"
  if python3 "$REPO/$@" 2>&1 | tee -a "$LOG"; then
    echo "  ✅ ${label}完了" | tee -a "$LOG"
  else
    echo "  ⚠️  ${label}失敗（ログ: $LOG）" | tee -a "$LOG"
  fi
}

# 最新コードを取得
git fetch origin claude/add-claude-documentation-Wipf0
git reset --hard origin/claude/add-claude-documentation-Wipf0

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG"
echo "  日次自動実行 $(date '+%Y-%m-%d %H:%M')" | tee -a "$LOG"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG"

# ── note記事 公開（初回のみ: URLが未保存なら実行）────
if [ ! -f "$REPO/.sessions/note_article_urls.json" ]; then
  run "note公開" auto_note_publish.py
fi

# ── X 今日の1投稿 ────────────────────────────
run "X投稿" auto_x_post.py

# ── D: CW案件 5件自動応募 ──────────────────────
run "D" auto_d_apply.py

# ── A: SEOサービス出品 ────────────────────────
run "A" auto_a_service.py

echo "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG"
echo "  完了。SNS DM（B）は半自動:" | tee -a "$LOG"
echo "  python3 $REPO/auto_b_dm.py" | tee -a "$LOG"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG"

# ── YouTube動画生成（月・木のみ） ─────────────────────
DOW=$(date +%u)  # 1=月 〜 7=日
if [ "$DOW" = "1" ] || [ "$DOW" = "4" ]; then
  run "YouTube動画生成" auto_youtube_produce.py
  run "YouTubeアップロード" auto_youtube_upload.py
fi

# B は半自動（Instagram規約上、完全自動は規約違反）
if [ -t 0 ]; then
  echo "\n[B] SNS DM 起動（今日の3件）..."
  python3 "$REPO/auto_b_dm.py"
fi
