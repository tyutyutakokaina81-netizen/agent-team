#!/bin/bash
# 保留中の note.com 作業を、1回の実行でまとめて片づける（オーナーのMacで実行）。
#
#   bash ops/finish_pending.sh            # 何をするか表示するだけ（保存しない）
#   bash ops/finish_pending.sh --go       # 実行する
#   bash ops/finish_pending.sh --go --login   # noteログインから始める
#
# code(A1)は note.com に接続できないため、note側の操作はすべてここに集約している。
# やること（この順で・前が失敗しても次へ進む）:
#   ① 空の有料note3本を「下書きに戻す」＝¥300の値札が付いた7文字の記事を店頭から下げる（最優先）
#   ② 無料キュー(drafts/queue/)の記事を公開する
#   ③ 結果を outbox に報告し、commit & push する
set -uo pipefail
cd "$(dirname "$0")/.."

GO=0; LOGIN=0
for a in "$@"; do
  case "$a" in
    --go)    GO=1 ;;
    --login) LOGIN=1 ;;
  esac
done

BR="$(git rev-parse --abbrev-ref HEAD)"
mkdir -p ops/logs
TS="$(date +%Y-%m-%d_%H%M%S)"
LOG="ops/logs/finish_${TS}.log"
exec > >(tee -a "$LOG") 2>&1

PYBIN="python3"; [ -x "$HOME/.note_venv/bin/python" ] && PYBIN="$HOME/.note_venv/bin/python"
PUBDIR="CDO/outputs/note_publisher"

echo "=== finish_pending ${TS} (branch=${BR}) ==="
if [ $GO -eq 0 ]; then
  echo "🚦 DRY-RUN（何も保存しません）。実行するには --go を付けてください。"
fi

# 前回の未完マージ等で git が詰まっていると全部止まるので先に解消してから同期
find .git -name '*.lock' -delete 2>/dev/null || true
git merge --abort 2>/dev/null || true
git rebase --abort 2>/dev/null || true
git pull --rebase origin "$BR" || git pull origin "$BR" || \
  { echo "⚠️ pull失敗→origin/${BR}へ強制同期"; git fetch origin "$BR" && git reset --hard "origin/${BR}"; }

if [ $LOGIN -eq 1 ]; then
  echo "--- noteログイン（ブラウザが開きます。ログイン後 Enter）---"
  "$PYBIN" "$PUBDIR/publish_to_note.py" --login || echo "⚠️ ログイン中断"
fi

# ---- ① 空の有料note3本を下書きに戻す（最優先） ----
# 2026-08-19 の事故＝見出し抽出バグの修正前コードで、本文7文字のまま¥300で公開されたもの。
# 削除ではなく「下書きに戻す」＝取り消しが利く方を選ぶ。
EMPTY_IDS="n94864fee1d83 n752e3adfbaf2 n5a495d8e38c3"
echo ""
echo "=== ① 空の有料note を下書きに戻す ==="
unpub_ok=0; unpub_ng=0; unpub_detail=""
for nid in $EMPTY_IDS; do
  echo "--- $nid"
  if [ $GO -eq 1 ]; then
    out="$("$PYBIN" "$PUBDIR/_cowork_unpublish_by_id.py" "$nid" --go 2>&1)"
  else
    out="$("$PYBIN" "$PUBDIR/_cowork_unpublish_by_id.py" "$nid" 2>&1)"
  fi
  echo "$out"
  # CARD_NOT_FOUND = 一覧に無い＝既に下書き/削除済みの可能性が高い（成功と同じ扱いにはしない）
  if echo "$out" | grep -q "^DONE:"; then
    unpub_ok=$((unpub_ok+1)); unpub_detail="${unpub_detail} ${nid}:下書きに戻した"
  elif echo "$out" | grep -q "CARD_NOT_FOUND"; then
    unpub_detail="${unpub_detail} ${nid}:一覧に無し(既に非公開か要目視)"
  elif echo "$out" | grep -q "DRY-RUN"; then
    unpub_detail="${unpub_detail} ${nid}:DRY(対象を確認)"
  else
    unpub_ng=$((unpub_ng+1)); unpub_detail="${unpub_detail} ${nid}:失敗"
  fi
done
echo "=== ①結果: 下書きに戻した ${unpub_ok} / 失敗 ${unpub_ng} ==="

# ---- ② 無料キューの公開 ----
echo ""
echo "=== ② 無料キューの公開 ==="
shopt -s nullglob
published=0; failed=0; ok_list=""; fail_reasons=""
for f in drafts/queue/*.md; do
  name="$(basename "$f")"
  echo "--- 公開試行: ${name}"
  if [ $GO -eq 0 ]; then
    echo "    DRY-RUN: ここで公開します"
    continue
  fi
  out="$("$PYBIN" "$PUBDIR/publish_to_note.py" --text-only --article "$f" 2>&1)"; rc=$?
  echo "$out"
  if [ $rc -eq 0 ]; then
    mkdir -p drafts/published
    git mv "$f" "drafts/published/$name" 2>/dev/null || mv "$f" "drafts/published/$name"
    published=$((published+1)); ok_list="${ok_list} ${name}"
    echo "$out" | grep -q "写真サムネは未設定" && echo "    ⚠️ サムネ未設定（note側UI変更の可能性・手動設定してください）"
  else
    failed=$((failed+1))
    reason="$(echo "$out" | grep -m1 -E '✗|エラー|Error|重複ゲート|ログイン|Timeout' | sed 's/^[[:space:]]*//' | cut -c1-100)"
    [ -z "$reason" ] && reason="$(echo "$out" | tail -1 | cut -c1-100)"
    fail_reasons="${fail_reasons}
    - ${name}: ${reason}"
  fi
done
echo "=== ②結果: 公開 ${published} / 失敗 ${failed} ==="

if [ $GO -eq 0 ]; then
  echo ""
  echo "🚦 DRY-RUNだったので、何も変更していません。実行は: bash ops/finish_pending.sh --go"
  exit 0
fi

# ---- ③ 報告 & push ----
body="【空note下書き化】成功 ${unpub_ok} / 失敗 ${unpub_ng} ―${unpub_detail}
【無料公開】公開 ${published} 件 / 失敗 ${failed} 件（log: ${LOG}）"
[ -n "$ok_list" ] && body="${body} | OK:${ok_list}"
[ -n "$fail_reasons" ] && body="${body}
【失敗理由】${fail_reasons}"
python3 ops/process_inbox.py post --from cowork --to code --type report \
  --title "finish_pending 結果 ${TS}" --body "$body" || true

git add -A
git commit -m "cowork: finish_pending unpub=${unpub_ok}/3 publish=${published}/$((published+failed)) (${TS})" || true
for i in 1 2 3 4; do git push origin "$BR" && break || sleep $((2**i)); done
echo ""
echo "=== 完了。空note下書き化 ${unpub_ok}/3 ・公開 ${published} 件 ==="
echo "公開URLは上のログに出ています。Claudeに貼れば台帳を更新します。"
