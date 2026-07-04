#!/bin/bash
# 配車係（dispatcher）: 5分ごとにcronで起動し、mainの ops/run_requests/ に未消化の
# 実行要求があれば run_worker.sh を起動する。これにより code が実行要求ファイルを
# push するだけでワーカー便が出る（ownerのコマンド貼り付け不要）。
#
# インストール（1回だけ・ownerのMacで）:
#   bash docs/worker_dispatcher.sh --install
# アンインストール:
#   crontab -l | grep -v worker_dispatcher.sh | crontab -
REPO="$HOME/agent-team-run"
STATE_DIR="$HOME/.agent-team-dispatch"
mkdir -p "$STATE_DIR"

if [ "$1" = "--install" ]; then
  LINE="*/5 * * * * /bin/bash $REPO/docs/worker_dispatcher.sh >> $STATE_DIR/dispatch.log 2>&1"
  (crontab -l 2>/dev/null | grep -v worker_dispatcher.sh; echo "$LINE") | crontab -
  echo "✅ 配車係を登録しました（5分ごと）。ログ: $STATE_DIR/dispatch.log"
  echo "   以後、code が ops/run_requests/ に要求を push すると自動でワーカー便が出ます。"
  exit 0
fi

cd "$REPO" || exit 1
git pull origin main -q 2>/dev/null

# 朝の定期便cron(7:17)の前後30分は配車しない（同時実行ガード。ロックでも守るが二重の保険）
HM=$(date +%H%M)
if [ "$HM" -ge 0647 ] && [ "$HM" -le 0747 ]; then exit 0; fi

# 未消化の実行要求を探す（消化済みはローカル記録。Macは1台前提）
CONSUMED="$STATE_DIR/consumed.txt"
touch "$CONSUMED"
REQ=""
for f in ops/run_requests/*.txt; do
  [ -e "$f" ] || continue
  grep -qxF "$f" "$CONSUMED" || { REQ="$f"; break; }
done
[ -z "$REQ" ] && exit 0

echo "$REQ" >> "$CONSUMED"
echo "=== dispatch: ${REQ} $(date '+%Y-%m-%d %H:%M:%S') ==="
# 実行中ロックは run_worker.sh 自身が持つ（実行中なら即終了するだけで安全）
bash docs/run_worker.sh
