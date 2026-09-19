#!/bin/bash
# ops/run_x.sh — 【C】X(旧Twitter)投稿を動かす（owner の Mac で実行）
#
#   bash ops/run_x.sh              # 診断＋DRY-RUN（投稿しない。今なにが足りないかを出す）
#   bash ops/run_x.sh --setup      # 認証キーの置き場所 ~/.x_keys.env を作る（値は自分で書く）
#   bash ops/run_x.sh --install    # tweepy を入れる（pip install --user tweepy）
#   bash ops/run_x.sh --go         # 先頭1スレッドだけ投稿する（1回1スレッド・連投しない）
#
# 安全のため:
#   ・キーは ~/.x_keys.env（リポジトリの外）だけに置く。このスクリプトは値を絶対に表示しない。
#   ・--go は1スレッドで止まる。280字超があれば投稿せず中止する（x_poster.py 側の仕様）。
set -u
cd "$(dirname "$0")/.." || exit 1
KEYFILE="$HOME/.x_keys.env"
TS="$(date +%Y-%m-%d_%H%M%S)"
LOG="ops/logs/x_run_${TS}.log"
mkdir -p ops/logs

if [ "${1:-}" = "--setup" ]; then
  if [ -f "$KEYFILE" ]; then
    echo "既にあります: ${KEYFILE}（中身は表示しません）"
  else
    cat > "$KEYFILE" <<'KEYS'
# X API の認証情報。このファイルはリポジトリの外にあり、git には絶対に入らない。
# 取得: https://developer.x.com/ → Projects & Apps → Keys and tokens
#   ・App permissions を "Read and write" にしてから Access Token を作り直すこと
#     （Read only のまま作ったトークンでは投稿が 403 で落ちる）
export X_API_KEY=""
export X_API_SECRET=""
export X_ACCESS_TOKEN=""
export X_ACCESS_SECRET=""
KEYS
    chmod 600 "$KEYFILE"
    echo "作りました: $KEYFILE"
  fi
  echo "→ このファイルを開いて4つの値を書いてから、もう一度 bash ops/run_x.sh を実行してください。"
  exit 0
fi

# tweepy はここに入れる。macOS の Homebrew python は PEP 668 で
# **システム全体への pip install を拒否する**（2026-09-19 実測: externally-managed-environment）。
# --break-system-packages で強行すると Homebrew を壊しうるので、**専用の venv を作る**。
VENV="$HOME/.agent_venv"
VPY="$VENV/bin/python3"
[ -x "$VPY" ] || VPY="python3"     # venv が無ければ素のpython（tweepy 無しでも診断は動く）

