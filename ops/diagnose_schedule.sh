#!/bin/bash
# 「タスクが実行されていない」の原因調査。読み取りだけで、何も変更しない。
#   使い方: cd ~/agent-team && bash ops/diagnose_schedule.sh
cd "$(dirname "$0")/.."
echo "=== 1. crontab（日次公開は 0 8 * * * で登録されているはず） ==="
crontab -l 2>&1 | grep -v "^#" | grep -v "^$" || echo "（crontab は空、または未設定）"

echo ""
echo "=== 2. launchd（agentteam 系の常駐） ==="
launchctl list 2>/dev/null | grep agentteam || echo "（agentteam の登録なし）"

echo ""
echo "=== 3. cron のログ（cowork_run.sh の出力先） ==="
if [ -f ops/logs/cron.log ]; then
  echo "最終更新: $(date -r ops/logs/cron.log '+%Y-%m-%d %H:%M')"
  tail -15 ops/logs/cron.log
else
  echo "（ops/logs/cron.log が無い＝cron から一度も走っていない可能性）"
fi

echo ""
echo "=== 4. 直近の publish ログ（実際に走った証拠） ==="
ls -lt ops/logs/publish_*.log 2>/dev/null | head -5 || echo "（publish ログなし）"

echo ""
echo "=== 5. スリープ／再起動の履歴（cron が飛ぶ主因） ==="
pmset -g log 2>/dev/null | grep -iE "Sleep +|Wake +|Entering Sleep" | tail -12 || echo "（pmset ログ取得不可）"

echo ""
echo "=== 6. スリープ設定（AC電源時に眠るか） ==="
pmset -g custom 2>/dev/null | sed -n '1,24p' || echo "（取得不可）"

echo ""
echo "=== 7. git が使えるか（Xcodeライセンス等で止まっていないか） ==="
git --version && git -C . status --short | head -3 && echo "→ git は正常"
