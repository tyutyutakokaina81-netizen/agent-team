#!/usr/bin/env bash
# 知恵帳 SessionStart リマインダー（API費用ゼロ運用）
# 各役職フォルダ直下の 知恵帳.md を走査し、本日の日付 (### YYYY-MM-DD) が
# まだ無い役職を列挙して systemMessage でユーザー UI にのみ表示する。
# - Claude のコンテキストには注入しない（API トークン消費 = 0）
# - ユーザーが本日の追記をしたくなった時に手動で Claude に依頼する運用
# CLAUDE.md「知恵帳の運用ルール（毎日ひとつ各自）」に対応。

set -euo pipefail

today=$(date +%Y-%m-%d)
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

missing=()
for log_file in "$repo_root"/*/知恵帳.md; do
  [ -f "$log_file" ] || continue
  role=$(basename "$(dirname "$log_file")")
  if ! grep -qE "^### ${today}( |$)" "$log_file"; then
    missing+=("$role")
  fi
done

if [ ${#missing[@]} -eq 0 ]; then
  exit 0
fi

list=$(IFS=", "; echo "${missing[*]}")
jq -nc \
  --arg list "$list" \
  --arg today "$today" \
  '{
    systemMessage: ("【知恵帳リマインド】本日（" + $today + "）未追記の役職: " + $list + "。追記したい時は Claude に依頼してください。")
  }'