# ---- キーを対話で入れる（エディタを開かずに済む）----
# 2026-09-19: ファイルを開いて4か所を書き換える作業がボトルネックになっていた。
# `read -rs` は**画面に出さず**、コマンド履歴にも残らない（引数ではなく標準入力で受けるため）。
if [ "${1:-}" = "--keys" ]; then
  echo "X の認証情報を4つ入力します。**画面には表示されません**。"
  echo "（developer.x.com → Projects & Apps → Keys and tokens で表示されるもの）"
  echo "途中でやめるときは Ctrl+C。"
  echo ""
  ask() {   # $1=表示名  → 変数 ANS に入れる。前後の空白は落とす。
    printf '  %s を貼って Enter: ' "$1"
    IFS= read -rs ANS
    echo ""
    ANS="$(printf '%s' "$ANS" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^"//' -e 's/"$//')"
  }
  ask "API Key";           K1="$ANS"
  ask "API Key Secret";    K2="$ANS"
  ask "Access Token";      K3="$ANS"
  ask "Access Token Secret"; K4="$ANS"
  bad=0
  for pair in "API Key:$K1" "API Key Secret:$K2" "Access Token:$K3" "Access Token Secret:$K4"; do
    nm="${pair%%:*}"; vl="${pair#*:}"
    if [ -z "$vl" ]; then echo "  ★$nm が空です"; bad=1
    elif [ ${#vl} -lt 15 ]; then echo "  ★$nm が短すぎます（${#vl}文字）"; bad=1; fi
  done
  if [ "$bad" -ne 0 ]; then
    echo "✗ 入力に問題があるので**ファイルは書き換えていません**。もう一度 --keys を実行してください。"
    exit 1
  fi
  umask 077
  cat > "$KEYFILE" <<KEYS
# X API の認証情報（$(date +%Y-%m-%d) に run_x.sh --keys で設定）。
# このファイルはリポジトリの外にあり、git には入らない。値は画面にも出していない。
export X_API_KEY="$K1"
export X_API_SECRET="$K2"
export X_ACCESS_TOKEN="$K3"
export X_ACCESS_SECRET="$K4"
KEYS
  chmod 600 "$KEYFILE"
  echo "✅ 保存しました: $KEYFILE（本人だけが読める権限）"
  echo "→ 続けて: bash ops/run_x.sh   で接続を確認します"
  exit 0
fi

if [ "${1:-}" = "--install" ]; then
  echo "== tweepy を入れます（専用の仮想環境 $VENV を作ります）=="
  echo "   理由: macOS の python は PEP 668 でシステムへの pip install を拒否します。"
  echo "   Homebrew を壊さないよう、リポジトリの外に専用環境を作ってそこへ入れます。"
  python3 -m venv "$VENV" || { echo "✗ venv を作れませんでした"; exit 1; }
  "$VENV/bin/pip" install --quiet --upgrade pip
  "$VENV/bin/pip" install tweepy && echo "✅ 入りました: $VENV" || { echo "✗ tweepy の導入に失敗"; exit 1; }
  echo "→ もう一度 bash ops/run_x.sh を実行してください（この venv を自動で使います）"
  exit 0
fi

git pull --rebase --autostash || echo "⚠️ git pull に失敗。ローカルのまま続行します"

{
  echo "### X投稿 ${TS}"
  echo "--- 前提チェック（値は表示しません）---"
  # 1) キーファイル
  if [ -f "$KEYFILE" ]; then
    echo "認証ファイル $KEYFILE : あり"
    # shellcheck disable=SC1090
    . "$KEYFILE"
  else
    echo "認証ファイル $KEYFILE : ★なし（bash ops/run_x.sh --setup で作れます）"
  fi
  # 2) 環境変数（存在の有無だけ）
  miss=0
  for v in X_API_KEY X_API_SECRET X_ACCESS_TOKEN X_ACCESS_SECRET; do
    eval "val=\${$v:-}"   # macOS の bash 3.2 でも動く書き方（${!v} を避ける）
    if [ -z "$val" ]; then
      echo "  $v : ★未設定"; miss=1
    else
      # **値そのものは絶対に出さない**。長さと「よくある貼り間違い」だけ見る。
      len=${#val}
      note=""
      case "$val" in
        *" "*)   note=" ★空白が混ざっています（前後を削ってください）" ;;
        \"*|*\") note=" ★引用符が値の中に入っています" ;;
        "<"*)    note=" ★<...> のままです（実際の値に置き換えてください）" ;;
      esac
      # X のキーはおおむね 20〜60文字。極端に短いのは貼り損ね。
      if [ "$len" -lt 15 ]; then note="${note} ★短すぎます（${len}文字）＝貼り損ねの可能性"; fi
      echo "  $v : 設定済み（${len}文字）${note}"
      [ -n "$note" ] && miss=1
    fi
  done
  # 3) tweepy
  if "$VPY" -c "import tweepy" 2>/dev/null; then
    echo "tweepy : あり（${VPY}）"
  else
    echo "tweepy : ★なし（bash ops/run_x.sh --install で入ります）"
    miss=1
  fi
  # 3b) 実際に X に繋がるかを**投稿せずに**確かめる（読み取りだけ）。
  #     「設定済み」と出ているのにキーが古い/権限が Read only、という失敗は
  #     --go まで分からなかった。先に分かれば貼り直しが1回で済む。
  if [ "$miss" -eq 0 ]; then
    echo "接続確認（投稿はしません）:"
    "$VPY" - <<'PYEOF' || true
import os, sys
try:
    import tweepy
except Exception as e:
    print("  ? tweepy を読み込めない:", e); sys.exit(0)
c = tweepy.Client(consumer_key=os.environ["X_API_KEY"],
                  consumer_secret=os.environ["X_API_SECRET"],
                  access_token=os.environ["X_ACCESS_TOKEN"],
                  access_token_secret=os.environ["X_ACCESS_SECRET"])
try:
    me = c.get_me()
    u = getattr(me, "data", None)
    print(f"  ✅ 認証OK: @{getattr(u, 'username', '?')} として接続できました")
except Exception as e:
    msg = str(e)
    print(f"  ✗ 認証に失敗: {type(e).__name__}: {msg[:160]}")
    if "401" in msg or "Unauthorized" in msg:
        print("     → キーが違う/古い可能性。4つを developer.x.com で作り直してください。")
    elif "403" in msg or "Forbidden" in msg:
        print("     → 権限不足の可能性。**App permissions を Read and write にしてから**")
        print("        Access Token を作り直す必要があります（順番が逆だと403）。")
    elif "429" in msg:
        print("     → レート制限。しばらく待って再実行してください。")
PYEOF
  fi

  # 4) 投稿実績
  if [ -f ops/logs/x_posted.tsv ]; then
    echo "投稿実績 : $(wc -l < ops/logs/x_posted.tsv) 件（ops/logs/x_posted.tsv）"
  else
    echo "投稿実績 : 0件（ops/logs/x_posted.tsv がまだ無い）"
  fi

  echo
  if [ "${1:-}" = "--go" ]; then
    if [ "$miss" -ne 0 ]; then
      echo "✗ 前提が足りないので投稿しません。上の ★ を埋めてから再実行してください。"
    else
      echo "--- 先頭1スレッドを投稿します ---"
      "$VPY" ops/x_poster.py --go
    fi
  else
    echo "--- DRY-RUN（投稿しません。次に出る文面の確認）---"
    "$VPY" ops/x_poster.py
    echo
    echo "問題なければ:  bash ops/run_x.sh --go"
  fi
} 2>&1 | tee "$LOG"

echo
echo "== 結果を code に渡す（commit & push）=="
git add -A ops/logs ops/x_queue.txt 2>/dev/null
if git diff --cached --quiet; then
  echo "（変更なし）"
else
  git commit -q -m "owner: X投稿の実行ログ ${TS}" && echo "commit した"
  BR="$(git rev-parse --abbrev-ref HEAD)"
  # detached HEAD のまま push すると "not a full refname" で4回とも失敗する（2026-09-19 実測）。
  if [ "$BR" = "HEAD" ]; then
    echo "⚠️ ブランチから外れているので push しません。git switch main で戻してから、もう一度実行してください。"
  else
    for i in 1 2 3 4; do
      git push -u origin "$BR" && break
      echo "push 失敗、$((2**i))秒待って再試行"; sleep $((2**i))
    done
  fi
fi
echo "ログ: $(pwd)/${LOG}"
