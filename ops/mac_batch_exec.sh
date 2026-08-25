#!/bin/bash
set -e

echo "【ステップ1】リポジトリ更新 + 環境確認"
cd ~/agent-team-run
git fetch origin main && git reset --hard origin/main
echo "✅ main最新化完了"

echo ""
echo "【ステップ2】8/17の5本を公開（publish_today.sh）"
bash ops/publish_today.sh --all
echo "✅ 8/17の5本を公開完了"

echo ""
echo "【ステップ3】有料note¥500を下書き作成（確認用）"
~/.note_venv/bin/python CDO/outputs/note_publisher/publish_paid_note.py \
  --article "CMO/outputs/2026-08-20_有料note_AIに会社を運営させた3か月_161本公開して売上0円.md" \
  --price 500
echo "✅ 有料note下書き作成完了"
echo "🔍 ↑のURLをコピーしてください（次のステップで必要）"

echo ""
echo "【ステップ4】有料note URL入力"
read -p "有料note の公開URL (https://note.com/...) を入力: " PAID_URL

echo ""
echo "【ステップ5】入口記事のURLを置換"
sed -i "" "s|<<有料noteURL>>|$PAID_URL|g" \
  CMO/outputs/2026-08-21_note記事_AIは一度もやめましょうと言わなかった.md
echo "✅ URL置換完了: $PAID_URL"

echo ""
echo "【ステップ6】入口記事を公開"
~/.note_venv/bin/python CDO/outputs/note_publisher/publish_to_note.py \
  --article "CMO/outputs/2026-08-21_note記事_AIは一度もやめましょうと言わなかった.md"
echo "✅ 入口記事公開完了"

echo ""
echo "================================"
echo "✅ 全タスク完了！"
echo "================================"
echo ""
echo "【報告】以下の内容で ops/outbox へ報告:"
echo "- 8/17の5本公開完了"
echo "- 有料note¥500公開URL: $PAID_URL"
echo "- 入口記事公開完了"
