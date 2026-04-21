#!/bin/bash
# ダッシュボード表示専用スクリプト
# 最新データでダッシュボードを生成してブラウザで開く
# 使い方: ./scripts/open_dashboard.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

# 最新データでダッシュボードを生成
python3 "$SCRIPT_DIR/dashboard.py"

# ブラウザで開く
if command -v open >/dev/null 2>&1; then
    open "$SCRIPT_DIR/dashboard.html"
    echo "✅ ブラウザでダッシュボードを開きました"
else
    echo "⚠️  open コマンド非対応。手動でブラウザ開いて："
    echo "   $SCRIPT_DIR/dashboard.html"
fi
