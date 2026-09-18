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
    echo "既にあります: $KEYFILE（中身は表示しません）"
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

if [ "${1:-}" = "--install" ]; then
  echo "== tweepy を入れます =="
  python3 -m pip install --user tweepy || pip3 install --user tweepy
  exit $?
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
    if [ -n "$val" ]; then echo "  $v : 設定済み"; else echo "  $v : ★未設定"; miss=1; fi
  done
  # 3) tweepy
  if python3 -c "import tweepy" 2>/dev/null; then
    echo "tweepy : あり"
  else
    echo "tweepy : ★なし（bash ops/run_x.sh --install で入ります）"
    miss=1
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
      python3 ops/x_poster.py --go
    fi
  else
    echo "--- DRY-RUN（投稿しません。次に出る文面の確認）---"
    python3 ops/x_poster.py
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
  for i in 1 2 3 4; do
    git push -u origin "$BR" && break
    echo "push 失敗、$((2**i))秒待って再試行"; sleep $((2**i))
  done
fi
echo "ログ: $(pwd)/${LOG}"
