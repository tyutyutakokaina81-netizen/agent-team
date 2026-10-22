#!/bin/bash
# ワーカー実行＋ログ自動送信ランチャー v2
# ・実行中: 3分ごとにログ末尾を ops/logs/worker_live.log として自動push（codeが遠隔でリアルタイム診断）
# ・終了時: ログ末尾120行+exit code を ops/logs/worker_<日時>.log として push
cd "$HOME/agent-team-run" || exit 1

# ★2026-09-23: **cron の PATH は対話シェルと違う**。これが毎朝の便が動かない真因だった。
#   09:30 便のログ＝`env: node: No such file or directory` / exit_code=127。
#   claude は `#!/usr/bin/env node` で始まる node スクリプトなので、claude 本体が見つかっても
#   **node が PATH に無ければ 127 で落ちる**。08:45 便の `$CLA` が空だったのも同じ理由。
#   ログインシェルでは Homebrew / nvm / volta が PATH を足してくれるが、cron では足されない。
#   → よく使われる場所を**存在するものだけ**先頭に足す（無害・冪等）。
for d in /opt/homebrew/bin /usr/local/bin "$HOME/.local/bin" "$HOME/.volta/bin" \
         "$HOME/.claude/local" "$HOME/.npm-global/bin"; do
  [ -d "$d" ] && case ":$PATH:" in *":$d:"*) ;; *) PATH="$d:$PATH" ;; esac
done
# nvm は版ごとにディレクトリが分かれるので、既定版→最新版の順に1つだけ拾う
if [ -z "$(command -v node 2>/dev/null)" ] && [ -d "$HOME/.nvm/versions/node" ]; then
  NVMBIN="$(ls -d "$HOME"/.nvm/versions/node/*/bin 2>/dev/null | sort -V | tail -1)"
  [ -n "$NVMBIN" ] && PATH="$NVMBIN:$PATH"
fi
export PATH

# ★2026-10-21: **PATH は直していたのに、認証情報は一切引き継いでいなかった。**
#   症状＝ログに `Failed to authenticate: OAuth session expired and could not be refreshed`、
#   exit_code=1。ところが**オーナーがターミナルで `claude` を叩くと普通に起動する**
#   （起動画面に "API Usage Billing" と出る）。つまり**ログイン切れではない**。
#   対話シェルは ~/.zshrc などで `ANTHROPIC_API_KEY` を読み込んでいて、
#   **cron / launchd はそれを読まない**ので、保存済みの OAuth に落ちて期限切れになる。
#   PATH のときとまったく同じ型＝「ログインシェルにはあるが、自動実行には無い」。
#   → ログインシェルの環境から **その1個だけ**取り出す。
#     `zsh -lic` は ~/.zprofile と ~/.zshrc の両方を読む。printenv なので**値は出力に残らない**。
if [ -z "$ANTHROPIC_API_KEY" ]; then
  # オーナーが鍵を置くための専用ファイル（あれば最優先。.gitignore 済の場所に作る）
  for ef in "$HOME/.agent-team.env" "$HOME/.config/agent-team/env"; do
    [ -r "$ef" ] && . "$ef" && break
  done
fi
# ★対話シェル（zsh -lic）は**使わない**。launchd から走るときに、.zshrc の中身次第で
#   入力待ちになって止まる恐れがある。代わりに**代入の1行だけ**を読んで評価する。
#   値が `$(security find-generic-password ...)` のような形でも、eval なら解決できる。
if [ -z "$ANTHROPIC_API_KEY" ]; then
  for rc in "$HOME/.zshenv" "$HOME/.zprofile" "$HOME/.zshrc" "$HOME/.bash_profile" "$HOME/.profile"; do
    [ -r "$rc" ] || continue
    KLINE=$(grep -E '^[[:space:]]*(export[[:space:]]+)?ANTHROPIC_API_KEY=' "$rc" 2>/dev/null | tail -1)
    if [ -n "$KLINE" ]; then
      eval "$KLINE" 2>/dev/null
      export ANTHROPIC_API_KEY
      [ -n "$ANTHROPIC_API_KEY" ] && echo "auth: $rc から読みました" && break
    fi
  done
  unset KLINE
