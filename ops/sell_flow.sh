#!/bin/bash
# 有料note(¥500)を売れる状態にするまでを、1回の実行で通す（オーナーのMacで実行）。
#
#   bash ops/sell_flow.sh                    # 何をするか表示するだけ（保存しない）
#   bash ops/sell_flow.sh --go               # 実行する
#   bash ops/sell_flow.sh --go --login       # noteログインから始める
#   bash ops/sell_flow.sh --go --paid-url https://note.com/xxx/n/nxxxx
#                                            # 有料noteが公開済みのとき、URLだけ渡して④から再開
#
# code(A1)は note.com に接続できないため、note側の操作はすべてここに集約している。
# やること（この順・前が失敗したら次へ進まない）:
#   ① 有料note(¥500)を公開し、公開URLを拾う
#   ② 拾ったURLを無料の入口記事の <<有料noteURL>> に差し込む
#   ③ 入口記事を公開する
#   ④ 結果を outbox に報告して commit & push する
#
# ★順序が命：入口記事を先に出すと、行き先の無いリンクだけが残る。
#   だから URL が取れなかった時点で、このスクリプトは③へ進まずに止まる。
set -uo pipefail
cd "$(dirname "$0")/.."

PAID="CMO/outputs/2026-08-20_有料note_AIに会社を運営させた3か月_161本公開して売上0円.md"
FREE="CMO/outputs/2026-08-21_note記事_AIは一度もやめましょうと言わなかった.md"
PRICE=500
PLACEHOLDER="<<有料noteURL>>"
STATE="ops/.sell_flow_state"

GO=0; LOGIN=0; PAID_URL=""
while [ $# -gt 0 ]; do
  case "$1" in
    --go)       GO=1 ;;
    --login)    LOGIN=1 ;;
    --paid-url) shift; PAID_URL="${1:-}" ;;
    *) echo "⚠️ 不明な引数: $1（無視します）" ;;
  esac
  shift
done

BR="$(git rev-parse --abbrev-ref HEAD)"
mkdir -p ops/logs
TS="$(date +%Y-%m-%d_%H%M%S)"
LOG="ops/logs/sell_${TS}.log"
exec > >(tee -a "$LOG") 2>&1

PYBIN="python3"; [ -x "$HOME/.note_venv/bin/python" ] && PYBIN="$HOME/.note_venv/bin/python"
PUBDIR="CDO/outputs/note_publisher"

echo "=== sell_flow ${TS} (branch=${BR}) ==="
[ $GO -eq 0 ] && echo "🚦 DRY-RUN（何も公開・保存しません）。実行するには --go を付けてください。"

# 前回の未完マージ等で git が詰まっていると全部止まるので先に解消してから同期
find .git -name '*.lock' -delete 2>/dev/null || true
git merge --abort 2>/dev/null || true
git rebase --abort 2>/dev/null || true
git pull --rebase origin "$BR" || git pull origin "$BR" || \
  { echo "⚠️ pull失敗→origin/${BR}へ強制同期"; git fetch origin "$BR" && git reset --hard "origin/${BR}"; }

# 記事が手元にあるか（main を reset すると消えるので、ここで必ず確かめる）
missing=0
for f in "$PAID" "$FREE"; do
  if [ ! -f "$f" ]; then echo "✗ 見つかりません: $f"; missing=1; fi
done
if [ $missing -eq 1 ]; then
  echo ""
  echo "取り直してから再実行してください:"
  echo "  git fetch origin main && git reset --hard origin/main"
  exit 1
fi

# 空の有料note3本が店頭に残っていないか（新しい商品を並べる前に下げる）
echo ""
echo "※ 8/19の事故で本文7文字の有料note3本が¥300で公開されたままなら、先に下げてください:"
echo "    bash ops/finish_pending.sh --go"

if [ $LOGIN -eq 1 ]; then
  echo ""
  echo "--- noteログイン（ブラウザが開きます。ログイン後 Enter）---"
  "$PYBIN" "$PUBDIR/publish_to_note.py" --login || echo "⚠️ ログイン中断"
fi

# ---- ① 有料note(¥500)を公開して、URLを拾う ----
echo ""
echo "=== ① 有料note(¥${PRICE})を公開 ==="
# 既に置換済み＝この工程は終わっている（二重公開を防ぐ）
if ! grep -qF "$PLACEHOLDER" "$FREE"; then
  echo "✅ 入口記事のURLは差し込み済みです。①②をとばします。"
  PAID_URL="$(python3 ops/_note_url.py < "$FREE" || true)"
  echo "   差し込み済みURL: ${PAID_URL:-（見つかりません・手で確認してください）}"
elif [ -n "$PAID_URL" ]; then
  PAID_URL="$(echo "$PAID_URL" | python3 ops/_note_url.py || true)"
  if [ -z "$PAID_URL" ]; then
    echo "✗ --paid-url の形式が正しくありません（https://note.com/<ユーザー>/n/<記事ID> の形で渡してください）。"
    exit 1
  fi
  echo "✅ --paid-url が渡されたので、公開ずみとして扱います: $PAID_URL"
