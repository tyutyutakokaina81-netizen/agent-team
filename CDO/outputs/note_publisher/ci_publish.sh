#!/usr/bin/env bash
# ci_publish.sh — GitHub Actions（クラウド無人）用の公開ループ。
#
# Mac版 publish_all.sh とは別物（git pull / launchctl を持たず、CIで完結する）。
# 公開状態は git 追跡される manifest に記録するので、Action 実行をまたいで重複公開しない。
#
# 安全策:
#   ① 対象は当日(またはそれ以前)のみ。未来日付は公開しない
#   ② 1日あたり最大 MAX 本（既定5）
#   ③ ファイル名 manifest で二重投稿防止
#   ④ タイトル manifest で同題重複を防止（6/12インシデント対策）
#
# 使い方（CIから）: bash ci_publish.sh "$TARGET_DATE" [MAX]
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
REPO="$(cd ../../.. && pwd)"
ARTICLES="$REPO/CMO/outputs"

# git 追跡される公開状態（.published.log は gitignore のため CI 用に別ファイル）
MANIFEST="$SCRIPT_DIR/published_manifest.txt"
TITLES="$SCRIPT_DIR/published_titles_manifest.txt"
touch "$MANIFEST" "$TITLES"

TODAY="$(date +%F)"
TARGET="${1:-$TODAY}"
[ -z "$TARGET" ] && TARGET="$TODAY"
MAX="${2:-5}"

echo "==== ci_publish target=$TARGET max=$MAX ===="

# 安全策①: 未来日付は公開しない
if [[ "$TARGET" > "$TODAY" ]]; then
  echo "✗ 対象日($TARGET)が未来日付。中止。"
  exit 1
fi

article_title() {
  python3 - "$1" <<'PY'
import re, sys
t = open(sys.argv[1], encoding="utf-8").read()
m = re.search(r"メイン.*?\n```\n(.+?)\n```", t, re.S) or re.search(r"##\s*タイトル.*?\n```\n(.+?)\n```", t, re.S)
print(m.group(1).strip().splitlines()[0].strip() if m else "")
PY
}

count=0
shopt -s nullglob
for f in "$ARTICLES/${TARGET}_note記事_"*.md; do
  base="$(basename "$f")"
  if grep -qxF "$base" "$MANIFEST"; then
    echo "skip(既公開): $base"; continue
  fi
  title="$(article_title "$f")"
  if [ -n "$title" ] && grep -qxF "$title" "$TITLES"; then
    echo "skip(重複タイトル): $base（$title）"; continue
  fi

  echo "--- 公開: $base ---"
  if python3 publish_to_note.py --article "$f" --text-only; then
    echo "$base" >> "$MANIFEST"
    [ -n "$title" ] && echo "$title" >> "$TITLES"
    count=$((count + 1))
    echo "✓ 完了: $base （累計 $count）"
  else
    echo "✗ 失敗: $base"
  fi

  if [ "$count" -ge "$MAX" ]; then
    echo "上限 $MAX 本に達したので終了"; break
  fi
  sleep 5
done

echo "==== 公開 $count 本 ===="
