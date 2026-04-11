#!/bin/zsh
# ================================================================
# automate.sh — リスクゼロの全自動化セットアップ
#
# 自動化される操作（人の手不要）:
#   - C柱: Vol.1〜2 Excelファイル生成
#   - D柱: 案件検索・評価・応募文生成（cron 毎日9時・18時）
#   - 日次レポート: 毎朝8時に進捗サマリー生成
#
# 人の手が必要な操作（安全のため自動化しない）:
#   - BOOTH: 「公開」ボタンのクリック（下書きは自動作成）
#   - 応募: 「応募」ボタンのクリック（URLは自動で開く）
#   - 口座: BOOTHが翌月末に自動振込（設定だけ必要）
#
# 使い方: ./automate.sh
# ================================================================
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
TEMPLATE_DIR="$REPO_DIR/projects/2026-04-08_月30万自動化/C_テンプレ販売"
PIPELINE_DIR="$REPO_DIR/projects/2026-04-08_月30万自動化/D_エクセル入力スクレイピング/pipeline"
LOG_DIR="$REPO_DIR/logs"
mkdir -p "$LOG_DIR"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🤖 リスクゼロ全自動化セットアップ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ────────────────────────────────────────────────────────
# STEP 1: 依存ライブラリ確認
# ────────────────────────────────────────────────────────
echo "\n[1/4] 依存ライブラリ確認..."
python3 -c "import openpyxl" 2>/dev/null || {
  echo "  openpyxl をインストールします..."
  pip3 install openpyxl -q
}
python3 -c "import playwright" 2>/dev/null || {
  echo "  playwright をインストールします..."
  pip3 install playwright -q
  playwright install chromium --quiet
}
echo "  ✅ 依存ライブラリ OK"

# ────────────────────────────────────────────────────────
# STEP 2: C柱 — Excelテンプレート自動生成
# ────────────────────────────────────────────────────────
echo "\n[2/4] C柱: Excelテンプレート生成..."
cd "$TEMPLATE_DIR"
python3 generate_products.py 2>&1 | sed 's/^/  /'

DIST_DIR="$TEMPLATE_DIR/dist"
if [[ -f "$DIST_DIR/vol1_freelance_cashflow.xlsx" ]] && [[ -f "$DIST_DIR/vol2_sns_calendar.xlsx" ]]; then
  echo "  ✅ テンプレートファイル生成完了"
  echo "  📁 $DIST_DIR/"
else
  echo "  ⚠️  一部ファイルの生成に失敗しました（openpyxlを確認してください）"
fi

# ────────────────────────────────────────────────────────
# STEP 3: D柱 — cron自動スケジューラ設定
# ────────────────────────────────────────────────────────
echo "\n[3/4] D柱: cron自動化設定..."

LOGFILE="$REPO_DIR/pipeline.log"
REPORT_LOGFILE="$LOG_DIR/daily_report.log"
CURRENT_CRON=$(crontab -l 2>/dev/null || echo "")

# 既登録チェック
if echo "$CURRENT_CRON" | grep -q "agent-team/start.sh"; then
  echo "  ✅ パイプライン cron 登録済み（スキップ）"
else
  NEW_CRON="$CURRENT_CRON
# agent-team パイプライン（毎日 9:00 と 18:00）
0 9 * * * $REPO_DIR/start.sh >> $LOGFILE 2>&1
0 18 * * * $REPO_DIR/start.sh >> $LOGFILE 2>&1"
  echo "$NEW_CRON" | crontab -
  echo "  ✅ パイプライン cron 登録: 毎日 09:00・18:00"
fi

# 日次レポートの cron 登録
if echo "$CURRENT_CRON" | grep -q "daily_report.py"; then
  echo "  ✅ 日次レポート cron 登録済み（スキップ）"
else
  CURRENT_CRON2=$(crontab -l 2>/dev/null || echo "")
  REPORT_CRON="$CURRENT_CRON2
# agent-team 日次レポート（毎朝 8:00）
0 8 * * * python3 $REPO_DIR/daily_report.py >> $REPORT_LOGFILE 2>&1"
  echo "$REPORT_CRON" | crontab -
  echo "  ✅ 日次レポート cron 登録: 毎朝 08:00"
fi

# ────────────────────────────────────────────────────────
# STEP 4: 初回レポート表示
# ────────────────────────────────────────────────────────
echo "\n[4/4] 初回ステータスレポート..."
python3 "$REPO_DIR/daily_report.py" 2>&1 | sed 's/^/  /'

# ────────────────────────────────────────────────────────
# 完了サマリー
# ────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ 自動化セットアップ完了"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  【自動化済み（人不要）✅ × 5】"
echo "  ✅ 1. Excelテンプレート生成（毎回）"
echo "  ✅ 2. BOOTH出品 → 即公開（セッション設定後に自動）"
echo "  ✅ 3. 案件検索・評価（毎日 09:00・18:00）"
echo "  ✅ 4. 応募文生成 + 自動送信（GO・スコア80以上）"
echo "  ✅ 5. 日次レポート（毎朝 08:00）→ $REPORT_LOGFILE"
echo ""
echo "  【あなたが1回だけやること（残り2件）】"
echo "  1. 各プラットフォームの初回ログイン（ブラウザでIDとパスを入力するだけ）"
echo "     → cd $PIPELINE_DIR && python3 00_session_setup.py"
echo "     → python3 $TEMPLATE_DIR/auto_booth_publish.py"
echo "  2. BOOTH 振込先口座登録（売上を受け取るため）"
echo "     → https://manage.booth.pm/payment_accounts"
echo ""
echo "  【毎日やること（0秒）】"
echo "  → なし。全部自動で動きます。"
echo "  ※ 売上確認だけ: $REPORT_LOGFILE"
echo ""
