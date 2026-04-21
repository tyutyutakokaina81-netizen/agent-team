#!/bin/bash
# 朝のワンコマンドルーティン
# 使い方: ./scripts/morning.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_DIR"

echo ""
echo "========================================"
echo "🌅 朝のルーティン開始"
echo "$(date '+%Y-%m-%d %H:%M')"
echo "========================================"

# 1. 昨日の進捗を表示
echo ""
echo "📊 昨日の進捗"
python3 "$SCRIPT_DIR/daily_report.py"

# 2. 今日やることをリマインド
echo ""
echo "========================================"
echo "🎯 今日やること"
echo "========================================"
echo "  □ 応募3件送信（CSO/outputs/案件リスト_応募文.md）"
echo "  □ 返信チェック＆対応（返信テンプレ集.md）"
echo "  □ 1つでも進捗を記録する"
echo ""

# 3. 応募記録モードを聞く
echo "応募を記録しますか？ (y/N)"
read -r ANSWER
if [[ "$ANSWER" = "y" ]] || [[ "$ANSWER" = "Y" ]]; then
    python3 "$SCRIPT_DIR/application_tracker.py"
fi

# 4. 自動バックアップ
echo ""
echo "========================================"
echo "💾 Gitバックアップ"
echo "========================================"
"$SCRIPT_DIR/backup.sh"

echo ""
echo "========================================"
echo "✅ 朝のルーティン完了"
echo "今日もがんばろう！"
echo "========================================"
echo ""
