#!/bin/zsh
# ─────────────────────────────────────────────
# smoke_test.sh — server.mjs / pipeline_server.mjs スモークテスト
# 用途: 改修後にエンドポイントの基本動作を確認
# 使い方: ./smoke_test.sh
#         サーバーを別タブで起動済みであること
# 終了コード: 0 = 全テスト通過, 1 以上 = 失敗あり
# ─────────────────────────────────────────────
set -u

GATEWAY_PORT=${GATEWAY_PORT:-3000}
PIPELINE_PORT=${PIPELINE_PORT:-3001}
PIPELINE_TOKEN=${PIPELINE_TOKEN:-}

PASS=0
FAIL=0

ok()   { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng()   { echo "  ❌ $1"; FAIL=$((FAIL+1)); }
section() { echo; echo "── $1 ──"; }

check_status() {
  local label="$1"
  local url="$2"
  local expected="$3"
  local extra_args="${4:-}"
  local actual
  actual=$(curl -s -o /dev/null -w "%{http_code}" $extra_args "$url" 2>/dev/null)
  if [[ "$actual" == "$expected" ]]; then
    ok "$label  ($url → $actual)"
  else
    ng "$label  ($url → 期待 $expected / 実際 $actual)"
  fi
}

check_jsonkey() {
  local label="$1"
  local url="$2"
  local key="$3"
  local extra_args="${4:-}"
  if curl -s $extra_args "$url" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if '$key' in d else 1)" 2>/dev/null; then
    ok "$label  ($url に \"$key\" キーあり)"
  else
    ng "$label  ($url に \"$key\" キーなし)"
  fi
}

# ─────────────────────────────────────────────
section "agent-gateway (server.mjs:$GATEWAY_PORT)"
# ─────────────────────────────────────────────
check_status  "GET /health → 200"   "http://127.0.0.1:$GATEWAY_PORT/health"  "200"
check_jsonkey "GET /health に ok"   "http://127.0.0.1:$GATEWAY_PORT/health"  "ok"
check_status  "GET /version → 200"  "http://127.0.0.1:$GATEWAY_PORT/version" "200"
check_jsonkey "GET /version に name" "http://127.0.0.1:$GATEWAY_PORT/version" "name"
check_status  "GET /unknown → 404"  "http://127.0.0.1:$GATEWAY_PORT/unknown" "404"
check_status  "POST /echo → 200"    "http://127.0.0.1:$GATEWAY_PORT/echo"    "200" \
  "-X POST -H 'Content-Type: application/json' -d {\"hello\":\"world\"}"

# ─────────────────────────────────────────────
section "pipeline-server (pipeline_server.mjs:$PIPELINE_PORT)"
# ─────────────────────────────────────────────
check_status  "GET /health → 200"   "http://127.0.0.1:$PIPELINE_PORT/health"  "200"
check_jsonkey "GET /health に uptime_sec" "http://127.0.0.1:$PIPELINE_PORT/health" "uptime_sec"
check_status  "GET /version → 200"  "http://127.0.0.1:$PIPELINE_PORT/version" "200"
check_jsonkey "GET /version に version" "http://127.0.0.1:$PIPELINE_PORT/version" "version"
check_status  "GET /status → 200"   "http://127.0.0.1:$PIPELINE_PORT/status"  "200"
check_status  "POST /search 認証なし → 401" "http://127.0.0.1:$PIPELINE_PORT/search" "401" "-X POST"

if [[ -n "$PIPELINE_TOKEN" ]]; then
  check_status "POST /search 認証あり → 200 or 409" "http://127.0.0.1:$PIPELINE_PORT/search" "200" \
    "-X POST -H 'Authorization: Bearer $PIPELINE_TOKEN'"
fi

# ─────────────────────────────────────────────
echo
echo "================================="
echo "結果: PASS=$PASS  FAIL=$FAIL"
echo "================================="

[[ $FAIL -eq 0 ]] && exit 0 || exit 1