fi
# それでも無ければ、非対話のログインシェル（-i は付けない）から1個だけ取り出す
if [ -z "$ANTHROPIC_API_KEY" ] && command -v zsh >/dev/null 2>&1; then
  K=$(zsh -lc 'printenv ANTHROPIC_API_KEY' 2>/dev/null | tail -1)
  [ -n "$K" ] && ANTHROPIC_API_KEY="$K" && export ANTHROPIC_API_KEY
  unset K
fi
# ★2026-10-21: **古いスクリプトが走ったことに気づけなかった。**
#   19:07 の便は auth: の行が1つも出ず、こちらは「直したのに効かない」と読みかけた。
#   実際は push の1分後に実行されていて、**Mac がまだ取り込んでいなかっただけ**。
#   → **版が分かる印を必ず出す。** この行が無いログは、修正前のスクリプトの出力。
# ★2026-10-23: **版の印は出していたのに、git に載るログには入っていなかった。**
#   committed されるのは `$RUNLOG`（claude 自身の出力）の tail だけで、
#   ランチャーの echo は launchd の stdout に出るだけだった。
#   そのため 10-23 の便を読んでも「どの版が走ったか」が分からず、
#   10-21 に入れた印がまるごと無駄になっていた。**印は読む場所に出す。**
#   → 行を貯めておいて、$RUNLOG の先頭に書き込む。
LAUNCHER_INFO="run_worker.sh 版: 2026-10-23 認証引き継ぎ＋版印をログへ"
# **値は絶対に出力しない。** 有無と長さだけ残す（ログは git に乗るため）。
if [ -n "$ANTHROPIC_API_KEY" ]; then
  LAUNCHER_INFO="${LAUNCHER_INFO}
