#!/bin/zsh
# note自動公開ヘルパー：初回セットアップ（一度だけ実行）
set -e

echo "📦 Python依存をインストール..."
python3 -m pip install --upgrade playwright

echo "🌐 Chromiumをダウンロード（初回のみ・数百MB）..."
python3 -m playwright install chromium

echo ""
echo "✅ セットアップ完了。次にやること:"
echo ""
echo "  1) noteへの初回ログイン（一度だけ）:"
echo "     python3 publish_to_note.py --login"
echo ""
echo "  2) 公開:"
echo "     python3 publish_to_note.py --photos ~/Pictures/note/2026-05-28/"
echo ""
