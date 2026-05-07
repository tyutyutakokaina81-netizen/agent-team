#!/bin/bash
# smoke_test.sh — PDCA スクリプトの回帰検知（軽量・依存ゼロ）
#
# 目的：refactor 後に各スクリプトが起動・正常終了するか確認。
# 機能の正しさは検証しない（exit code のみ）。
# 費用：¥0

set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../../.."

PASS=0
FAIL=0
FAILED_TESTS=()

run() {
  local label="$1"; shift
  if "$@" >/dev/null 2>&1; then
    echo "🟢 $label"
    PASS=$((PASS + 1))
  else
    echo "🔴 $label  (exit code: $?)"
    FAIL=$((FAIL + 1))
    FAILED_TESTS+=("$label")
  fi
}

echo "━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 PDCA Scripts スモークテスト"
echo "━━━━━━━━━━━━━━━━━━━━━━━"

run "daily_standup --dry-run"           node CDO/outputs/daily_standup.mjs --dry-run
run "morning_meeting --dry-run"         node CDO/outputs/morning_meeting.mjs --dry-run --no-notify
run "morning_meeting --if-missing"      node CDO/outputs/morning_meeting.mjs --no-notify --if-missing
run "evening_checkin --dry-run"         node CDO/outputs/evening_checkin.mjs --dry-run --no-notify
run "improvement_log_generator dry"     node CDO/outputs/improvement_log_generator.mjs --dry-run
run "pdca_status"                       node CDO/outputs/pdca_status.mjs
run "metrics_input --show"              node CDO/outputs/metrics_input.mjs --show
run "metrics_input --json"              node CDO/outputs/metrics_input.mjs --json
run "note_article_scaffold --list"      node CDO/outputs/note_article_scaffold.mjs --list
run "note_article_scaffold dry"         node CDO/outputs/note_article_scaffold.mjs --topic vol1_freelance_cashflow --dry-run
run "notify (test message)"             node CDO/outputs/notify.mjs "smoke test" "ok" info
run "session-start hook"                env CLAUDE_PROJECT_DIR="$PWD" bash .claude/hooks/session-start.sh
run "lib/pdca_lib import"               node -e "import('./CDO/outputs/lib/pdca_lib.mjs').then(m=>{if(!m.today())process.exit(1)})"
run "daily_audit"                       node CDO/outputs/daily_audit.mjs --quiet
run "article_quality_checker --help"    node CDO/outputs/article_quality_checker.mjs --help

echo "━━━━━━━━━━━━━━━━━━━━━━━"
echo "Results: 🟢 PASS=$PASS / 🔴 FAIL=$FAIL"
echo "━━━━━━━━━━━━━━━━━━━━━━━"

if [ $FAIL -gt 0 ]; then
  echo ""
  echo "Failed tests:"
  for t in "${FAILED_TESTS[@]}"; do
    echo "  - $t"
  done
  exit 1
fi

exit 0
