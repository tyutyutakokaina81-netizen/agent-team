#!/bin/zsh
# note 自動公開を1コマンドでセットアップする mac 専用スクリプト。
#
# やること:
#   1. Playwright Chromium で手動ログイン → storageState を取得
#   2. base64 化
#   3. gh CLI で NOTE_STORAGE_STATE Secret を登録
#   4. gh CLI で ENABLE_NOTE_AUTO_PUBLISH=true Variable を設定
#   5. workflow を即実行（DRY_RUN で動作確認）
#   6. state ファイルを削除（ローカルに残さない）
#
# 前提:
#   - mac で実行
#   - gh CLI インストール済み（無ければ brew install gh）
#   - gh auth login 済み
#   - python3 と playwright インストール済み
#
# 使い方:
#   cd ~/agent-team
#   bash tools/setup_note_auto.sh

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "=========================================="
echo "  note 自動公開 セットアップ"
echo "  作業ディレクトリ: $REPO_ROOT"
echo "=========================================="
echo ""

# 0. 前提チェック
if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: gh CLI が必要です。"
  echo "  brew install gh"
  echo "  gh auth login"
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "ERROR: gh auth login が必要です。"
  echo "  gh auth login"
  exit 1
fi

REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || true)"
if [ -z "$REPO" ]; then
  echo "ERROR: GitHub リポジトリの情報を取得できません。"
  echo "  agent-team のディレクトリで実行してください。"
  exit 1
fi
echo "→ 対象リポジトリ: $REPO"
echo ""

if ! python3 -c "import playwright" 2>/dev/null; then
  echo "→ playwright をインストール..."
  pip install --user playwright
  python3 -m playwright install chromium
fi

# 1. storageState の取得
echo ""
echo "==========================================="
echo "  Step 1/5: note にログインして state 取得"
echo "==========================================="
echo "ブラウザが開きます。note にログインしてからターミナルで Enter キーを押してください。"
echo ""
python3 tools/extract_note_state.py

if [ ! -f "note_state.b64" ]; then
  echo "ERROR: note_state.b64 が生成されませんでした"
  exit 1
fi

# 2. Secret 登録
echo ""
echo "==========================================="
echo "  Step 2/5: GitHub Secret に登録"
echo "==========================================="
gh secret set NOTE_STORAGE_STATE --repo "$REPO" < note_state.b64
echo "✓ NOTE_STORAGE_STATE 登録完了"

# 3. Variable 設定
echo ""
echo "==========================================="
echo "  Step 3/5: Variable で常時自動公開を有効化"
echo "==========================================="
gh variable set ENABLE_NOTE_AUTO_PUBLISH --repo "$REPO" --body "true"
echo "✓ ENABLE_NOTE_AUTO_PUBLISH=true 設定完了"

# 4. ワークフロー初回トリガー（DRY_RUN）
echo ""
echo "==========================================="
echo "  Step 4/5: ワークフロー DRY_RUN で動作確認"
echo "==========================================="
gh workflow run "Daily Drafts & Auto-Publish" \
  --repo "$REPO" \
  --ref claude/ai-monetization-handover-epkiB \
  -f enable_note=false \
  -f enable_reddit=false
echo "✓ DRY_RUN 実行をトリガーしました"
echo "  確認: gh run list --workflow=daily-drafts.yml"

# 5. ローカル state ファイルを削除（セキュリティ）
echo ""
echo "==========================================="
echo "  Step 5/5: ローカル state ファイルを削除"
echo "==========================================="
rm -f note_state.json note_state.b64
echo "✓ note_state.json / note_state.b64 を削除"

echo ""
echo "=========================================="
echo "  ✓ セットアップ完了"
echo "=========================================="
echo ""
echo "翌朝 07:00 (JST) から note 自動公開が動きます。"
echo ""
echo "今すぐ本番投稿でテストしたい場合:"
echo "  gh workflow run \"Daily Drafts & Auto-Publish\" \\"
echo "    --repo \"$REPO\" \\"
echo "    --ref claude/ai-monetization-handover-epkiB \\"
echo "    -f enable_note=true"
echo ""
echo "実行状況:"
echo "  https://github.com/$REPO/actions"
echo ""
echo "緊急停止:"
echo "  gh variable set ENABLE_NOTE_AUTO_PUBLISH --repo \"$REPO\" --body \"false\""
echo ""
echo "state 失効時（Discord 通知が来たら）:"
echo "  bash tools/setup_note_auto.sh   # このコマンド再実行で state 更新"
echo ""
