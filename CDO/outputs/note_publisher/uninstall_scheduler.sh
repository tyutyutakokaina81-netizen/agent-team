#!/bin/zsh
# uninstall_scheduler.sh — 無人公開スケジューラを停止・削除する
set -u
LABEL="com.agentteam.notepublish"
DST="${HOME}/Library/LaunchAgents/${LABEL}.plist"

launchctl unload "$DST" 2>/dev/null || true
if [[ -f "$DST" ]]; then
  rm -f "$DST"
  echo "✅ スケジューラを停止・削除しました（${DST}）"
else
  echo "ℹ️  スケジューラは登録されていません"
fi
