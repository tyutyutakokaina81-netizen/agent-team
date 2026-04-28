#!/bin/zsh
# setup_all.sh — 全自動化の初回セットアップ（一度だけ実行）
#
# やること:
#   1. Playwright インストール
#   2. note.com ログイン保存
#   3. X(Twitter) ログイン保存
#   4. CW ログイン保存
#   5. 毎朝9時の自動実行を LaunchAgent に登録
#
# 実行: zsh ~/agent-team/setup_all.sh

REPO="$HOME/agent-team"
SESSIONS="$REPO/.sessions"
mkdir -p "$SESSIONS" "$REPO/logs"

ok()  { echo "  ✅ $1"; }
err() { echo "  ❌ $1"; }
hdr() {
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  $1"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# ────────────────────────────────────────
hdr "STEP 1/5  Playwright インストール"
# ────────────────────────────────────────
if python3 -c "import playwright" 2>/dev/null; then
  ok "Playwright 導入済み"
else
  echo "  インストール中..."
  pip3 install playwright -q && playwright install chromium --quiet
  ok "Playwright インストール完了"
fi

# ────────────────────────────────────────
hdr "STEP 2/5  Chrome セッション一括取得（BOOTH / note / X）"
# ────────────────────────────────────────
echo "  Chromeにログイン済みであれば自動取得します"
echo "  ※ キーチェーンのダイアログが出たら「許可」"
python3 "$REPO/mac_auto_cookie_all.py"

# ────────────────────────────────────────
hdr "STEP 3/5  クラウドワークス セッション確認"
# ────────────────────────────────────────
CW_SESSION="$REPO/projects/2026-04-08_月30万自動化/D_エクセル入力スクレイピング/.sessions/crowdworks_session.json"
if [ -f "$CW_SESSION" ]; then
  ok "CW セッション済み（スキップ）"
else
  echo "  CWのセッションがありません。ブラウザでログインします..."
  python3 - <<'PYEOF'
import json, sys
from pathlib import Path
SESSION_FILE = Path.home() / "agent-team/projects/2026-04-08_月30万自動化/D_エクセル入力スクレイピング/.sessions/crowdworks_session.json"
SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
try:
    import browser_cookie3 as bc3
    jar = bc3.chrome(domain_name='.crowdworks.jp')
    cookies = {c.name: c.value for c in jar}
    if cookies:
        state = {"cookies": [{"name":k,"value":v,"domain":".crowdworks.jp","path":"/","expires":-1,"httpOnly":False,"secure":True,"sameSite":"None"} for k,v in cookies.items()], "origins":[]}
        SESSION_FILE.write_text(json.dumps(state), encoding="utf-8")
        print(f"  ✅ CW: {len(cookies)}個のクッキーを保存")
    else:
        print("  ⚠️  CWのクッキーなし → Chromeでクラウドワークスにログインしてから再実行")
except Exception as e:
    print(f"  エラー: {e}")
PYEOF
fi

# ────────────────────────────────────────
hdr "STEP 5/5  毎朝9時 自動実行 登録"
# ────────────────────────────────────────
PLIST="$HOME/Library/LaunchAgents/com.agent-team.daily.plist"

cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.agent-team.daily</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/zsh</string>
        <string>${REPO}/run_daily_auto.sh</string>
    </array>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>${REPO}/logs/launchd_daily.log</string>
    <key>StandardErrorPath</key>
    <string>${REPO}/logs/launchd_daily_err.log</string>

    <key>WorkingDirectory</key>
    <string>${REPO}</string>

    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
PLIST_EOF

# 既存の登録を解除してから再登録
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
ok "毎朝9:00 自動実行 登録完了"

# ────────────────────────────────────────
hdr "セットアップ完了"
# ────────────────────────────────────────
echo ""
echo "  毎朝9:00 に以下が自動実行されます："
echo "    note記事 公開（初回のみ）"
echo "    X投稿 1本（5本ローテーション）"
echo "    CW案件 5件応募"
echo "    CWサービス 出品"
echo ""
echo "  ログ確認："
echo "    cat $REPO/logs/daily_auto_\$(date +%Y-%m-%d).log"
echo ""
echo "  今すぐ手動実行："
echo "    zsh $REPO/run_daily_auto.sh"
echo ""
echo "  停止："
echo "    launchctl unload $PLIST"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
