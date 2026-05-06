#!/usr/bin/env bash
# note_show.sh — Vol N のタイトル/本文/タグをターミナルに表示
# (pbcopy は使わない。画面を見て自分で選択コピーする版)
#
# 使い方：
#   bash note_show* 7 title
#   bash note_show* 7 body
#   bash note_show* 7 tags
set -e
cd "$(dirname "$0")"

VOL="${1:-7}"
KIND="${2:-body}"

python3 - "$VOL" "$KIND" <<'PYEOF'
import re, sys
vol = sys.argv[1]
kind = sys.argv[2]
path = 'projects/2026-04-08_月30万自動化/今すぐ収益化/note_paste.md'
t = open(path, encoding='utf-8').read()

sec_pat = rf'## Vol\.{vol}\b.*?(?=^## Vol\.|^---\s*$|\Z)'
sec = re.search(sec_pat, t, re.M | re.S)
if not sec:
    print(f'Vol.{vol} not found', file=sys.stderr); sys.exit(1)
body = sec.group(0)

if kind == 'title':
    m = re.search(r'### タイトル\n```\n(.+?)\n```', body, re.S)
elif kind == 'body':
    m = re.search(r'### 本文\n```\n(.+?)\n```', body, re.S)
elif kind == 'tags':
    m = re.search(r'🏷 タグ\*\*：(.+)', body)

if not m:
    print(f'{kind} not found', file=sys.stderr); sys.exit(1)

print()
print("===== ↓ 選択コピーしてください ↓ =====")
print()
print(m.group(1).strip())
print()
print("===== ↑ ここまで ↑ =====")
PYEOF
