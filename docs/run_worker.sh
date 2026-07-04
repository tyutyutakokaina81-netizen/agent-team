#!/bin/bash
# ワーカー実行＋ログ自動送信ランチャー（ownerはこれを実行するだけ）
# ログ末尾を ops/logs/ にコミットして push するため、code が遠隔で診断できる。
cd "$HOME/agent-team-run" || exit 1
git pull origin main -q
TS=$(date +%Y-%m-%d_%H%M)
echo "=== ワーカー開始 ${TS}（終了まで無言が正常）==="
CLA=$(command -v claude || ls "$HOME/.claude/local/claude" 2>/dev/null)
"$CLA" -p "$(cat docs/worker-prompt.txt)" 2>&1 | tee -a worker.log
RC=$?
mkdir -p ops/logs
tail -120 worker.log > "ops/logs/worker_${TS}.log"
echo "exit_code=${RC}" >> "ops/logs/worker_${TS}.log"
git add ops/logs/ >/dev/null 2>&1
git commit -q -m "log: worker run ${TS} (tail auto-upload, rc=${RC})" >/dev/null 2>&1
git push -q origin main >/dev/null 2>&1
echo "=== 終了（ログをリポジトリへ自動送信済み・codeが遠隔診断できます）==="
