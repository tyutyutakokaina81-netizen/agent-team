#!/bin/zsh
# install_scheduler.sh — 無人公開スケジューラを Mac にインストール（一度だけ実行）
#
# 毎日決まった時刻に daily_auto_publish.sh を自動実行する launchd ジョブを登録する。
# インストール後はオーナーの手作業ゼロで、その日の記事がサムネ付きで公開される。
#
# 使い方:
#   ./install_scheduler.sh           # 毎朝 7:30 に実行（既定）
#   ./install_scheduler.sh 8 0       # 毎朝 8:00 に実行（時 分 を指定）
#
# ★前提（一度だけ）:
#   1) ./setup.sh                       でPlaywright/Chromium導入
#   2) python3 publish_to_note.py --login  でnoteログイン（セッション保存）
set -e

SCRIPT_DIR="${0:A:h}"
LABEL="com.agentteam.notepublish"
TEMPLATE="${SCRIPT_DIR}/${LABEL}.plist.template"
DST="${HOME}/Library/LaunchAgents/${LABEL}.plist"
HOUR="${1:-7}"
MIN="${2:-30}"

[[ -f "$TEMPLATE" ]] || { echo "✗ テンプレートが無い: $TEMPLATE"; exit 1; }

mkdir -p "${HOME}/Library/LaunchAgents" "${SCRIPT_DIR}/logs"
chmod +x "${SCRIPT_DIR}/daily_auto_publish.sh" "${SCRIPT_DIR}/publish_all.sh" 2>/dev/null || true

# ログインセッション確認（無いと無人公開は失敗するので警告）
if [[ ! -d "${HOME}/.note_publisher_profile" ]]; then
  echo "⚠️  noteログインがまだのようです。先に:"
  echo "     python3 publish_to_note.py --login"
  echo "   を済ませてから再実行してください（このまま続行はします）。"
fi

sed -e "s|__SCRIPT_DIR__|${SCRIPT_DIR}|g" \
    -e "s|__HOUR__|${HOUR}|g" \
    -e "s|__MIN__|${MIN}|g" \
    "$TEMPLATE" > "$DST"

# 既存ジョブがあれば外してから読み込み直す
launchctl unload "$DST" 2>/dev/null || true
launchctl load "$DST"

echo "✅ インストール完了"
echo "   毎日 ${HOUR}:$(printf '%02d' "$MIN") に自動公開します（最大5本・重複/未来日付ガード付き）"
echo ""
echo "   今すぐテスト実行 : launchctl start ${LABEL}"
echo "   実行ログ        : ${SCRIPT_DIR}/logs/"
echo "   停止・削除      : ./uninstall_scheduler.sh"
