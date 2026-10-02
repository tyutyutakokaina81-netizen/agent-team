#!/bin/bash
# ops/profile.sh — note / X のプロフィール文を出して、クリップボードに入れる
#   cd ~/agent-team-run && bash ops/profile.sh          note 用（既定）
#   cd ~/agent-team-run && bash ops/profile.sh --x      X 用
#   cd ~/agent-team-run && bash ops/profile.sh --short  短い版（文字数制限に入らないとき）
#
# 正本: CMO/outputs/2026-10-02_プロフィール文_note_X_フォロー導線.md
set -u
cd "$(dirname "$0")/.." 2>/dev/null || exit 1
MODE="${1:-}"
NOTE_LONG='富山県高岡市に住んでいます。名所ではなく、毎日見ているものの話を書いています。納豆を混ぜる回数、玄関で止まっている回覧板、冬に路面から出てくる水のこと。一日2本、200本を越えました。各記事の終わりに英語の要約を付けています。'
NOTE_SHORT='富山県高岡市。名所ではなく、毎日見ているものの話を一日2本書いています。200本を越えました。英語の要約つき。'
X_EN='Writing about ordinary things in Toyama, on the Japan Sea coast of Japan — how many times people stir natto, the water that comes out of the road to melt snow. Two posts a day. English summary on every one.'
case "$MODE" in
  --x)     OUT="$X_EN";      WHERE="X のプロフィール（設定 → プロフィール → 自己紹介）" ;;
  --short) OUT="$NOTE_SHORT"; WHERE="note のプロフィール（短い版）" ;;
  *)       OUT="$NOTE_LONG";  WHERE="note のプロフィール（設定 → アカウント → プロフィール）" ;;
esac
echo "=== ${WHERE} ==="
echo ""
echo "$OUT"
echo ""
echo "（${#OUT} 文字）"
if command -v pbcopy >/dev/null 2>&1; then
  printf '%s' "$OUT" | pbcopy
  echo "📋 クリップボードに入れました（貼り付け欄で ⌘V）"
fi
echo ""
echo "長さが入らないときは: bash ops/profile.sh --short"
echo "X 用を出すときは:     bash ops/profile.sh --x"
