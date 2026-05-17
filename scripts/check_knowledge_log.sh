#!/usr/bin/env bash
# SessionStart リマインダー（API費用ゼロ運用）
# 2つの確認を行い、必要があれば systemMessage でユーザー UI にのみ表示する。
# - Claude のコンテキストには注入しない（API トークン消費 = 0）
# - リマインドはユーザー画面表示のみ。手動対応する運用。
# 対応ルール：
#   1. 各役職フォルダ直下の 知恵帳.md に本日の日付 (### YYYY-MM-DD) があるか
#   2. context/diary/ と context/ideas/ にファイルが1つでもあるか（.gitkeep 除く）

set -euo pipefail

today=$(date +%Y-%m-%d)
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# --- 1. 知恵帳の本日エントリ確認 ---
missing_wisdom=()
for log_file in "$repo_root"/*/知恵帳.md; do
  [ -f "$log_file" ] || continue
  role=$(basename "$(dirname "$log_file")")
  if ! grep -qE "^### ${today}( |$)" "$log_file"; then
    missing_wisdom+=("$role")
  fi
done

# --- 2. context/ の空状態確認 ---
empty_context=()
for sub in diary ideas; do
  dir="$repo_root/context/$sub"
  [ -d "$dir" ] || continue
  # .gitkeep 以外のファイルがあるか
  count=$(find "$dir" -maxdepth 1 -type f ! -name '.gitkeep' | wc -l)
  if [ "$count" -eq 0 ]; then
    empty_context+=("$sub")
  fi
done

# --- 出力 ---
msg=""
if [ ${#missing_wisdom[@]} -gt 0 ]; then
  list=$(IFS=", "; echo "${missing_wisdom[*]}")
  msg="【知恵帳】本日（${today}）未追記: ${list}"
fi
if [ ${#empty_context[@]} -gt 0 ]; then
  ctx=$(IFS=", "; echo "${empty_context[*]}")
  ctx_msg="【context】未整備フォルダ: ${ctx}（オーナーが日記・アイデアを書き溜めると次セッションの質が上がります）"
  if [ -n "$msg" ]; then
    msg="${msg} ／ ${ctx_msg}"
  else
    msg="${ctx_msg}"
  fi
fi

if [ -z "$msg" ]; then
  exit 0
fi

jq -nc --arg msg "$msg" '{ systemMessage: $msg }'
