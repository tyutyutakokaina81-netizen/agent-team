#!/bin/bash
# ============================================================
# run_comment_reply.sh — note コメント自動返信の専用便ランチャー（2026-07-30）
# ・LaunchAgent から 1日数回起動され、コメント返信だけを実行する軽量便。
# ・full worker(run_worker.sh) と同じロックを共有＝二重の claude -p 起動を防ぐ
#   （full worker が走行中ならこの便はスキップ＝そちらが毎便コメント返信を含むため取りこぼさない）。
# 手動起動も可: bash docs/run_comment_reply.sh
# ============================================================
set -u
cd "$HOME/agent-team-run" 2>/dev/null || cd "$HOME/agent-team" || exit 1

# full worker と同じロックを共有（同時に2つの claude -p を走らせない）
LOCK="$HOME/.agent-team-dispatch/worker.lock"
mkdir -p "$(dirname "$LOCK")"
if ! mkdir "$LOCK" 2>/dev/null; then
  # 既に worker が走行中 or 残骸。生存プロセスがあればスキップ（そちらがコメントも返す）。
  if pgrep -f "dangerously-skip-permissions" >/dev/null 2>&1; then
    echo "$(date '+%F %T') 別のワーカー走行中→コメント便スキップ"
    exit 0
  fi
  # 残骸ロックは回収（6時間超 or 生存プロセス無し）
  if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +360 2>/dev/null)" ]; then rm -rf "$LOCK"; mkdir "$LOCK" 2>/dev/null || exit 0; else exit 0; fi
fi
echo $$ > "$LOCK/pid" 2>/dev/null || true
trap 'rm -rf "$LOCK"' EXIT

echo "=== コメント返信便 開始 $(date '+%F_%H%M') ==="
git pull origin main -q 2>/dev/null || echo "⚠️ git pull 失敗（続行）"

CLA=$(command -v claude || ls "$HOME/.claude/local/claude" 2>/dev/null)
[ -z "$CLA" ] && { echo "✗ claude CLI が見つかりません"; exit 1; }

# -p(非対話) + skip-permissions＝報告書き込み/git push を許可（full worker と同方式）
"$CLA" -p --dangerously-skip-permissions "$(cat docs/worker-comment-reply.txt)" 2>&1 | tee -a comment_reply.log

# 実行ログを ops/logs に残して push（code が遠隔で確認できる）
mkdir -p ops/logs
{ echo "# comment-reply $(date '+%F %T')"; tail -60 comment_reply.log; } > ops/logs/comment_reply_last.log
git add ops/logs/comment_reply_last.log 2>/dev/null
git commit -qm "log(comments): $(date '+%F %H%M')" 2>/dev/null
git push -q origin main 2>/dev/null || true
echo "=== コメント返信便 終了 $(date '+%F_%H%M') ==="
