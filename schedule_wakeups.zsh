#!/bin/zsh
# schedule_wakeups.zsh — 本日の 13:58 / 19:58 ウェイクを予約
# LaunchAgent (com.agent-team.wakeup) から毎朝 8:50 に呼ばれる

DATE=$(date +"%m/%d/%y")

sudo pmset schedule wakeorpoweron "${DATE} 13:58:00" 2>/dev/null && \
  echo "  OK: ${DATE} 13:58 ウェイク予約" || \
  echo "  NG: 13:58 予約失敗（sudoers未設定？）"

sudo pmset schedule wakeorpoweron "${DATE} 19:58:00" 2>/dev/null && \
  echo "  OK: ${DATE} 19:58 ウェイク予約" || \
  echo "  NG: 19:58 予約失敗（sudoers未設定？）"
