#!/bin/bash
# cowork 配信デーモン — オーナーのMacで実行（手動 or launchd/cron）。
# code が物理的にできない「note公開」を自動化し、★確認作業も自動化★する：
#   現ブランチを pull → キュー公開 → 全出力をログ保存 → 結果を outbox 報告 → commit & push。
# これにより、オーナーがコンソールを目視して貼り付けなくても、
# code が repo の ops/logs/ と ops/outbox/ を読んで結果を確認できる。
#
# ★安全ゲート（2026-06-19 追加・6/12インシデント再発防止）★
#   1. 本番公開ゲート：`ops/PUBLISH_ENABLED` が存在するときだけ本番公開する。
#      無ければ全件 --draft（下書き保存のみ）で動作し、本番公開しない。
#      → note側の棚卸し（再開条件①③）が完了してからオーナーがフラグを立てる：
#         touch ops/PUBLISH_ENABLED        # 本番公開ON
#         rm   ops/PUBLISH_ENABLED         # 本番公開OFF（下書きのみに戻す）
#   2. 未来日付ガード：ファイル名日付が今日より未来のキューはスキップ（誤公開防止）。
#   3. 冪等化：publish_to_note.py が published_log.tsv で二重公開を防止。
set -uo pipefail
cd "$(dirname "$0")/.."

BR="$(git rev-parse --abbrev-ref HEAD)"
mkdir -p ops/logs
TS="$(date +%Y-%m-%d_%H%M%S)"
TODAY="$(date +%F)"
LOG="ops/logs/publish_${TS}.log"

# 全標準出力/エラーをログにも複製（確認作業の自動化の中核）
exec > >(tee -a "$LOG") 2>&1

echo "=== publish run ${TS} (branch=${BR}) ==="

# --- 安全ゲート判定 ---
GATE="ops/PUBLISH_ENABLED"
DRAFT_FLAG="--draft"
MODE="DRAFT（下書きのみ・本番公開しない）"
if [ -f "$GATE" ]; then
  DRAFT_FLAG=""
  MODE="LIVE（本番公開）"
fi
echo "publish mode: ${MODE}  (gate: ${GATE} $( [ -f "$GATE" ] && echo present || echo absent ))"

git pull --rebase origin "$BR" || git pull origin "$BR" || true

PUB="CDO/outputs/note_publisher/publish_to_note.py"
shopt -s nullglob
published=0
failed=0
skipped=0
ok_list=""
fail_list=""
skip_list=""
thumb_fail=0

for f in drafts/queue/*.md; do
  name="$(basename "$f")"
  # --- 未来日付ガード：ファイル名の YYYY-MM-DD が今日より未来ならスキップ ---
  fdate="$(echo "$name" | grep -oE '^[0-9]{4}-[0-9]{2}-[0-9]{2}' || true)"
  if [ -n "$fdate" ] && [[ "$fdate" > "$TODAY" ]]; then
    echo "--- スキップ(未来日付 ${fdate} > ${TODAY}): ${name} ---"
    skipped=$((skipped+1)); skip_list="${skip_list} ${name}"
    continue
  fi

  echo "--- 公開試行(${MODE}): ${name} ---"
  out="$(python3 "$PUB" --article "$f" $DRAFT_FLAG 2>&1)"
  rc=$?
  echo "$out"
  # 写真サムネ未設定（=noteの既定サムネ適用）を集計。失敗ではなく情報として数える。
  if echo "$out" | grep -q "写真サムネは未設定"; then
    thumb_fail=$((thumb_fail+1))
  fi
  if [ $rc -eq 0 ]; then
    # 本番公開できたときだけ published/ へ移動する（下書き保存では queue に残す）
    if [ -z "$DRAFT_FLAG" ]; then
      mkdir -p drafts/published
      git mv "$f" "drafts/published/$name" 2>/dev/null || mv "$f" "drafts/published/$name"
    fi
    published=$((published+1)); ok_list="${ok_list} ${name}"
  else
    failed=$((failed+1)); fail_list="${fail_list} ${name}"
  fi
done

echo "=== summary: mode=${MODE} published=${published} failed=${failed} skipped(future)=${skipped} thumb_fail=${thumb_fail} ==="

# outbox に結果報告（記事名つき・code が機械的に読める）
body="[${MODE}] 公開 ${published} 件 / 失敗 ${failed} 件 / 未来日付スキップ ${skipped} 件 / 写真サムネ未設定 ${thumb_fail} 件(note既定サムネ適用)（log: ${LOG}）"
[ -n "$ok_list" ]   && body="${body} | OK:${ok_list}"
[ -n "$fail_list" ] && body="${body} | NG:${fail_list}"
[ -n "$skip_list" ] && body="${body} | SKIP:${skip_list}"
python3 ops/process_inbox.py post --from cowork --to code --type report \
  --title "auto-publish 結果 ${TS}" --body "$body" || true

git add -A
git commit -m "cowork auto: ${MODE} publish ${published}/$((published+failed)) skip=${skipped} thumb_fail=${thumb_fail} (${TS})" || true
for i in 1 2 3 4; do
  git push origin "$BR" && break || sleep $((2**i))
done
echo "done. mode=${MODE} published=${published} failed=${failed} skipped=${skipped} thumb_fail=${thumb_fail}  log=${LOG}"
