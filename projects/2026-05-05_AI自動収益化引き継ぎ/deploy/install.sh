#!/bin/zsh
# ai-auto セットアップスクリプト（macOS / Linux 兼用）
# 使い方: bash install.sh

set -e

SOURCE="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/ai-auto"

echo "============================================"
echo "  ai-auto セットアップ開始"
echo "  source: $SOURCE"
echo "  dest:   $DEST"
echo "============================================"

# 1) ディレクトリ作成
mkdir -p "$DEST/prompts" "$DEST/logs" "$DEST/outputs"

# 2) ファイルコピー
cp "$SOURCE"/*.py "$DEST/"
cp "$SOURCE"/*.sh "$DEST/"
cp "$SOURCE"/requirements.txt "$DEST/"
cp "$SOURCE"/README.md "$DEST/"
cp "$SOURCE"/iphone_shortcuts.md "$DEST/"
cp "$SOURCE"/com.aiauto.server.plist "$DEST/"
cp "$SOURCE"/.gitignore "$DEST/"
cp "$SOURCE"/prompts/* "$DEST/prompts/"

# 3) .env が無ければ env.template からコピー
if [ ! -f "$DEST/.env" ]; then
  cp "$SOURCE/env.template" "$DEST/.env"
  echo "→ $DEST/.env を新規作成（DRY_RUN=1 のまま）"
else
  echo "→ $DEST/.env は既存のため保持"
fi

# 4) 実行権限
chmod +x "$DEST"/*.sh

# 5) Python 依存
echo ""
echo "→ Python 依存をインストール..."
pip3 install --user -r "$DEST/requirements.txt"

# 6) Playwright Chromium
echo ""
echo "→ Playwright Chromium をインストール..."
python3 -m playwright install chromium

# 7) DRY_RUN で生成スクリプト動作確認
echo ""
echo "→ DRY_RUN で生成スクリプトを試運転..."
cd "$DEST"
DRY_RUN=1 python3 generate_daily_outputs.py
DRY_RUN=1 python3 auto_schedule.py

echo ""
echo "============================================"
echo "  ✓ セットアップ完了"
echo "============================================"
echo ""
echo "次のステップ："
echo ""
echo "  1) $DEST/.env を編集（必要なら REDDIT_* を設定）"
echo ""
echo "  2) ブラウザプロファイル初期化（手動ログイン・1回のみ）："
echo "     cd $DEST"
echo "     python3 -c \"from _browser import open_browser; "
echo "     ctx = open_browser.__wrapped__(False); "
echo "     # ↑ DRY_RUN=0 で実行する場合のみ。手順は README.md 参照\""
echo ""
echo "  3) cron 登録（crontab -e に以下2行）："
echo "     0 7 * * * /bin/zsh -lc 'cd \$HOME/ai-auto && ./run.sh'"
echo "     0 * * * * /bin/zsh -lc 'cd \$HOME/ai-auto && python3 dispatcher.py >> logs/dispatcher.log 2>&1'"
echo ""
echo "  4) 7日 DRY_RUN で観察 → Reddit から段階的に本番化"
echo ""
echo "  5) iPhone から確認・操作したい場合："
echo "     - .env に AI_AUTO_TOKEN=<32文字以上> を設定"
echo "     - $DEST/run_server.sh で API サーバー起動"
echo "     - 詳細手順は $DEST/iphone_shortcuts.md 参照"
echo "     - mac 常駐させるなら $DEST/com.aiauto.server.plist を ~/Library/LaunchAgents/ へ"
echo ""
echo "詳細：$DEST/README.md  /  iPhone対応：$DEST/iphone_shortcuts.md"
