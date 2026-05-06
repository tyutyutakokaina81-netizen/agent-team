#!/usr/bin/env bash
# note_copy.sh — 指定 Vol のタイトル / 本文をクリップボードへコピー
#
# 使い方:
#   bash note_copy* 7 title    # Vol.7 のタイトルをコピー → ⌘+V で note のタイトル欄に貼付
#   bash note_copy* 7 body     # Vol.7 の本文をコピー   → ⌘+V で note の本文欄に貼付
#   bash note_copy* 7 tags     # Vol.7 のタグをコピー
#
# 対応 Vol：2, 3, 5, 6, 7, 8, 9, 10, 11
set -e
cd "$(dirname "$0")"

VOL="${1:-7}"
KIND="${2:-body}"

python3 - "$VOL" "$KIND" <<'PYEOF' | pbcopy
import re, sys
vol = sys.argv[1]
kind = sys.argv[2]
path = 'projects/2026-04-08_月30万自動化/今すぐ収益化/note_paste.md'
t = open(path, encoding='utf-8').read()

sec_pat = rf'## Vol\.{vol}\b.*?(?=^## Vol\.|^---\s*$|\Z)'
sec = re.search(sec_pat, t, re.M | re.S)
if not sec:
    print(f'Vol.{vol} not found in {path}', file=sys.stderr)
    sys.exit(1)
body = sec.group(0)

if kind == 'title':
    m = re.search(r'### タイトル\n```\n(.+?)\n```', body, re.S)
elif kind == 'body':
    m = re.search(r'### 本文\n```\n(.+?)\n```', body, re.S)
elif kind == 'tags':
    m = re.search(r'🏷 タグ\*\*：(.+)', body)
else:
    print(f'unknown kind: {kind} (use: title / body / tags)', file=sys.stderr)
    sys.exit(1)

if not m:
    print(f'{kind} section not found for Vol.{vol}', file=sys.stderr)
    sys.exit(1)

print(m.group(1).strip(), end='')
PYEOF

echo "✅ Vol.${VOL} の ${KIND} をクリップボードにコピーしました。" >&2
echo "   → note のブラウザに切り替えて ⌘+V で貼付してください。" >&2
