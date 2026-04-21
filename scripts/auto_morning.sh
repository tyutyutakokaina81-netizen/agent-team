#!/bin/bash
# 毎日20時に自動実行される完全非対話版のデイリールーティン
# launchd から呼ばれる。対話は一切なし。ログは ~/agent-team/logs/cron.log
# PCが20時にスリープ/シャットダウンでも、次回起動時にキャッチアップ実行される

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_DIR"

LOG_DIR="$REPO_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/cron.log"
LOCK_FILE="$LOG_DIR/.last_run_date"
TODAY=$(date '+%Y-%m-%d')

# 1日1回ロック：既に今日実行済みなら終了
if [[ -f "$LOCK_FILE" ]] && [[ "$(cat "$LOCK_FILE")" == "$TODAY" ]]; then
    echo "今日はすでに実行済みです（$TODAY）" >> "$LOG_FILE"
    exit 0
fi

{
    echo ""
    echo "========================================"
    echo "🌙 自動デイリールーティン $(date '+%Y-%m-%d %H:%M')"
    echo "========================================"
    echo "（前回実行: $([[ -f "$LOCK_FILE" ]] && cat "$LOCK_FILE" || echo "初回")）"

    # 1. 最新をpull（conflictがあればスキップ）
    echo "📥 Git pull..."
    BRANCH=$(git rev-parse --abbrev-ref HEAD)
    git pull origin "$BRANCH" 2>&1 || echo "⚠️  pull失敗（手動対応必要）"

    # 2. 日次レポート
    echo ""
    python3 "$SCRIPT_DIR/daily_report.py"

    # 3. HTMLダッシュボード生成
    echo ""
    echo "📊 HTMLダッシュボード生成..."
    python3 "$SCRIPT_DIR/dashboard.py" 2>&1 | head -3

    # 4. 日曜なら週次レポート
    if [[ $(date +%u) -eq 7 ]]; then
        echo ""
        echo "📅 日曜なので週次レポートも生成"
        python3 "$SCRIPT_DIR/weekly_report.py"
    fi

    # 5. 月初（1日）なら月次レポート
    if [[ $(date +%d) -eq 01 ]]; then
        echo ""
        echo "📅 月初なので月次レポートも生成"
        python3 "$SCRIPT_DIR/monthly_report.py"
    fi

    # 6. 自動バックアップ（安全版・許可リスト方式）
    echo ""
    "$SCRIPT_DIR/backup.sh" 2>&1 || echo "⚠️  backup失敗"

    echo ""
    echo "✅ 自動デイリールーティン完了 $(date '+%Y-%m-%d %H:%M')"
    echo "========================================"

    # 今日実行済みマークをつける
    echo "$TODAY" > "$LOCK_FILE"
} >> "$LOG_FILE" 2>&1

# 最後の行をstdoutに出す（ログを見やすく）
tail -5 "$LOG_FILE"
