#!/bin/bash
# 日次公開(ops/cowork_run.sh)を **crontab から launchd へ移す**。
#   使い方: cd ~/agent-team && bash ops/install_daily_launchd.sh
#
# なぜ移すか（2026-09-16 の調査結果）:
#   ・cron は **実行時刻にMacが寝ていると、その回を黙って飛ばす**。起きても取り返さない。
#     ロックの残骸(.git/objects/maintenance.lock 等)から、この機械はスリープで処理を
#     中断された形跡が複数あった。09-14〜09-16 の公開ゼロと整合する。
#   ・launchd の StartCalendarInterval は **寝ていて逃した回を、起きた直後に実行する**。
#   ・cron は macOS アップデートのたびにフルディスクアクセス等で黙って壊れることがある。
set -uo pipefail
cd "$(dirname "$0")/.."
REPO="$(pwd)"
LADIR="$HOME/Library/LaunchAgents"
PLIST="$LADIR/com.agentteam.publish.plist"
mkdir -p "$LADIR" ops/logs

cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.agentteam.publish</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${REPO}/ops/cowork_run.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>8</integer><key>Minute</key><integer>0</integer></dict>
  <key>RunAtLoad</key><false/>
  <key>WorkingDirectory</key><string>${REPO}</string>
  <key>StandardOutPath</key><string>${REPO}/ops/logs/launchd_publish.log</string>
  <key>StandardErrorPath</key><string>${REPO}/ops/logs/launchd_publish.log</string>
</dict>
</plist>
PL

launchctl unload "$PLIST" 2>/dev/null || true
if launchctl load "$PLIST" 2>/dev/null; then
  echo "✅ 登録しました: com.agentteam.publish（毎日 08:00 / 寝ていたら起床後に実行）"
else
  echo "⚠️ load に失敗。手動で: launchctl load $PLIST"
fi

echo ""
echo "--- 現在の登録状況 ---"
launchctl list | grep agentteam || echo "（agentteam の登録なし）"

echo ""
echo "--- crontab に残っている cowork_run があれば、二重実行になるので外してください ---"
if crontab -l 2>/dev/null | grep -q "cowork_run"; then
  echo "⚠️ crontab に cowork_run の行があります。次のコマンドで編集して該当行を消してください:"
  echo "     crontab -e"
  crontab -l 2>/dev/null | grep -n "cowork_run"
else
  echo "（crontab に cowork_run は無し）"
fi
