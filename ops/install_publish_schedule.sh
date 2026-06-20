#!/bin/bash
# 【オーナーのMacで一度だけ実行】note公開を毎日 自動実行する launchd を登録する。
# launchd(LaunchAgent) はログイン中のGUIセッションで動くため、Chrome起動が必要な
# note公開にも対応できる（cron はGUI不可なので使わない）。
#
#   bash ops/install_publish_schedule.sh           # 既定: 毎日 08:00
#   bash ops/install_publish_schedule.sh 21 30     # 任意: 毎日 21:30
#
# 解除したいとき:
#   launchctl unload ~/Library/LaunchAgents/com.agentteam.publish.plist
set -euo pipefail

HOUR="${1:-8}"
MIN="${2:-0}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
LA="$HOME/Library/LaunchAgents"
PLIST="$LA/com.agentteam.publish.plist"
mkdir -p "$LA" "$REPO/ops/logs"

cat > "$PLIST" <<EOF
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
  <dict>
    <key>Hour</key><integer>${HOUR}</integer>
    <key>Minute</key><integer>${MIN}</integer>
  </dict>
  <key>StandardOutPath</key><string>${REPO}/ops/logs/launchd.out.log</string>
  <key>StandardErrorPath</key><string>${REPO}/ops/logs/launchd.err.log</string>
  <key>RunAtLoad</key><false/>
</dict>
</plist>
EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

echo "✅ 登録完了: $PLIST"
echo "   → 毎日 $(printf '%02d:%02d' "$HOUR" "$MIN") に drafts/queue を処理し、結果を ops/logs/ と ops/outbox/ に残して push します。"
echo ""
echo "   ★安全ゲート（既定はOFF＝本番公開しない）★"
echo "   既定では cowork_run.sh は --draft（下書き保存のみ）で動きます。本番公開はしません。"
echo "   note側の棚卸し（再開条件①③）が完了したら、本番公開を有効化:"
echo "       touch \"$REPO/ops/PUBLISH_ENABLED\"   # 本番公開ON"
echo "       rm    \"$REPO/ops/PUBLISH_ENABLED\"   # 本番公開OFF（下書きのみに戻す）"
echo "   未来日付ファイルは自動スキップ、公開済み記事は冪等化で二重公開しません。"
echo ""
echo "   今すぐ動作テスト（既定=下書きで安全）: launchctl start com.agentteam.publish"
echo "   解除: launchctl unload $PLIST"
