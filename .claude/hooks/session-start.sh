#!/bin/bash
# Agent Team — SessionStart Hook
#
# 役割：Claude Code セッション起動時に PDCA サイクル（朝会＋ヘルスチェック）を自動実行
#
# 設計原則：
#   - 依存インストール不要（プロジェクトは Node 標準モジュールのみ）
#   - 冪等性：複数回実行しても安全（朝会レポートは当日分を上書き）
#   - 非対話：プロンプト・確認なし
#   - 同期実行：セッション開始前に PDCA レポートが揃った状態にする
#   - 費用ゼロ：外部API呼び出し・新規SaaSなし
#
# 実行頻度：Claude Code セッションが起動されるたび（startup / resume / clear / compact）

set -euo pipefail

# プロジェクトルートに移動（CLAUDE_PROJECT_DIR が無い環境でも動くよう fallback）
cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}"

echo "━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌅 Agent Team — PDCA SessionStart"
echo "━━━━━━━━━━━━━━━━━━━━━━━"

# Node のチェック（無ければスキップ・致命的にはしない）
if ! command -v node >/dev/null 2>&1; then
  echo "⚠️ node が見つかりません。PDCA hook をスキップします。"
  exit 0
fi

# 朝会レポート生成（--if-missing：当日分が無い時だけ書き込み・冪等）
echo ""
echo "▼ 朝会レポート確認"
if [ -x CDO/outputs/morning_meeting.mjs ] || [ -f CDO/outputs/morning_meeting.mjs ]; then
  node CDO/outputs/morning_meeting.mjs --no-notify --if-missing || echo "⚠️ 朝会生成失敗（継続）"
else
  echo "⚠️ morning_meeting.mjs が存在しません（スキップ）"
fi

# ヘルスチェック
echo ""
echo "▼ PDCA ヘルスチェック"
if [ -x CDO/outputs/pdca_status.mjs ] || [ -f CDO/outputs/pdca_status.mjs ]; then
  node CDO/outputs/pdca_status.mjs || echo "⚠️ ヘルスチェック失敗（継続）"
else
  echo "⚠️ pdca_status.mjs が存在しません（スキップ）"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━"
echo "📚 本日の朝会：CDO/research/meetings/$(date +%Y-%m-%d)_morning.md"
echo "💡 数字入力：node CDO/outputs/metrics_input.mjs"
echo "🌆 夕方：node CDO/outputs/evening_checkin.mjs"
echo "━━━━━━━━━━━━━━━━━━━━━━━"

exit 0
