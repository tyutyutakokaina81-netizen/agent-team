#!/bin/zsh
# run_mac.sh — Mac ワンコマンド公開実行
# 使い方: zsh run_mac.sh
# ※ Chrome で note.com / x.com / studio.youtube.com にログイン済みであること

REPO="$HOME/agent-team"
cd "$REPO"

ok() { echo "  ✅ $1" }
ng() { echo "  ⚠️  $1" }

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  高岡アイ コンテンツ公開"
echo "  $(date '+%Y-%m-%d %H:%M')"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 最新コードに同期
echo "\n[0] コード同期..."
git fetch origin claude/add-claude-documentation-Wipf0 --quiet
git reset --hard origin/claude/add-claude-documentation-Wipf0 --quiet
ok "最新コード"

# note 公開（1本）
echo "\n[1] note 公開..."
if python3 auto_note_publish.py; then
  ok "note 公開完了"
else
  ng "note 公開失敗（Chromeでnote.comにログインしているか確認）"
fi

# X 投稿（1本）
echo "\n[2] X 投稿..."
if python3 auto_x_post.py; then
  ok "X 投稿完了"
else
  ng "X 投稿失敗（ChromeでX.comにログインしているか確認）"
fi

# YouTube アップロード（長尺 + Shorts）
echo "\n[3] YouTube アップロード..."
if python3 auto_youtube_upload.py; then
  ok "YouTube アップロード完了"
else
  ng "YouTube アップロード失敗（ChromeでYouTube Studioにログインしているか確認）"
fi

# アフィリエイト挿入（記事更新分）
echo "\n[4] アフィリエイト最適化..."
python3 auto_affiliate.py 2>/dev/null && ok "アフィリエイト挿入" || true

# 横断変換（新規公開記事から X + Shorts 自動生成）
echo "\n[5] コンテンツ横断変換..."
python3 auto_repurpose.py 2>/dev/null && ok "X投稿・Shorts台本 自動生成" || true

echo "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  完了！ $(date '+%H:%M')"
echo ""
echo "  確認:"
echo "  - note.com/dashboard → 公開済み記事を確認"
echo "  - x.com → 投稿を確認"
echo "  - studio.youtube.com → アップロード状況確認"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
