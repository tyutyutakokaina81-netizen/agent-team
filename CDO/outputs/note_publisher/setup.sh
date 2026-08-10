#!/bin/zsh
# note自動公開ヘルパー：初回セットアップ（一度だけ実行）
# 2026-08-16 PEP 668(externally-managed-environment)対応：Homebrew等のPythonは
#   `pip install` を既定でブロックする。順に①通常②--user --break-system-packages
#   ③--break-system-packages と試し、通ったものを採用する（set -e下でも||で継続）。
set -e

echo "📦 Python依存をインストール（PEP668対応・自動フォールバック）..."
python3 -m pip install --upgrade playwright \
  || python3 -m pip install --user --break-system-packages --upgrade playwright \
  || python3 -m pip install --break-system-packages --upgrade playwright \
  || { echo "✗ playwrightのインストールに失敗。Homebrewなら 'brew install python' 後に再実行、または 'pipx install playwright' をお試しください。"; exit 1; }

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
