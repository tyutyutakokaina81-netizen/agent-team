#!/bin/bash
# ops/mac_diag.sh — Mac 側の自動実行の設定を集めて、リポジトリに置いて push する。
#
#   cd ~/agent-team-run 2>/dev/null || cd ~/agent-team; bash ops/mac_diag.sh
#
# なぜ（2026-10-21）:
#   毎晩 18:09〜18:11 に `merge: sync with origin before auto-backup` というコミットが作られ、
#   **origin 側で増えたファイルを捨てている**（記事5本・サムネ5枚・検査3本などが消えた）。
#   リポジトリの中には該当する実装が無く、Mac の中にしかない。
#   ところが**ターミナルの出力を貼り直すと、それがコマンドとして実行されてしまう**
#   （実際 `zsh: command not found: 881` が大量に出た）。
#   だから**貼らずに、ファイルにしてリポジトリへ push する**形にする。
#
# 集めるもの（読み取りだけ。設定は何も変えない）:
#   ・LaunchAgents の中身（agent-team 系だけ）
#   ・crontab
#   ・`cfo-agent` という名前を含むファイル（コミットの author がこれ）
#   ・`自動バックアップ` という文字列を含むファイル
set +e
cd "$(dirname "$0")/.." 2>/dev/null || exit 1
OUT="ops/logs/mac_diag.txt"
mkdir -p ops/logs
{
  echo "=== 取得: $(date) ==="
  echo ""
  echo "=== LaunchAgents（agent-team 系の中身） ==="
  for f in "$HOME"/Library/LaunchAgents/*.plist; do
    case "$f" in
      *agent-team*|*agentteam*) echo "----- $f"; cat "$f"; echo "";;
    esac
  done
  echo "=== crontab ==="
  crontab -l 2>/dev/null
  echo ""
  echo "=== 'cfo-agent' を含むファイル（コミットの author がこれ） ==="
  grep -rls "cfo-agent" "$HOME/Library/LaunchAgents" "$HOME/bin" "$HOME/.zshrc" \
      "$HOME/ai-auto" "$HOME/note-auto" "$HOME/quiet-japan" "$HOME/.agent-team-dispatch" 2>/dev/null | head -20
  echo ""
  echo "=== '自動バックアップ' を含むファイル ==="
  grep -rls "自動バックアップ" "$HOME/Library/LaunchAgents" "$HOME/bin" "$HOME/.zshrc" \
      "$HOME/ai-auto" "$HOME/note-auto" "$HOME/quiet-japan" "$HOME/.agent-team-dispatch" 2>/dev/null | head -20
  echo ""
  echo "=== git の author 設定 ==="
  git config --get user.name; git config --get user.email
  git config --global --get user.name; git config --global --get user.email
} > "$OUT" 2>&1

echo "書き出しました: $OUT"
git add -f "$OUT" >/dev/null 2>&1
git commit -q -m "diag: Mac 側の自動実行の設定を収集" >/dev/null 2>&1
for i in 1 2 3; do
  git push -q origin main 2>/dev/null && { echo "push しました。次のセッションで code が読みます"; exit 0; }
  git pull --rebase --autostash -q origin main 2>/dev/null
done
echo "push に失敗しました。もう一度 bash ops/mac_diag.sh を実行してください"
