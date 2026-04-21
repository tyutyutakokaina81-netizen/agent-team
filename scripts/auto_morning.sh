#!/bin/bash
# 毎日20時に自動実行される完全非対話版のデイリールーティン
# launchd から呼ばれる。対話は一切なし。ログは ~/agent-team/logs/cron.log
# PCが20時にスリープ/シャットダウンでも、次回起動時にキャッチアップ実行される
#
# エッジケース対応：
# - 多重実行防止（PID lock）
# - 1日1回ロック（日付ベース）
# - 各ステップ独立・失敗しても続行
# - ログローテーション（7日超は削除）

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_DIR"

LOG_DIR="$REPO_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/cron.log"
DATE_LOCK="$LOG_DIR/.last_run_date"
PID_LOCK="$LOG_DIR/.auto_morning.pid"
TODAY=$(date '+%Y-%m-%d')

# 多重実行防止：PIDロック
if [[ -f "$PID_LOCK" ]]; then
    OLD_PID=$(cat "$PID_LOCK" 2>/dev/null || echo '')
    if [[ -n "$OLD_PID" ]] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "$(date): 前回実行がまだ進行中（PID:$OLD_PID）。スキップ。" >> "$LOG_FILE"
        exit 0
    fi
fi
echo $$ > "$PID_LOCK"
trap 'rm -f "$PID_LOCK"' EXIT

# 1日1回ロック：既に今日実行済みなら終了
if [[ -f "$DATE_LOCK" ]] && [[ "$(cat "$DATE_LOCK")" == "$TODAY" ]]; then
    echo "$(date): 今日はすでに実行済みです（$TODAY）" >> "$LOG_FILE"
    exit 0
fi

{
    echo ""
    echo "========================================"
    echo "🌙 自動デイリールーティン $(date '+%Y-%m-%d %H:%M')"
    echo "========================================"
    echo "（前回実行: $([[ -f "$DATE_LOCK" ]] && cat "$DATE_LOCK" || echo "初回")）"

    # 1. 最新をpull（conflictがあればスキップ）
    echo ""
    echo "📥 Git pull..."
    BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'main')
    if [[ "$BRANCH" = "HEAD" ]]; then
        echo "⚠️  detached HEAD状態。pullスキップ"
    else
        git pull origin "$BRANCH" 2>&1 || echo "⚠️  pull失敗（手動対応必要）"
    fi

    # 2. 日次レポート（エラー時も続行）
    echo ""
    python3 "$SCRIPT_DIR/daily_report.py" 2>&1 || echo "⚠️  daily_report.py 失敗"

    # 3. HTMLダッシュボード生成
    echo ""
    echo "📊 HTMLダッシュボード生成..."
    python3 "$SCRIPT_DIR/dashboard.py" 2>&1 | head -3 || echo "⚠️  dashboard.py 失敗"

    # 4. 日曜なら週次レポート
    if [[ $(date +%u) -eq 7 ]]; then
        echo ""
        echo "📅 日曜なので週次レポートも生成"
        python3 "$SCRIPT_DIR/weekly_report.py" 2>&1 || echo "⚠️  weekly_report.py 失敗"
    fi

    # 5. 月初（1日）なら月次レポート
    if [[ $(date +%d) -eq 01 ]]; then
        echo ""
        echo "📅 月初なので月次レポートも生成"
        python3 "$SCRIPT_DIR/monthly_report.py" 2>&1 || echo "⚠️  monthly_report.py 失敗"
    fi

    # 6. 自動バックアップ（安全版・許可リスト方式）
    echo ""
    "$SCRIPT_DIR/backup.sh" 2>&1 || echo "⚠️  backup失敗"

    # 7. 受注チェックリマインド
    echo ""
    echo "========================================"
    echo "📬 受注チェック リマインド"
    echo "========================================"
    echo "各プラットフォームの未読・新着を確認してください："
    echo "  クラウドワークス: https://crowdworks.jp/mypage"
    echo "  ランサーズ:       https://www.lancers.jp/mypage"
    echo "  ママワークス:     https://mamaworks.jp/member/home"
    echo ""
    echo "対話で確認する場合："
    echo "  ./scripts/deliver/check_orders.sh"
    echo ""

    echo ""
    echo "✅ 自動デイリールーティン完了 $(date '+%Y-%m-%d %H:%M')"
    echo "========================================"

    # 今日実行済みマークをつける（全ステップ完了後）
    echo "$TODAY" > "$DATE_LOCK"

    # ログローテーション（7日より古いログエントリを削除）
    if [[ $(wc -l < "$LOG_FILE" 2>/dev/null || echo 0) -gt 5000 ]]; then
        tail -1000 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
    fi
} >> "$LOG_FILE" 2>&1

# 7. ダッシュボードをブラウザで自動表示（Macのみ・エラー無視）
if command -v open >/dev/null 2>&1; then
    if [[ -f "$SCRIPT_DIR/dashboard.html" ]]; then
        open "$SCRIPT_DIR/dashboard.html" 2>/dev/null || true
    fi
fi
