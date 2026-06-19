#!/bin/zsh
# daily_auto_publish.sh — launchd から毎朝呼ばれる「無人公開ジョブ」
#
# オーナー判断（2026-06-19）で無人スケジュール公開を採用。
# 6/12 の重複公開インシデントを踏まえ、以下の安全策を多重に入れている:
#   ① 対象は「当日(またはそれ以前)」のみ。未来日付は絶対に公開しない
#   ② 1日あたり最大 5 本（MAX）
#   ③ タイトル重複ガード（publish_all.sh 側 .published_titles.log）
#   ④ 二重投稿防止（publish_all.sh 側 .published.log）
#   ⑤ 実行ログを logs/ に保存
#   ⑥ 失敗時は macOS 通知でオーナーに知らせる（無人でも事故に気づける）
#
# 使い方:
#   ./daily_auto_publish.sh              # 当日分を公開
#   ./daily_auto_publish.sh 2026-06-14  # 対象日を明示（過去日のみ可）
set -u

SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR" || exit 1

LOG_DIR="${SCRIPT_DIR}/logs"
mkdir -p "$LOG_DIR"
TODAY="$(date +%F)"
LOG="${LOG_DIR}/auto_${TODAY}.log"
MAX=5
TARGET="${1:-$TODAY}"

notify() {
  command -v osascript >/dev/null 2>&1 && \
    osascript -e "display notification \"$1\" with title \"note自動公開\"" 2>/dev/null || true
}

{
  echo ""
  echo "==== $(date) daily_auto_publish 開始 (target=$TARGET, max=$MAX) ===="

  # --- 安全策①: 未来日付は公開しない（ISO日付は文字列比較で大小判定できる） ---
  if [[ "$TARGET" > "$TODAY" ]]; then
    echo "✗ 対象日($TARGET)が未来日付。安全のため中止。"
    notify "未来日付のため中止: $TARGET"
    exit 1
  fi

  # --- (0) 新規記事を台帳へ自動登録 ---
  echo "--- STEP 0 新規記事の自動登録 ---"
  python3 register_articles.py || true

  # --- (1) サムネ生成（未生成のみ。既存はスキップ） ---
  echo "--- STEP 1/3 サムネ生成 ---"
  python3 generate_thumbnails.py --filter "$TARGET" || true

  # --- (2) 公開（対象日・最大5本・重複ガードは publish_all.sh 内） ---
  echo "--- STEP 2/3 公開（最大${MAX}本） ---"
  if ./publish_all.sh --date "$TARGET" --max "$MAX"; then
    echo "✓ 公開ステップ完了"
    notify "公開完了: $TARGET（最大${MAX}本）"
  else
    echo "✗ 公開ステップで失敗あり"
    notify "公開に失敗。logs/auto_${TODAY}.log を確認してください"
  fi

  # --- (3) サムネ後追い添付 ---
  echo "--- STEP 3/3 サムネ添付 ---"
  python3 attach_thumbnails.py --filter "$TARGET" --skip-existing || true

  echo "==== $(date) daily_auto_publish 終了 ===="
} >> "$LOG" 2>&1
