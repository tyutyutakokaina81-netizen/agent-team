#!/bin/bash
# Mac 側の自動実行の設定を集めて、リポジトリのファイルに書き出して push する。
# オーナーは `bash ops/mac_diag.sh` の1行だけ。**画面の出力を貼る必要がない**のが要点。
#   ★2026-10-21: ターミナルの出力を貼り直すと、シェルがそれをコマンドとして実行してしまい
#     `zsh: command not found: 881` が大量に出て肝心の中身が取れなかった。だから貼らない。
# **設定は何も変えない。読み取りだけ。**
set +e
cd "$(dirname "$0")/.." 2>/dev/null || exit 1

# ★Mac 以外で走らせない。code（Linux のコンテナ）で動作確認したら、**中身が空の診断ファイルが
#   そのまま push され**、翌日それを「Mac の結果」として読みかけた。空のファイルは
#   「設定が無い」という**誤った結論**に直結するので、ここで止める。
if [ "$(uname)" != "Darwin" ]; then
  echo "✗ これは Mac で実行するスクリプトです（いまは $(uname)）。"
  echo "  オーナーの Mac で: cd ~/agent-team-run 2>/dev/null || cd ~/agent-team; bash ops/mac_diag.sh"
  exit 1
fi

OUT="ops/logs/mac_diag.txt"
mkdir -p ops/logs
{
  echo "=== 取得: $(date) ==="
  echo
  echo "=== LaunchAgents（agent-team 系の中身） ==="
  for f in "$HOME"/Library/LaunchAgents/*agent*team*.plist "$HOME"/Library/LaunchAgents/*agentteam*.plist; do
    [ -f "$f" ] || continue
    echo "----- $f"; cat "$f"; echo
  done

  echo "=== crontab ==="
  crontab -l 2>/dev/null

  # ★ここから v2（2026-10-21 10:46 の結果を見て足した）。
  #   v1 は `agent-team-run` の中だけを grep していたので **空で返ってきた**。
  #   ところが plist は `/Users/apple/agent-team`（run なし＝**別のクローン**）も指していた。
  #   消失コミットの author `cfo-agent` も「自動バックアップ」も、そっちにある見込みが高い。
  echo
  echo "=== 同じリポジトリのクローンが Mac に何個あるか ==="
  for d in "$HOME"/agent-team "$HOME"/agent-team-run "$HOME"/ai-auto "$HOME"/note-auto "$HOME"/quiet-japan; do
    [ -d "$d" ] || continue
    echo "----- $d"
    echo "  remote: $(git -C "$d" remote -v 2>/dev/null | head -1)"
    echo "  branch: $(git -C "$d" rev-parse --abbrev-ref HEAD 2>/dev/null)"
    echo "  HEAD  : $(git -C "$d" log -1 --pretty='%h %an | %s' 2>/dev/null | cut -c1-80)"
    echo "  author: $(git -C "$d" config user.name 2>/dev/null) / $(git -C "$d" config user.email 2>/dev/null)"
  done

  echo
  echo "=== 'cfo-agent' / 'auto-backup' / '自動バックアップ' / 'sync with origin' を含むファイル ==="
  # ホーム全体は重いので、自動実行に関係する場所だけ・深さを切って探す。
  for d in "$HOME"/agent-team "$HOME"/agent-team-run "$HOME"/scripts "$HOME"/bin \
           "$HOME"/ai-auto "$HOME"/note-auto "$HOME"/quiet-japan "$HOME"/Library/LaunchAgents; do
    [ -d "$d" ] || continue
    grep -rlI --exclude-dir=.git --exclude-dir=node_modules \
      -e 'cfo-agent' -e 'auto-backup' -e '自動バックアップ' -e 'sync with origin' \
      "$d" 2>/dev/null | head -20
  done | sort -u

  echo
  echo "=== 認証情報が自動実行に渡るか（★値は出さない。有無と長さだけ） ==="
  #   2026-10-21: worker が `OAuth session expired` で落ちるのに、対話の `claude` は起動する。
  #   対話シェルにだけ鍵があり、cron/launchd に渡っていない、という読み。その裏取り。
  for sh in 'zsh -lic' 'zsh -lc' 'bash -lc'; do
    v=$($sh 'printenv ANTHROPIC_API_KEY' 2>/dev/null | tail -1)
    if [ -n "$v" ]; then echo "  $sh : あり（${#v} 文字）"; else echo "  $sh : 無し"; fi
  done
  v=$(printenv ANTHROPIC_API_KEY 2>/dev/null)
  if [ -n "$v" ]; then echo "  このスクリプトの環境 : あり（${#v} 文字）"; else echo "  このスクリプトの環境 : 無し"; fi
  unset v
  echo "  --- どのファイルで定義されているか（行番号だけ。値は出さない） ---"
  for rc in "$HOME/.zshrc" "$HOME/.zprofile" "$HOME/.zshenv" "$HOME/.bash_profile" "$HOME/.profile" \
            "$HOME/.agent-team.env" "$HOME/.config/agent-team/env"; do
    [ -r "$rc" ] || continue
    ln=$(grep -n 'ANTHROPIC_API_KEY' "$rc" 2>/dev/null | cut -d: -f1 | tr '\n' ',')
    [ -n "$ln" ] && echo "  $rc : $ln 行目に記述あり"
  done
  echo "  --- claude の保存済み認証（存在と更新日だけ） ---"
  for f in "$HOME/.claude/.credentials.json" "$HOME/.claude.json"; do
    [ -e "$f" ] && echo "  $f : $(date -r "$f" '+%Y-%m-%d %H:%M' 2>/dev/null)"
  done

  echo
  echo "=== 18時台に走るもの＝order-check の中身（消失は毎回 18:09〜18:11） ==="
  for f in "$HOME"/agent-team/scripts/deliver/auto_check_orders.sh \
           "$HOME"/agent-team/scripts/morning.sh \
           "$HOME"/agent-team-run/docs/worker_dispatcher.sh; do
    [ -f "$f" ] || { echo "----- $f （無い）"; continue; }
    echo "----- $f"; cat "$f"; echo
  done
} > "$OUT" 2>&1

git add -f "$OUT" >/dev/null 2>&1
git commit -q -m "diag: Mac 側の自動実行の設定を収集" >/dev/null 2>&1
for i in 1 2 3 4; do
  git push -u origin main >/dev/null 2>&1 && { echo "push しました。次のセッションで code が読みます"; exit 0; }
  sleep $((2 ** i))
done
echo "push できませんでした（$OUT は書けています）"
