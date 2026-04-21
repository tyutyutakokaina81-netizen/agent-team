#!/bin/bash
# Gitに自動バックアップ（安全版：明示的許可リスト方式）
# 機密ファイルが混入しないよう、追加するファイルパターンを明示指定
#
# エッジケース対応：
# - detached HEAD 検出
# - ネットワーク失敗時の自動リトライ
# - git lock ファイル検出
# - リポジトリ外からの実行検知
# - ステージング失敗時の自動クリーンアップ

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_DIR"

# gitリポジトリであることを検証
if [[ ! -d "$REPO_DIR/.git" ]]; then
    echo "❌ gitリポジトリではありません: $REPO_DIR"
    exit 1
fi

# git lock ファイル検出
if [[ -f "$REPO_DIR/.git/index.lock" ]]; then
    echo "❌ git lock ファイルが残っています: .git/index.lock"
    echo "   他のgit操作が実行中か、前回の操作が中断された可能性があります"
    echo "   手動で確認してください: ls -la .git/index.lock"
    exit 1
fi

# detached HEAD 検出
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
if [[ "$BRANCH" = "HEAD" ]]; then
    echo "❌ detached HEAD状態です。ブランチに戻ってください："
    echo "   git checkout claude/check-current-status-IRaNC"
    exit 1
fi

# 変更があるかチェック（ignoredを除く）
if [[ -z "$(git status --porcelain)" ]]; then
    echo "📭 変更なし。スキップします。"
    exit 0
fi

# 許可されたファイルのみを追加（許可リスト方式）
echo "📋 安全なファイルのみステージング..."

# ルートレベルのMarkdownと設定
git add -- \
    '*.md' \
    '.gitignore' \
    'company.md' \
    'CLAUDE.md' \
    'README.md' 2>/dev/null || true

# 各役職の _index.md のみ（outputs/research は .gitignore で除外済）
for ROLE in CDO CFO CMO CPO CSO; do
    [[ -f "$ROLE/_index.md" ]] && git add -- "$ROLE/_index.md"
    [[ -f "$ROLE/prompt.md" ]] && git add -- "$ROLE/prompt.md"
done

# CDO の outputs（.gitignore対象ではないので、Markdownのみ許可）
git add -- 'CDO/outputs/*.md' 2>/dev/null || true
git add -- 'CDO/research/*.md' 2>/dev/null || true

# CMO, CPO の outputs/research（Markdown のみ）
for ROLE in CMO CPO; do
    git add -- "$ROLE/outputs/*.md" 2>/dev/null || true
    git add -- "$ROLE/research/*.md" 2>/dev/null || true
done

# projects/ 配下（Markdown と Python のみ許可。JSON, PNG, 認証情報は除外）
git add -- 'projects/**/*.md' 2>/dev/null || true
git add -- 'projects/**/*.py' 2>/dev/null || true

# scripts/ 配下（実行可能ファイルとドキュメント）
git add -- 'scripts/*.py' 2>/dev/null || true
git add -- 'scripts/*.sh' 2>/dev/null || true
git add -- 'scripts/*.md' 2>/dev/null || true
git add -- 'scripts/deliver/*.py' 2>/dev/null || true
git add -- 'scripts/deliver/*.sh' 2>/dev/null || true
git add -- 'scripts/deliver/*.md' 2>/dev/null || true

# サーバーコード（ルート）
git add -- '*.mjs' '*.js' 2>/dev/null || true

# シェル関連の定義済みファイル
git add -- '*.txt' '*.sh' 2>/dev/null || true

# 設定ファイルテンプレート（plist等）
git add -- '*.plist' '*.template' 'scripts/*.plist.template' 2>/dev/null || true

# 追加されたものを確認
STAGED=$(git diff --cached --name-only | wc -l | tr -d ' ')
if [[ "$STAGED" -eq 0 ]]; then
    echo "📭 ステージング対象なし。スキップします。"
    exit 0
fi

echo "✅ $STAGED ファイルをステージング"
echo ""
echo "--- ステージング済み ---"
git diff --cached --name-only | head -10
[[ "$STAGED" -gt 10 ]] && echo "... 他 $((STAGED - 10)) ファイル"
echo ""

# 未ステージの変更があれば警告
UNSTAGED=$(git diff --name-only | wc -l | tr -d ' ')
UNTRACKED=$(git ls-files --others --exclude-standard | wc -l | tr -d ' ')
if [[ "$UNSTAGED" -gt 0 ]] || [[ "$UNTRACKED" -gt 0 ]]; then
    echo "⚠️  許可リスト外の変更を検出（バックアップ対象外）："
    git diff --name-only | head -5 | sed 's/^/    /'
    git ls-files --others --exclude-standard | head -5 | sed 's/^/    /'
    TOTAL_SKIPPED=$((UNSTAGED + UNTRACKED))
    [[ "$TOTAL_SKIPPED" -gt 5 ]] && echo "    ... 他 $((TOTAL_SKIPPED - 5)) 件"
    echo "（機密ファイルの可能性あり。手動で確認してください）"
    echo ""
fi

DATE=$(date '+%Y-%m-%d %H:%M')

# コミット（失敗時はステージングをクリア）
echo "📝 コミットします..."
if ! git commit -m "backup: 自動バックアップ $DATE"; then
    echo "⚠️  コミット失敗。ステージングを解除します。"
    git reset HEAD 2>/dev/null || true
    exit 1
fi

# プッシュ（ネットワーク失敗時のリトライ）
echo "☁️  GitHubへプッシュ中..."
PUSH_RETRY=0
MAX_RETRIES=3
while [[ $PUSH_RETRY -lt $MAX_RETRIES ]]; do
    if git push -u origin "$BRANCH" 2>&1; then
        echo "✅ バックアップ完了: $DATE"
        exit 0
    fi
    PUSH_RETRY=$((PUSH_RETRY + 1))
    if [[ $PUSH_RETRY -lt $MAX_RETRIES ]]; then
        WAIT=$((2 ** PUSH_RETRY))
        echo "⚠️  push失敗（${PUSH_RETRY}回目）。${WAIT}秒後にリトライ..."
        sleep $WAIT
    fi
done

echo "❌ push が $MAX_RETRIES 回失敗しました（ネットワーク確認必要）"
echo "   ローカルコミットは保持されています。後で手動pushしてください："
echo "   git push origin $BRANCH"
exit 2
