#!/bin/zsh
# note自動公開ヘルパー：初回セットアップ（一度だけ実行）
# 2026-08-18 venv優先に変更：Homebrew/Python3.14 の PEP668(externally-managed) を根本回避。
#   専用venv ~/.note_venv を作り、そこに playwright + chromium を入れる（PEP668に一切触れない）。
#   venvが作れない環境では system pip に --break-system-packages でフォールバック。
#   ★publish_today.sh / cowork_run.sh は ~/.note_venv/bin/python があれば自動でそれを使う。
set -e
VENV="$HOME/.note_venv"

echo "📦 専用venvを作成/更新します（$VENV・PEP668安全）..."
python3 -m venv "$VENV" 2>/dev/null || true

PYOK=""
if [ -x "$VENV/bin/python" ]; then
  "$VENV/bin/python" -m pip install --upgrade pip >/dev/null 2>&1 || true
  if "$VENV/bin/python" -m pip install --upgrade playwright; then
    echo "🌐 Chromiumをダウンロード（初回のみ・数百MB）..."
    "$VENV/bin/python" -m playwright install chromium && PYOK=1
  fi
fi

if [ -z "$PYOK" ]; then
  echo "⚠️ venv経路が使えないため system pip にフォールバック（PEP668対応）..."
  python3 -m pip install --upgrade playwright \
    || python3 -m pip install --user --break-system-packages --upgrade playwright \
    || python3 -m pip install --break-system-packages --upgrade playwright \
    || { echo "✗ playwright導入に失敗。'brew install python' 後に再実行、または 'pipx install playwright' をお試しください。"; exit 1; }
  python3 -m playwright install chromium
fi

echo ""
echo "✅ セットアップ完了。"
if [ -n "$PYOK" ]; then echo "   使用Python: $VENV/bin/python（publish_today.sh / cowork_run.sh が自動で使用）"; fi
echo ""
echo "  次にやること（~/agent-team-run で）:"
echo "   1) 無料の溜まり分を公開:  bash ops/publish_today.sh --all"
echo "   2) 有料記事を公開（例）:"
echo "      \${PY:-python3} CDO/outputs/note_publisher/publish_paid_note.py --article \"CMO/outputs/<有料md>\" --price 300 --publish"
echo "      ※ venv使用時は PY=$VENV/bin/python を頭に付ける"
echo ""
