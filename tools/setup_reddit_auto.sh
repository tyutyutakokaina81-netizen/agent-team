#!/bin/zsh
# Reddit 自動公開を1コマンドでセットアップする mac/Linux 用スクリプト。
#
# 事前準備（人間がブラウザで1回だけ）:
#   1. https://www.reddit.com/prefs/apps を開く
#   2. 「create another app...」→ 種類: script
#      name: ai-auto / redirect uri: http://localhost:8080
#   3. 表示された client_id（14文字）と secret を控える
#
# このスクリプトを実行すると:
#   - 認証情報を対話入力（パスワードは表示されない）
#   - gh CLI 経由で全 Secret/Variable を登録
#   - ENABLE_REDDIT_AUTO_PUBLISH=true を設定
#
# 前提:
#   - gh CLI と gh auth login 済み

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "=========================================="
echo "  Reddit 自動公開 セットアップ"
echo "=========================================="

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: gh CLI が必要です: brew install gh && gh auth login"
  exit 1
fi
if ! gh auth status >/dev/null 2>&1; then
  echo "ERROR: gh auth login が必要です"
  exit 1
fi

REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || true)"
if [ -z "$REPO" ]; then
  echo "ERROR: agent-team ディレクトリで実行してください"
  exit 1
fi

echo "対象リポジトリ: $REPO"
echo ""
echo "事前にやっておくこと:"
echo "  1. https://www.reddit.com/prefs/apps で script アプリを作成"
echo "  2. client_id（14文字）と secret を控える"
echo ""
read -p "準備できたら Enter: "

read -p "Reddit ユーザー名: " R_USER
read -s -p "Reddit パスワード（表示されません）: " R_PASS
echo
read -p "Client ID（14文字）: " R_CID
read -s -p "Client Secret（表示されません）: " R_SEC
echo
read -p "投稿先 Subreddit（既定 SlowLiving）: " R_SUB
R_SUB="${R_SUB:-SlowLiving}"

R_UA="ai-auto:v1.0 by /u/${R_USER}"

echo ""
echo "→ GitHub Secret 登録..."
printf '%s' "$R_CID"  | gh secret set REDDIT_CLIENT_ID     --repo "$REPO"
printf '%s' "$R_SEC"  | gh secret set REDDIT_CLIENT_SECRET --repo "$REPO"
printf '%s' "$R_UA"   | gh secret set REDDIT_USER_AGENT    --repo "$REPO"
printf '%s' "$R_USER" | gh secret set REDDIT_USERNAME      --repo "$REPO"
printf '%s' "$R_PASS" | gh secret set REDDIT_PASSWORD      --repo "$REPO"

echo "→ Variable 設定..."
gh variable set ENABLE_REDDIT_AUTO_PUBLISH --repo "$REPO" --body "true"
gh variable set REDDIT_SUBREDDIT --repo "$REPO" --body "$R_SUB"

echo ""
echo "✓ Reddit 自動公開セットアップ完了"
echo "  翌朝07:00から自動投稿。緊急停止は ENABLE_REDDIT_AUTO_PUBLISH=false"
echo "  今すぐテスト: gh workflow run 'Daily Drafts & Auto-Publish' --repo '$REPO' \\"
echo "    --ref claude/ai-monetization-handover-epkiB -f enable_reddit=true"
