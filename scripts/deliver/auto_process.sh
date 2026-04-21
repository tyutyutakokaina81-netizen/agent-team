#!/bin/bash
# 受注内容 自動処理パイプライン
# クリップボードの受注メッセージを精査→判定→アクション提案
#
# 使い方:
#   # クリップボードにコピーしてから
#   ./scripts/deliver/auto_process.sh
#
# 動作：
# 1. クリップボードから受注内容を取得
# 2. scrutinize_order.py で自動精査
# 3. 判定に応じて：
#    - accept → 受注セットアップ案内
#    - review → 条件確認返信案内
#    - reject → 辞退返信案内

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_DIR"

echo "========================================"
echo "🤖 受注自動処理パイプライン"
echo "========================================"

# クリップボードの中身を確認
if ! command -v pbpaste &>/dev/null; then
    echo "❌ pbpaste が使えません（Mac以外）"
    echo "   scrutinize_order.py を対話式で使ってください："
    echo "   python3 scripts/deliver/scrutinize_order.py"
    exit 1
fi

CLIPBOARD_LEN=$(pbpaste | wc -c | tr -d ' ')
if [[ "$CLIPBOARD_LEN" -lt 20 ]]; then
    echo "❌ クリップボードが空または短すぎます（${CLIPBOARD_LEN}文字）"
    echo "   受注内容をコピーしてから再実行してください"
    exit 1
fi

echo "📋 クリップボード検出: ${CLIPBOARD_LEN}文字"
echo ""

# 精査実行
python3 "$SCRIPT_DIR/scrutinize_order.py" --clipboard

echo ""
echo "========================================"
echo "次のステップ:"
echo "========================================"
echo "  承認→受注セットアップ:  python3 scripts/deliver/new_job.py"
echo "  拒否→応募ログに記録:    python3 scripts/application_tracker.py"
echo ""
