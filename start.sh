#!/bin/zsh
# ================================================================
# start.sh — パイプライン 全自動起動スクリプト
# 使い方: ./start.sh
# ================================================================
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
PIPELINE_DIR="$REPO_DIR/projects/2026-04-08_月30万自動化/D_エクセル入力スクレイピング/pipeline"

# .env 読み込み
if [[ -f "$PIPELINE_DIR/.env" ]]; then
  export $(grep -v '^#' "$PIPELINE_DIR/.env" | xargs)
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🤖 パイプライン自動起動"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 依存ライブラリ確認
echo "\n[1/4] 依存ライブラリ確認..."
cd "$PIPELINE_DIR"
python3 -c "import playwright" 2>/dev/null || {
  echo "  playwright をインストールします..."
  pip3 install -r requirements.txt -q
  playwright install chromium --quiet
}
python3 -c "import openpyxl" 2>/dev/null || pip3 install openpyxl -q
echo "  ✅ 依存ライブラリ OK"

# セッション確認
echo "\n[2/4] ログインセッション確認..."
SESSION_DIR="$REPO_DIR/projects/2026-04-08_月30万自動化/D_エクセル入力スクレイピング/.sessions"
CW_SESSION="$SESSION_DIR/crowdworks_session.json"
LC_SESSION="$SESSION_DIR/lancers_session.json"

if [[ ! -f "$CW_SESSION" ]] && [[ ! -f "$LC_SESSION" ]]; then
  echo ""
  echo "  ⚠️  ログインセッションが見つかりません"
  echo "  以下を実行してください（1回だけ）:"
  echo ""
  echo "    cd $PIPELINE_DIR"
  echo "    python3 00_session_setup.py"
  echo ""
  exit 1
fi

[[ -f "$CW_SESSION" ]] && echo "  ✅ CrowdWorks: セッションあり"
[[ -f "$LC_SESSION" ]] && echo "  ✅ ランサーズ: セッションあり"

# ANTHROPIC_API_KEY 確認
echo "\n[3/4] API キー確認..."
if [[ -z "$ANTHROPIC_API_KEY" ]]; then
  echo "  ⚠️  ANTHROPIC_API_KEY 未設定（ルールベース評価で動作します）"
  echo "  より精度を上げるには:"
  echo "    cp $PIPELINE_DIR/.env.example $PIPELINE_DIR/.env"
  echo "    .env に ANTHROPIC_API_KEY を設定"
else
  echo "  ✅ API キーあり（Claude による高精度評価が有効）"
fi

# パイプライン実行（AUTO_APPLY=1: GOスコア80以上の案件に自動応募）
echo "\n[4/4] パイプライン実行中..."
cd "$PIPELINE_DIR"
AUTO_APPLY=1 AUTO_APPLY_THRESHOLD=80 python3 run_pipeline.py search

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ 完了"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  結果: $REPO_DIR/projects/2026-04-08_月30万自動化/D_エクセル入力スクレイピング/outputs/"
echo ""
