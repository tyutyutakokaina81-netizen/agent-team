#!/bin/bash
# ============================================================
# install_autopilot.sh — 「すべて一度に自動化」(owner指示 2026-07-10)
# ============================================================
# owner が Mac のターミナルで【一度だけ】実行:
#   cd ~/agent-team-run && git pull origin main -q && bash docs/install_autopilot.sh
#
# これがやること（cronより堅牢な macOS LaunchAgent 化）:
#   1) 配車係(dispatcher)を 5分ごと + ログイン時(RunAtLoad) に起動する LaunchAgent を常駐
#      → Mac再起動しても自動復活・cronのように消えない・スリープ明けも走る
#   2) 毎日の定期便(run_worker.sh)を 7:17 に起動する LaunchAgent を常駐
#   3) 今すぐ1回、配車係を起動（積まれた便を即消化）
#   ※以後 owner の作業はゼロ。code が run_requests を push すれば自動でワーカー便が出る。
#
# なぜ「一度だけ」は必要か: code はクラウド(A1)にいて owner の Mac を直接操作できない。
#   Mac 上で自動実行を"仕込む"作業だけは、物理的に Mac 上で1回動かす必要がある。以後は無人。
set -u
REPO="${AGENT_TEAM_DIR:-$HOME/agent-team-run}"
LADIR="$HOME/Library/LaunchAgents"
DISP_PLIST="$LADIR/com.agentteam.dispatcher.plist"
DAILY_PLIST="$LADIR/com.agentteam.daily.plist"
STATE_DIR="$HOME/.agent-team-dispatch"
mkdir -p "$LADIR" "$STATE_DIR"

cd "$REPO" 2>/dev/null || { echo "✗ $REPO が見つかりません。先に run_all.sh か git clone を。"; exit 1; }
git pull origin main -q 2>/dev/null || echo "⚠️ git pull 失敗（オフライン?）。手元mainで続行。"

echo "=================================================="
echo " オートパイロット導入（LaunchAgent・再起動しても自動）"
echo "=================================================="

# 旧cron(あれば)は撤去してLaunchAgentへ一本化（二重起動防止）
if crontab -l 2>/dev/null | grep -q worker_dispatcher.sh; then
  crontab -l 2>/dev/null | grep -v worker_dispatcher.sh | crontab -
  echo "  ・旧cron(dispatcher)を撤去 → LaunchAgentへ移行"
fi

# ---- 1) 配車係 LaunchAgent（5分ごと + ログイン時）----
cat > "$DISP_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.agentteam.dispatcher</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$REPO/docs/worker_dispatcher.sh</string>
  </array>
  <key>StartInterval</key><integer>300</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$STATE_DIR/dispatch.log</string>
  <key>StandardErrorPath</key><string>$STATE_DIR/dispatch.log</string>
</dict>
</plist>
PLIST

# ---- 2) 毎日の定期便 LaunchAgent（7:17）----
cat > "$DAILY_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.agentteam.daily</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$REPO/docs/run_worker.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>7</integer><key>Minute</key><integer>17</integer></dict>
  <key>RunAtLoad</key><false/>
  <key>StandardOutPath</key><string>$STATE_DIR/daily.log</string>
  <key>StandardErrorPath</key><string>$STATE_DIR/daily.log</string>
</dict>
</plist>
PLIST

# ---- スリープ防止 LaunchAgent（owner「毎回止まる」対策 2026-07-11）----
# caffeinate -s = AC電源接続中はシステムスリープを抑止（バッテリー時は通常どおり眠る＝電池を守る）。
# これで「Macがスリープ→配車係が止まる→公開されない」を根治。KeepAlive=落ちても復活。
AWAKE_PLIST="$LADIR/com.agentteam.awake.plist"
cat > "$AWAKE_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.agentteam.awake</string>
  <key>ProgramArguments</key>
  <array><string>/usr/bin/caffeinate</string><string>-s</string></array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
</dict>
</plist>
PLIST

# ---- ロード（既存はunloadしてから）----
for L in "$DISP_PLIST" "$DAILY_PLIST" "$AWAKE_PLIST"; do
  launchctl unload "$L" 2>/dev/null || true
  launchctl load "$L" 2>/dev/null && echo "  ✅ 常駐登録: $(basename "$L")" || echo "  ⚠️ load失敗: $(basename "$L")（手動: launchctl load $L）"
done

echo "---- 3) 今すぐ1回、配車係を起動（積まれた便を消化）----"
bash "$REPO/docs/worker_dispatcher.sh" || true

echo "=================================================="
echo " ✅ 完了。以後は Mac を起動しておくだけで自動運転。"
echo "    ・5分ごとに配車係が run_requests を消化"
echo "    ・毎朝7:17に定期便"
echo "    ・再起動してもログイン時に自動復活（cronと違い消えない）"
echo "    確認: launchctl list | grep agentteam"
echo "    ログ: tail -f $STATE_DIR/dispatch.log"
echo "=================================================="
