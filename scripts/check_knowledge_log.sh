#!/usr/bin/env bash
# 知恵帳 SessionStart リマインダー
# 各役職フォルダ直下の 知恵帳.md を走査し、本日の日付 (### YYYY-MM-DD) が
# まだ無い役職を列挙して Claude に additionalContext として渡す。
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
    hookSpecificOutput: {
      hookEventName: "SessionStart",
      additionalContext: ("【知恵帳リマインド】本日（" + $today + "）まだ追記がない役職: " + $list + "。今日の会話の中で適切なタイミングで、CLAUDE.md「知恵帳の運用ルール」に従い、各役職フォルダ直下の 知恵帳.md に『学び/背景/示唆』を1件ずつ追記すること。書けない役職は無理に書かない。")
    }
  }'
