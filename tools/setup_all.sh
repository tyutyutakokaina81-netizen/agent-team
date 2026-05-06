#!/bin/zsh
# 全自動化セットアップ（mac で1コマンド）。
#
# 順番に実行:
#   1. Reddit 自動公開（API・規約OK・認証情報を対話入力）
#   2. note 自動公開（Playwright・規約グレー・手動ログイン1回）
#   3. Discord 通知（任意・Webhook URL を貼るだけ）
#
# 前提: gh CLI 認証済み・python3 + playwright インストール済み

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "============================================"
echo "  AI 自動収益化システム 全自動セットアップ"
echo "============================================"
echo ""
echo "やること:"
echo "  ① Reddit 自動公開（5分・iPhone でアプリ作成必要）"
echo "  ② note 自動公開（5分・規約グレー・BANリスク承知）"
echo "  ③ Discord 通知（1分・任意）"
echo ""
read -p "進める？ [Y/n]: " GO
[ "$GO" = "n" ] && exit 0

# ① Reddit
echo ""
echo "============================================"
echo "  ① Reddit 自動公開"
echo "============================================"
read -p "セットアップする？ [Y/n]: " R_YES
if [ "$R_YES" != "n" ]; then
  bash tools/setup_reddit_auto.sh
fi

# ② note
echo ""
echo "============================================"
echo "  ② note 自動公開（規約グレー）"
echo "============================================"
echo "警告: note 規約上ボット投稿は禁止。BAN リスクあり。"
read -p "それでもセットアップする？ [y/N]: " N_YES
if [ "$N_YES" = "y" ]; then
  bash tools/setup_note_auto.sh
fi

# ③ Discord
echo ""
echo "============================================"
echo "  ③ Discord 通知（任意）"
echo "============================================"
echo "Discord アプリで Webhook URL を作成しておいてください。"
read -p "Discord Webhook URL（ENTERでスキップ）: " D_URL
if [ -n "$D_URL" ]; then
  REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
  printf '%s' "$D_URL" | gh secret set DISCORD_WEBHOOK_URL --repo "$REPO"
  echo "✓ Discord 通知有効化"
fi

# 完了
echo ""
echo "============================================"
echo "  ✓ 全自動セットアップ完了"
echo "============================================"
echo ""
REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
echo "翌朝07:00から自動運用が始まります。"
echo ""
echo "今すぐテスト実行:"
echo "  gh workflow run 'Daily Drafts & Auto-Publish' \\"
echo "    --repo '$REPO' \\"
echo "    --ref claude/ai-monetization-handover-epkiB"
echo ""
echo "実行履歴:"
echo "  https://github.com/$REPO/actions"
echo ""
echo "緊急停止:"
echo "  gh variable set ENABLE_REDDIT_AUTO_PUBLISH --repo '$REPO' --body 'false'"
echo "  gh variable set ENABLE_NOTE_AUTO_PUBLISH   --repo '$REPO' --body 'false'"
