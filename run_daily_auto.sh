#!/bin/zsh
# run_daily_auto.sh — 毎朝9時・毎夕20時 自動実行
# 生成→公開→計測→改善→ループ の永続サイクル

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
    echo "  ⚠️  ${label}失敗" | tee -a "$LOG"
  fi
}

# 最新コード取得
git fetch origin claude/add-claude-documentation-Wipf0 --quiet
git reset --hard origin/claude/add-claude-documentation-Wipf0 --quiet

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG"
echo "  自動実行 $(date '+%Y-%m-%d %H:%M')" | tee -a "$LOG"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG"

HOUR=$(date +%H)

if [ "$HOUR" -lt "15" ]; then
  # ━━━━ 朝の実行（9時）━━━━━━━━━━━━━━━━━━━━━━━━━━

  # ① 写真素材取得（動画・記事の品質向上）
  run "Wikimedia写真取得" auto_wikimedia_photos.py

  # ② アフィリエイトリンク挿入（収益化）
  run "アフィリエイト挿入" auto_affiliate.py

  # ③ note記事 2本公開
  run "note公開①" auto_note_publish.py
  run "note公開②" auto_note_publish.py

  # ④ 公開記事をX投稿・Shorts台本に横断変換（1本の記事から3プラットフォーム分）
  run "コンテンツ横断変換" auto_repurpose.py

  # ⑤ X投稿 2本（朝）
  run "X投稿①" auto_x_post.py
  run "X投稿②" auto_x_post.py

  # ⑥ CW案件 新着検索→自動応募
  run "CW応募" auto_d_apply.py

  # ⑦ CWサービス出品
  run "CW出品" auto_a_service.py

  # ⑧ BOOTH出品
  run "BOOTH出品" mac_booth_publish.py

  # ⑨ YouTube（月・木）: Shorts → 長尺 → アップロード（長尺+Shorts両方）
  DOW=$(date +%u)
  if [ "$DOW" = "1" ] || [ "$DOW" = "4" ]; then
    run "YouTubeShorts生成" auto_youtube_shorts.py
    run "YouTube動画生成" auto_youtube_produce.py
    run "YouTubeアップロード（長尺+Shorts）" auto_youtube_upload.py
  fi

else
  # ━━━━ 夕方の実行（20時）━━━━━━━━━━━━━━━━━━━━━━━

  # X投稿 1本（夕方）
  run "X投稿（夕）" auto_x_post.py

  # コンテンツキュー自動補充（在庫切れ防止）
  run "コンテンツ自動生成ループ" auto_content_loop.py

  # KPI計測（YouTube/note/X の数値を記録）
  run "KPI自動計測" auto_kpi_tracker.py

  # ━━━━ 自己評価＋改善ループ ━━━━━━━━━━━━━━━━━━━━━━
  # スコアが80点未満なら自動で改善スクリプトを実行
  run "自己評価ループ" auto_self_eval.py

fi

echo "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG"
echo "  完了 $(date '+%H:%M')" | tee -a "$LOG"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG"
