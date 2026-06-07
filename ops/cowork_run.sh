#!/bin/bash
# cowork 配信デーモン — オーナーのMacで cron/launchd 実行し、code が物理的にできない
# 「note公開」を自動化する。canonical(main)を pull → 公開キュー処理 → 報告 → push。
set -euo pipefail
cd "$(dirname "$0")/.."
git pull --rebase origin main || git pull origin main
PUB="CDO/outputs/note_publisher/publish_to_note.py"
shopt -s nullglob
published=0
for f in drafts/queue/*.md; do
  if python3 "$PUB" --article "$f"; then
    mkdir -p drafts/published
    git mv "$f" "drafts/published/$(basename "$f")"
    published=$((published+1))
  fi
done
# outbox に結果報告
ts=$(date +%Y-%m-%d)
python3 ops/process_inbox.py post --from cowork --to code --type report \
  --title "auto-publish 結果 ${ts}" --body "公開 ${published} 件（drafts/queue→published）。" || true
git add -A
git commit -m "cowork auto: publish ${published} from queue (${ts})" || true
git push origin main || true
echo "done. published=${published}"
