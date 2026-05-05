#!/bin/zsh
set -e
cd "$HOME/ai-auto"
mkdir -p logs outputs

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

STAMP="$(date '+%Y-%m-%d %H:%M')"
echo "===== RUN $STAMP =====" >> logs/run.log
python3 generate_daily_outputs.py >> logs/run.log 2>&1
python3 auto_schedule.py >> logs/run.log 2>&1

LATEST_DIR="$HOME/ai-auto/outputs"
echo ""
echo "=== 本日の生成物（最新） ==="
ls -1t "$LATEST_DIR" | head -5 | sed "s|^|  $LATEST_DIR/|"

echo ""
echo "=== 本日の自動投稿スケジュール ==="
if [ -f schedule.json ]; then
  python3 -c "import sys,json; s=json.load(sys.stdin); [print(f'  {t[\"time\"]}  {t[\"kind\"]}') for t in s['tasks']]" < schedule.json
else
  echo "  (schedule.json なし)"
fi

if command -v osascript >/dev/null 2>&1; then
  osascript -e "display notification \"生成完了。スケジュール組み済み（schedule.json）\" with title \"ai-auto\" subtitle \"$STAMP\"" 2>/dev/null || true
fi
