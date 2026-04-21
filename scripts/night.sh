#!/bin/bash
# 夜のワンコマンドルーティン
# 使い方: ./scripts/night.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_DIR"

echo ""
echo "========================================"
echo "🌙 夜のルーティン開始"
echo "$(date '+%Y-%m-%d %H:%M')"
echo "========================================"

# 1. 今日の最終レポート
echo ""
echo "📊 今日の実績"
python3 "$SCRIPT_DIR/daily_report.py"

# 2. ステータス更新モード
echo ""
echo "ステータスを更新する案件はありますか？"
echo "（受注・返信・失注など）"
echo "更新する場合は応募トラッカーを起動します (y/N)"
read -r ANSWER
if [[ "$ANSWER" = "y" ]] || [[ "$ANSWER" = "Y" ]]; then
    python3 "$SCRIPT_DIR/application_tracker.py"
fi

# 3. 明日のリマインド
echo ""
echo "========================================"
echo "📅 明日の最優先3つを書き出そう"
echo "========================================"
echo "（メモ帳でもいいから書いておく。"
echo "  朝に迷わず動き出せる）"
echo ""

# 4. 自動バックアップ
echo ""
echo "========================================"
echo "💾 Gitバックアップ"
echo "========================================"
"$SCRIPT_DIR/backup.sh"

echo ""
echo "========================================"
echo "✅ お疲れ様でした"
echo "明日も頑張ろう"
echo "========================================"
echo ""
