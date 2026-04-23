#!/bin/zsh
# 新商品3件をバックグラウンドで自動出品
# ターミナルを閉じても続行される

REPO=~/agent-team
LOG=$REPO/logs/booth_publish_new.log

cd "$REPO"
mkdir -p "$REPO/logs"

# 最新コードを取得（diverge しても強制同期）
git fetch origin claude/add-claude-documentation-Wipf0
git reset --hard origin/claude/add-claude-documentation-Wipf0

# バックグラウンドで実行（ターミナルを閉じてもOK）
nohup python3 "$REPO/mac_booth_publish.py" > "$LOG" 2>&1 &
PID=$!

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  バックグラウンド出品開始 (PID: $PID)"
echo "  ターミナルを閉じて出かけてOKです"
echo ""
echo "  ログ確認（戻ってから）:"
echo "  cat ~/agent-team/logs/booth_publish_new.log"
echo ""
echo "  出品確認:"
echo "  https://manage.booth.pm/items"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
