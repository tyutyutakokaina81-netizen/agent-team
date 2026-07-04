#!/bin/bash
# ワーカー実行＋ログ自動送信ランチャー v2
# ・実行中: 3分ごとにログ末尾を ops/logs/worker_live.log として自動push（codeが遠隔でリアルタイム診断）
# ・終了時: ログ末尾120行+exit code を ops/logs/worker_<日時>.log として push
cd "$HOME/agent-team-run" || exit 1
git pull origin main -q
TS=$(date +%Y-%m-%d_%H%M)
CLA=$(command -v claude || ls "$HOME/.claude/local/claude" 2>/dev/null)

# 送信専用クローン（ワーカーのgit操作と衝突させない）
LOGCLONE="$HOME/.agent-team-logclone"
URL=$(git remote get-url origin)
if [ ! -d "$LOGCLONE/.git" ]; then git clone --depth 1 -q "$URL" "$LOGCLONE"; fi

echo "=== ワーカー開始 ${TS}（実行中も3分ごとに状況が自動送信されます）==="
# --dangerously-skip-permissions: -p(非対話)では権限プロンプトに答えられず、報告書き込み/git pushが
# 全部ブロックされる（2026-07-04 11:35便で実証: 報告もログも届かなかった）。owner環境の自リポジトリ限定運用。
"$CLA" -p --dangerously-skip-permissions "$(cat docs/worker-prompt.txt)" 2>&1 | tee -a worker.log &
PID=$!

# ライブ送信ループ（ワーカーが生きている間だけ）
(
  while kill -0 $PID 2>/dev/null; do
    sleep 180
    kill -0 $PID 2>/dev/null || break
    cd "$LOGCLONE" && git pull --rebase -q origin main 2>/dev/null
    mkdir -p ops/logs
    { echo "# live tail $(date '+%H:%M:%S') (running)"; tail -80 "$HOME/agent-team-run/worker.log"; } > ops/logs/worker_live.log
    git add ops/logs/worker_live.log 2>/dev/null
    git commit -qm "log(live): worker running $(date '+%H:%M')" 2>/dev/null
    git push -q origin main 2>/dev/null || true
  done
) &
LIVEPID=$!

wait $PID
RC=$?
kill $LIVEPID 2>/dev/null

# 最終ログ送信
cd "$LOGCLONE" && git pull --rebase -q origin main 2>/dev/null
mkdir -p ops/logs
{ tail -120 "$HOME/agent-team-run/worker.log"; echo "exit_code=${RC}"; } > "ops/logs/worker_${TS}.log"
echo "# finished $(date '+%H:%M:%S') rc=${RC}" > ops/logs/worker_live.log
git add ops/logs/ 2>/dev/null
git commit -qm "log: worker run ${TS} finished (rc=${RC})" 2>/dev/null
git push -q origin main 2>/dev/null || true
echo "=== 終了 rc=${RC}（ログ送信済み・codeが遠隔診断できます）==="
