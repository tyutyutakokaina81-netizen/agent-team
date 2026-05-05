#!/bin/zsh
# ai-auto API サーバー起動スクリプト
# 使い方:
#   ./run_server.sh              # 127.0.0.1:8765 で起動（mac内のみ）
#   ./run_server.sh lan          # 0.0.0.0:8765 で起動（LAN内・要 AI_AUTO_TOKEN）
#   ./run_server.sh stop         # 停止
set -e
cd "$HOME/ai-auto"

if [ -f .env ]; then
  set -a; source .env; set +a
fi

PIDFILE="$HOME/ai-auto/server.pid"
PORT="${AI_AUTO_PORT:-8765}"

case "${1:-start}" in
  stop)
    if [ -f "$PIDFILE" ]; then
      kill "$(cat "$PIDFILE")" 2>/dev/null || true
      rm -f "$PIDFILE"
      echo "stopped"
    fi
    ;;
  lan)
    [ -z "$AI_AUTO_TOKEN" ] && echo "ERROR: LANモードは AI_AUTO_TOKEN を .env に設定してください" && exit 1
    nohup python3 server.py --port "$PORT" --bind 0.0.0.0 > logs/server.log 2>&1 &
    echo $! > "$PIDFILE"
    echo "LAN started: http://$(hostname -I 2>/dev/null | awk '{print $1}' || ipconfig getifaddr en0):$PORT"
    ;;
  *)
    nohup python3 server.py --port "$PORT" --bind 127.0.0.1 > logs/server.log 2>&1 &
    echo $! > "$PIDFILE"
    echo "started: http://127.0.0.1:$PORT"
    ;;
esac
