#!/bin/bash
# 朝の公開ワンボタン（オーナーのMacで実行）。
#   git lock掃除 → main同期 → drafts/queue の本日記事を順に公開。
# 使い方:
#   bash ops/publish_today.sh            # 本日分を公開（ログイン済み前提）
#   bash ops/publish_today.sh --login    # 先にnoteログインしてから公開
#   bash ops/publish_today.sh --all      # 本日分に限らずキュー全部
#
# 2026-06-23 作成。今朝の不具合（zshグロブでlock消えない／未来日付誤選択／
# タイトル欄タイムアウトでクラッシュ）をまとめて回避するための定型スクリプト。
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

LOGIN=0
ALL=0
for a in "$@"; do
  case "$a" in
    --login) LOGIN=1 ;;
    --all)   ALL=1 ;;
  esac
done

echo "== ① git lock 掃除（場所を問わず再帰削除・zsh安全）=="
find .git -name '*.lock' -print -delete 2>/dev/null || true

echo "== ② main 同期 =="
git fetch origin main && git checkout -B main origin/main || { echo "✗ git同期失敗。lockが残っていないか確認。"; exit 1; }

PUB="CDO/outputs/note_publisher/publish_to_note.py"

if [ $LOGIN -eq 1 ] || [ ! -d "$HOME/.note_publisher_profile" ]; then
  echo "== ③ noteログイン（ブラウザが開きます。ログイン済みなら Enter）=="
  python3 "$PUB" --login || { echo "✗ ログイン中断"; exit 1; }
fi

shopt -s nullglob
today="$(date +%Y-%m-%d)"
if [ $ALL -eq 1 ]; then
  files=(drafts/queue/*.md)
else
  files=(drafts/queue/${today}_*.md)
  if [ ${#files[@]} -eq 0 ]; then
    echo "本日(${today})のキュー記事なし → キュー全体を対象にします。"
    files=(drafts/queue/*.md)
  fi
fi

if [ ${#files[@]} -eq 0 ]; then
  echo "公開対象がありません（drafts/queue 空）。"; exit 0
fi

ok=0; ng=0
for f in "${files[@]}"; do
  echo ""; echo "========== 公開: $(basename "$f") =========="
  if python3 "$PUB" --text-only --article "$f"; then
    ok=$((ok+1))
    mkdir -p drafts/published
    git mv "$f" "drafts/published/$(basename "$f")" 2>/dev/null || mv "$f" "drafts/published/$(basename "$f")"
  else
    ng=$((ng+1))
    echo "  ⚠️  この記事は公開できませんでした（キューに残します）。"
  fi
  sleep 4
done

echo ""; echo "=== 結果: 公開 ${ok} 件 / 失敗 ${ng} 件 ==="
if [ $ok -gt 0 ]; then
  git add -A
  git -c user.email=noreply@anthropic.com -c user.name=Claude commit -q -m "publish: 本日分 ${ok}件をqueue→publishedへ移動 (${today})" || true
  for i in 1 2 3 4; do git push origin main && break || sleep $((2**i)); done
fi
echo "=== 完了 ==="