auth: ANTHROPIC_API_KEY を引き継ぎました（${#ANTHROPIC_API_KEY} 文字）"
else
  LAUNCHER_INFO="${LAUNCHER_INFO}
auth: ANTHROPIC_API_KEY は見つかりません（保存済みの認証で起動します）"
fi
echo "$LAUNCHER_INFO"

# 実行中ロック（cron定期便・配車係・手動の三経路すべての二重起動防止）
LOCK="$HOME/.agent-team-dispatch/worker.lock"
mkdir -p "$(dirname "$LOCK")"
if ! mkdir "$LOCK" 2>/dev/null; then
  # 残骸ロックの回収判定（2026-07-20強化: Macスリープ等で異常終了しロックが残ると
  # 旧ロジックは最大6時間ワーカーを止めていた＝5日間便が出ない事故の一因）。
  # 「実際にworkerプロセスが生きているか」を最優先で判定し、居なければ即回収する。
  STALE=""
  OLDPID=$(cat "$LOCK/pid" 2>/dev/null)
  # ① 保持PIDが死んでいる  ② そもそもワーカー(claude -p …)が1つも走っていない  ③ 6時間超の保険
  { [ -n "$OLDPID" ] && ! kill -0 "$OLDPID" 2>/dev/null; } && STALE=1
  pgrep -f "dangerously-skip-permissions" >/dev/null 2>&1 || STALE=1
  [ -n "$(find "$LOCK" -maxdepth 0 -mmin +360 2>/dev/null)" ] && STALE=1
  if [ -n "$STALE" ]; then
    echo "（残骸ロックを回収して続行）"
    rm -rf "$LOCK" 2>/dev/null
    mkdir "$LOCK" 2>/dev/null || { echo "ロック取得失敗"; exit 0; }
  else
    echo "=== 別のワーカーが実行中のため起動しません（二重起動防止）==="
    exit 0
  fi
fi
echo $$ > "$LOCK/pid" 2>/dev/null   # 保持者PIDを記録（次回の生存判定に使う）
trap 'rm -rf "$LOCK" 2>/dev/null' EXIT

git pull origin main -q

# 配車係の自動インストール（冪等）: ownerの貼り付け作業なしで、次にこのスクリプトが
# 走った時点（朝7:17のcron便など）で dispatcher が crontab に登録される。
if ! crontab -l 2>/dev/null | grep -q worker_dispatcher.sh; then
  bash docs/worker_dispatcher.sh --install || true
fi

TS=$(date +%Y-%m-%d_%H%M)

# 送信専用クローン（ワーカーのgit操作と衝突させない）
LOGCLONE="$HOME/.agent-team-logclone"
URL=$(git remote get-url origin)
if [ ! -d "$LOGCLONE/.git" ]; then git clone --depth 1 -q "$URL" "$LOGCLONE"; fi


# ★2026-09-23: **ここが空のまま走っていた**。2026-09-23 08:45 の便のログが
#   `run_worker.sh: line 51: : command not found` で埋まっており（空文字列を実行した形）、
#   それでも `exit_code=0` で「成功」として報告されていた。キューに3本あるのに公開0本。
#   原因の第一候補は **cron の PATH が対話シェルと違う**こと。`command -v claude` は
#   ログインシェルでは当たるが、cron の最小 PATH では外れる。
#   → 代表的な導入先を順に見て、**見つからなければはっきり落とす**（黙って空実行しない）。
CLA=$(command -v claude 2>/dev/null)
if [ -z "$CLA" ]; then
  for c in "$HOME/.claude/local/claude" \
           "$HOME/.local/bin/claude" \
           "/opt/homebrew/bin/claude" \
           "/usr/local/bin/claude" \
           "$HOME/.npm-global/bin/claude" \
           "$HOME/node_modules/.bin/claude"; do
    [ -x "$c" ] && CLA="$c" && break
  done
fi
if [ -z "$(command -v node 2>/dev/null)" ]; then
  MSG="node が見つかりません（PATH=${PATH}）。claude は node スクリプトなので node が無いと 127 で落ちます。node の場所を上の PATH 追加リストに足してください。"
  echo "=== 起動できません: $MSG ==="
  cd "$LOGCLONE" 2>/dev/null && git pull --rebase -q origin main 2>/dev/null
  mkdir -p ops/logs
  { echo "launcher_error=node_not_found"; echo "$MSG"; echo "exit_code=127"; } > "ops/logs/worker_${TS}.log"
  git add ops/logs/ 2>/dev/null
  git commit -qm "log: worker run ${TS} could not start (node not found)" 2>/dev/null
  git push -q origin main 2>/dev/null || true
  exit 127
fi

if [ -z "$CLA" ]; then
  MSG="claude コマンドが見つかりません（PATH=${PATH}）。cron から起動すると PATH が対話シェルと違うため、フルパスで指定するか PATH を通してください。"
  echo "=== 起動できません: $MSG ==="
  mkdir -p "$HOME/agent-team-run/ops/logs"
  { echo "launcher_error=claude_not_found"; echo "$MSG"; echo "exit_code=127"; } \
    > "$HOME/agent-team-run/ops/logs/worker_${TS}.log"
  cd "$LOGCLONE" 2>/dev/null && git pull --rebase -q origin main 2>/dev/null
  mkdir -p ops/logs
  { echo "launcher_error=claude_not_found"; echo "$MSG"; echo "exit_code=127"; } > "ops/logs/worker_${TS}.log"
  git add ops/logs/ 2>/dev/null
  git commit -qm "log: worker run ${TS} could not start (claude not found)" 2>/dev/null
  git push -q origin main 2>/dev/null || true
  exit 127
fi

echo "=== ワーカー開始 ${TS}（実行中も3分ごとに状況が自動送信されます）==="
# --dangerously-skip-permissions: -p(非対話)では権限プロンプトに答えられず、報告書き込み/git pushが
# 全部ブロックされる（2026-07-04 11:35便で実証: 報告もログも届かなかった）。owner環境の自リポジトリ限定運用。
# ★2026-09-23: `| tee` を挟むとパイプラインの終了コードは **tee のもの**になり、
#   本体が落ちても RC=0 になる。実際、claude が空で実行できなかった便も rc=0 で
#   「成功」と報告されていた。本体の終了コードを拾うため PIPESTATUS を使う。
# ★2026-09-23: worker.log は `tee -a` で**積み上がる**ファイルで、送信しているのはその tail。
#   そのため「今回の便のログ」を読んでいるつもりで、**何便も前の失敗が混ざって**いた
#   （08:45 便のログは同じエラーが数十行並んでいたが、実際は1便1行×多数便だった）。
#   → 今回分だけの RUNLOG を別に持ち、判定も送信もそちらを見る。
# リポジトリの外に置く＝ops/logs/ を git add したときに生ログまで載らないようにする。
RUNLOG="$HOME/.agent-team-dispatch/worker_run_${TS}.out"
mkdir -p "$(dirname "$RUNLOG")"
# ★ランチャーの情報を**ログの先頭に置く**。送信されるのは $RUNLOG の tail -120 なので、
#   出力が長い便では流れてしまうが、短い便（＝失敗便）では必ず残る。
#   失敗便こそ版を知りたいので、これで足りる。
{ echo "$LAUNCHER_INFO"; echo "claude: $CLA"; echo "---- ここからワーカーの出力 ----"; } > "$RUNLOG"
set -o pipefail
"$CLA" -p --dangerously-skip-permissions "$(cat docs/worker-prompt.txt)" 2>&1 | tee -a worker.log >> "$RUNLOG" &
PID=$!

# ライブ送信ループ（ワーカーが生きている間だけ）
(
  while kill -0 $PID 2>/dev/null; do
    sleep 180
    kill -0 $PID 2>/dev/null || break
    cd "$LOGCLONE" && git pull --rebase -q origin main 2>/dev/null
    mkdir -p ops/logs
    { echo "# live tail $(date '+%H:%M:%S') (running)"; tail -80 "$RUNLOG"; } > ops/logs/worker_live.log
    git add ops/logs/worker_live.log 2>/dev/null
    git commit -qm "log(live): worker running $(date '+%H:%M')" 2>/dev/null
    git push -q origin main 2>/dev/null || true
  done
) &
LIVEPID=$!

wait $PID
RC=$?
kill $LIVEPID 2>/dev/null

# ★2026-09-23: ログイン切れは本体が「Not logged in · Please run /login」と1行出して
#   すぐ終わるだけで、キューがあっても1本も公開されない。終了コードだけ見ても分からないので、
#   **ログの文言で検出して rc に出す**（code 側の R33 がこれを見る）。
if grep -q "Not logged in" "$RUNLOG" 2>/dev/null; then
  echo "launcher_error=not_logged_in（Mac の claude が未ログイン。ターミナルで claude を起動し /login）" | tee -a "$RUNLOG"
  [ "$RC" = "0" ] && RC=126
fi
# ★2026-10-21: **これと「未ログイン」は別物**。
#   `Failed to authenticate: OAuth session expired and could not be refreshed` は、
#   **対話では普通に起動するのに自動実行だけ落ちる**ときに出る。
#   原因は認証情報が cron / launchd に渡っていないことで、`/login` では直らない
#   （実際、この文言を「ログイン切れ」と読んで `/login` を案内して外した）。
#   区別できる形で記録する。
if grep -q "OAuth session expired\|Failed to authenticate" "$RUNLOG" 2>/dev/null; then
  echo "launcher_error=auth_not_inherited（認証情報が自動実行に渡っていない。対話で claude が起動するなら /login では直らない。\$HOME/.agent-team.env に ANTHROPIC_API_KEY を置くか、ログインシェルの設定を確認）" | tee -a "$RUNLOG"
  [ "$RC" = "0" ] && RC=125
fi

# 最終ログ送信
cd "$LOGCLONE" && git pull --rebase -q origin main 2>/dev/null
mkdir -p ops/logs
{ tail -120 "$RUNLOG"; echo "exit_code=${RC}"; } > "ops/logs/worker_${TS}.log"
echo "# finished $(date '+%H:%M:%S') rc=${RC}" > ops/logs/worker_live.log
git add ops/logs/ 2>/dev/null
git commit -qm "log: worker run ${TS} finished (rc=${RC})" 2>/dev/null
git push -q origin main 2>/dev/null || true
echo "=== 終了 rc=${RC}（ログ送信済み・codeが遠隔診断できます）==="
