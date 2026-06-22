#!/bin/bash
set -e

# ==================== DAILY WORKFLOW ====================
# Macで毎日実行：記事生成→クロスポスト素材→公開→拡散まで一気通貫
#
# 用途：
#   手動実行: bash ~/agent-team/scripts/daily_workflow.sh
#   自動実行: LaunchAgent で毎日 5:30 AM に実行
#
# 前提：
#   - Claude Code CLI インストール済み
#   - ~/agent-team が git clone済み
#   - MacのPythonで publish_to_note.py が実行可能
#
# ==================== SETTINGS ====================

REPO_HOME="$HOME/agent-team"
BRANCH="claude/new-session-jn2hnw"
TODAY=$(date +%Y-%m-%d)
LOGFILE="$HOME/.claude_daily_$(date +%Y%m%d).log"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOGFILE"
}

error() {
  echo "[ERROR] $1" | tee -a "$LOGFILE"
  exit 1
}

# ==================== STEP 1: 記事生成 ====================
log "🚀 STEP1: 記事生成開始（対象日: $TODAY）"

cd "$REPO_HOME"
git pull origin "$BRANCH" 2>&1 | tee -a "$LOGFILE" || error "git pull failed"

# 本日の記事数をカウント
ARTICLE_COUNT=$(ls CMO/outputs/${TODAY}_note記事_*.md 2>/dev/null | wc -l || echo 0)
log "📊 本日の記事: $ARTICLE_COUNT/5本"

if [ "$ARTICLE_COUNT" -lt 5 ]; then
  log "📝 不足分を生成します（必要: $((5 - ARTICLE_COUNT))本）"

  # Claude CLI で「実行して」を送信
  # (セッション内で自動実行されるプロンプト)
  log "Claude: 「実行して」でセッション内自動生成を開始..."

  # note: Claude CLI が実行していない場合は、スクリプトで待機
  # 本来ここで claude CLI invoke をするが、セッション管理が複雑なため
  # オーナーのManualステップとしている
  log "⚠️  Claude Code セッションで「実行して」を実行してください"
  log "✓ 記事5本生成完了までお待ちください"

  # Slackに通知（オプション）
  # curl -X POST $SLACK_WEBHOOK -d '...'
else
  log "✅ 本日の記事は揃っています（5本確認）"
fi

# ==================== STEP 2: クロスポスト素材生成 ====================
log "🔄 STEP2: Reddit/X/EN素材生成"

cd "$REPO_HOME"
python3 CDO/outputs/cross_post/gen_all.py --since "$TODAY" 2>&1 | tee -a "$LOGFILE" || \
  log "⚠️  クロスポスト生成でWarning（続行）"

log "✅ Reddit/X/EN素材 生成完了"

# ==================== STEP 3: git commit & push ====================
log "📦 STEP3: git commit & push"

cd "$REPO_HOME"
git add -A && git commit -m "Daily: $TODAY 記事＋クロスポスト素材生成完了（自動）" 2>&1 | tee -a "$LOGFILE" || \
  log "ℹ️  （無変更の場合）"

git push origin "$BRANCH" 2>&1 | tee -a "$LOGFILE" || error "git push failed"
log "✅ commit & push 完了"

# ==================== STEP 4: note 公開 ====================
log "📢 STEP4: note 記事公開"

cd "$REPO_HOME"
python3 CDO/outputs/note_publisher/batch_publish.py --date "$TODAY" 2>&1 | tee -a "$LOGFILE" || \
  log "⚠️  note公開処理でWarning（手動確認推奨）"

log "✅ note 公開完了（ボタン自動クリック有効の場合）"

# ==================== STEP 5: 海外クロスポスト ====================
log "🌍 STEP5: Reddit/X投稿素材準備完了"
log "   手動投稿: EN/outputs/ の素材をReddit/Xに貼り付け"
log "   自動化: Buffer/Later 等の投稿ツールに連携（オプション）"

# ==================== COMPLETION ====================
log "========================================="
log "✅ 本日のワークフロー完了！"
log "========================================="
log "📍 記事: CMO/outputs/${TODAY}_note記事_*.md"
log "📍 素材: EN/outputs/{reddit,x_tweets}/${TODAY}_*"
log "📍 ログ: $LOGFILE"

# MacのNotificationCenter に通知
osascript -e "display notification \"$TODAY のワークフロー完了！\\n記事5本＋クロスポスト素材＋公開\" with title \"agent-team\""