elif [ $GO -eq 0 ]; then
  echo "DRY-RUN: ここで下記を実行します"
  echo "  $PYBIN $PUBDIR/publish_paid_note.py --article \"$PAID\" --price $PRICE --publish"
  # 解析だけは実際に走らせる（価格・無料/有料の字数がここで出る＝公開前の目視確認）
  "$PYBIN" "$PUBDIR/publish_paid_note.py" --article "$PAID" --price "$PRICE" 2>&1 | grep -E "記事解析OK|✗" || true
else
  out="$("$PYBIN" "$PUBDIR/publish_paid_note.py" --article "$PAID" --price "$PRICE" --publish 2>&1)"
  echo "$out"
  # 「🔗 想定公開URL: …」と「✅ 公開リクエスト送信。最終URL: …」の両方から拾う
  # URLらしき文字列ではなく「実際に開ける形か」まで検証して受け取る（_note_url.py）
  PAID_URL="$(echo "$out" | python3 ops/_note_url.py || true)"
fi

if [ -z "$PAID_URL" ]; then
  echo ""
  if [ $GO -eq 0 ]; then
    # DRY-RUNでは公開していないのでURLが無いのは正常。ここで警告を出すと本物の失敗と紛らわしい。
    echo "（DRY-RUN: 実行時はここで公開URLを拾って、②③へ進みます）"
  else
    echo "✗ 有料noteのURLが取れませんでした。**入口記事は公開しません**（行き先の無いリンクを出さないため）。"
    echo "  noteの管理画面で公開されているか見て、URLが分かったら:"
    echo "    bash ops/sell_flow.sh --go --paid-url <そのURL>"
    echo "有料note公開=URL取得失敗 (${TS})" >> "$STATE"
    exit 1
  fi
fi

# ---- ② URLを入口記事に差し込む ----
echo ""
echo "=== ② 入口記事にURLを差し込む ==="
if grep -qF "$PLACEHOLDER" "$FREE"; then
  if [ $GO -eq 0 ]; then
    echo "DRY-RUN: ${PLACEHOLDER} を有料noteのURLに置換します（${FREE}）"
  else
    "$PYBIN" - "$FREE" "$PLACEHOLDER" "$PAID_URL" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); ph, url = sys.argv[2], sys.argv[3]
t = p.read_text(encoding="utf-8")
n = t.count(ph)
p.write_text(t.replace(ph, url), encoding="utf-8")
print(f"✅ {n}箇所を差し替えました → {url}")
PY
  fi
else
  echo "（差し込み済みなので、そのまま）"
fi

# ---- ③ 入口記事を公開 ----
echo ""
echo "=== ③ 無料の入口記事を公開 ==="
published=0
if [ $GO -eq 0 ]; then
  echo "DRY-RUN: $PYBIN $PUBDIR/publish_to_note.py --text-only --article \"$FREE\""
elif grep -qF "$PLACEHOLDER" "$FREE"; then
  echo "✗ まだプレースホルダが残っています。安全のため公開しません。"
elif [ -f "$STATE" ] && grep -q "^free_published=" "$STATE"; then
  # 再実行で同じ記事をもう一度公開しないための歯止め。出し直したいときは STATE の行を消す。
  FREE_URL="$(sed -n 's/^free_published=//p' "$STATE" | tail -1)"
  echo "✅ 入口記事は公開済みです（${FREE_URL}）。とばします。"
  echo "   出し直す場合は ${STATE} の free_published= の行を削除してから再実行してください。"
  published=1
else
  out2="$("$PYBIN" "$PUBDIR/publish_to_note.py" --text-only --article "$FREE" 2>&1)"; rc=$?
  echo "$out2"
  if [ $rc -eq 0 ]; then
    published=1
    FREE_URL="$(echo "$out2" | python3 ops/_note_url.py || true)"
    echo "free_published=${FREE_URL}" >> "$STATE"
  else
    echo "⚠️ 入口記事の公開に失敗しました（有料noteは公開済みのはずなので、①はやり直さないでください）。"
    echo "   題材ゲートで止まった場合のみ: $PYBIN $PUBDIR/publish_to_note.py --text-only --allow-topic-dup --article \"$FREE\""
  fi
fi

if [ $GO -eq 0 ]; then
  echo ""
  echo "🚦 DRY-RUNだったので、何も変更していません。実行は: bash ops/sell_flow.sh --go"
  exit 0
fi

# ---- ④ 報告 & push ----
echo ""
echo "=== ④ 報告とpush ==="
body="【有料note ¥${PRICE}】${PAID_URL:-URL取得できず}
【入口記事(無料)】$( [ $published -eq 1 ] && echo "公開 ${FREE_URL:-URL不明}" || echo "未公開（要対応）" )
log: ${LOG}"
python3 ops/process_inbox.py post --from cowork --to code --type report \
  --title "sell_flow 結果 ${TS}" --body "$body" || true

git add -A
git commit -m "cowork: sell_flow paid=${PAID_URL:-none} free=$( [ $published -eq 1 ] && echo published || echo pending ) (${TS})" || true
for i in 1 2 3 4; do git push origin "$BR" && break || sleep $((2**i)); done

echo ""
echo "=== 完了 ==="
echo "有料note: ${PAID_URL:-取得できず}"
echo "入口記事: $( [ $published -eq 1 ] && echo "${FREE_URL:-公開済み(URL不明)}" || echo "未公開" )"
echo "このURLをClaudeに貼れば、台帳とSTATEを更新します。"
