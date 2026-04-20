#!/bin/bash
# Gitに自動バックアップ
# 使い方: ./scripts/backup.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_DIR"

# 変更があるかチェック
if [[ -z "$(git status --porcelain)" ]]; then
    echo "📭 変更なし。スキップします。"
    exit 0
fi

# 現在のブランチ名を取得
BRANCH=$(git rev-parse --abbrev-ref HEAD)
DATE=$(date '+%Y-%m-%d %H:%M')

# コミット＆push
echo "📝 変更を検出。コミットします..."
git add .
git commit -m "backup: 自動バックアップ $DATE"

echo "☁️  GitHubへプッシュ中..."
git push -u origin "$BRANCH"

echo "✅ バックアップ完了: $DATE"
