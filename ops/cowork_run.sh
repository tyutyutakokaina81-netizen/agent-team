#!/bin/bash
# cowork 配信デーモン — オーナーのMacで実行（手動 or launchd/cron）。
# code が物理的にできない「note公開」を自動化し、★確認作業も自動化★する：
#   現ブランチを pull → キュー公開 → 全出力をログ保存 → 結果を outbox 報告 → commit & push。
# これにより、オーナーがコンソールを目視して貼り付けなくても、
# code が repo の ops/logs/ と ops/outbox/ を読んで結果を確認できる。
set -uo pipefail
cd "$(dirname "$0")/.."

BR="$(git rev-parse --abbrev-ref HEAD)"
mkdir -p ops/logs
TS="$(date +%Y-%m-%d_%H%M%S)"
LOG="ops/logs/publish_${TS}.log"

# 全標準出力/エラーをログにも複製（確認作業の自動化の中核）
exec > >(tee -a "$LOG") 2>&1

echo "=== publish run ${TS} (branch=${BR}) ==="
# 自己修復: 前回の未完マージ/リベースや残骸ロックがあると git 同期が全部詰まるので先に解消
find .git -name '*.lock' -delete 2>/dev/null || true
git merge --abort  2>/dev/null || true
git rebase --abort 2>/dev/null || true
git pull --rebase origin "$BR" || git pull origin "$BR" || { echo "⚠️ pull失敗→origin/${BR}へ強制同期(Macはミラー)"; git fetch origin "$BR" && git reset --hard "origin/${BR}"; }

PUB="CDO/outputs/note_publisher/publish_to_note.py"
shopt -s nullglob
published=0
failed=0
ok_list=""
fail_list=""
thumb_fail=0
login_fail=0

for f in drafts/queue/*.md; do
  name="$(basename "$f")"
  echo "--- 公開試行: ${name} ---"
  out="$(python3 "$PUB" --text-only --article "$f" 2>&1)"
  rc=$?
  echo "$out"
  # 写真サムネ未設定（=noteの既定サムネ適用）を集計。失敗ではなく情報として数える。
  if echo "$out" | grep -q "写真サムネは未設定"; then
    thumb_fail=$((thumb_fail+1))
  fi
  # ★ログイン切れ/未ログインを検知（publisherが未ログイン時に出す定型文）。無人では自動ログインできないため
  #   outboxに「要ログイン」をはっきり残し、owner が --login すべきと分かるようにする（0/N全滅の原因特定用）。
  if echo "$out" | grep -qE "ログインしていない|初回ログインがまだ"; then
    login_fail=1
  fi
  if [ $rc -eq 0 ]; then
    mkdir -p drafts/published
    git mv "$f" "drafts/published/$name" 2>/dev/null || mv "$f" "drafts/published/$name"
    published=$((published+1)); ok_list="${ok_list} ${name}"
  else
    failed=$((failed+1)); fail_list="${fail_list} ${name}"
  fi
done

echo "=== summary: published=${published} failed=${failed} thumb_fail=${thumb_fail} ==="

# outbox に結果報告（記事名つき・code が機械的に読める）
body="公開 ${published} 件 / 失敗 ${failed} 件 / 写真サムネ未設定 ${thumb_fail} 件(note既定サムネ適用)（log: ${LOG}）"
# ★ログイン切れ検知時は先頭に大きく警告（無人では復旧不可＝owner対応が必要）
if [ $login_fail -eq 1 ]; then
  body="⚠️【要対応】noteログイン切れ/未ログインで公開できません。owner は Mac で \`python3 CDO/outputs/note_publisher/publish_to_note.py --login\` を実行しnoteにログイン→再度公開してください。 || ${body}"
fi
[ -n "$ok_list" ]   && body="${body} | OK:${ok_list}"
[ -n "$fail_list" ] && body="${body} | NG:${fail_list}"
python3 ops/process_inbox.py post --from cowork --to code --type report \
  --title "auto-publish 結果 ${TS}" --body "$body" || true

git add -A
git commit -m "cowork auto: publish ${published}/$((published+failed)) thumb_fail=${thumb_fail} (${TS})" || true
for i in 1 2 3 4; do
  git push origin "$BR" && break || sleep $((2**i))
done
echo "done. published=${published} failed=${failed} thumb_fail=${thumb_fail}  log=${LOG}"
