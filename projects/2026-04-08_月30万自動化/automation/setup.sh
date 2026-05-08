#!/bin/bash
# 公開自動化のセットアップスクリプト（macOS / Linux 両対応）
# 使い方:
#   bash projects/2026-04-08_月30万自動化/automation/setup.sh

set -e

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
AUTO_DIR="$REPO_ROOT/projects/2026-04-08_月30万自動化/automation"

echo "═══════════════════════════════════════════"
echo "  公開自動化セットアップ"
echo "═══════════════════════════════════════════"
echo "REPO_ROOT: $REPO_ROOT"
echo "AUTO_DIR : $AUTO_DIR"
echo ""

# 1. venv 作成（PEP 668 対策）
cd "$AUTO_DIR"
if [ ! -d .venv ]; then
  echo "[1/3] venv を作成..."
  python3 -m venv .venv
else
  echo "[1/3] venv 既存（スキップ）"
fi

# 2. 依存インストール
echo "[2/3] playwright + openpyxl をインストール..."
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q "playwright>=1.40.0" "openpyxl>=3.1.0"

# 3. Chromium インストール
echo "[3/3] Chromium をインストール..."
python3 -m playwright install chromium

echo ""
echo "═══════════════════════════════════════════"
echo "  ✅ セットアップ完了"
echo "═══════════════════════════════════════════"
echo ""
echo "次のコマンドを実行してください："
echo ""
echo "  cd $AUTO_DIR"
echo "  source .venv/bin/activate"
echo "  python3 00_session_setup.py     # 1 回だけ・3 分"
echo "  python3 run_all.py              # 5〜10 分で公開＋告知"
echo ""
