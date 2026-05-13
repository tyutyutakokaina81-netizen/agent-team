#!/usr/bin/env bash
# autonomous/deploy_live.sh
# One-shot deployment of jp-subsidy-mcp + toyama-local-mcp to Cloudflare Workers.
#
# Required env: CLOUDFLARE_API_TOKEN
# Optional env: SERVER_ADDRESS (defaults to burn address if not set)
#
# Usage:
#   CLOUDFLARE_API_TOKEN='cfut_xxx' bash autonomous/deploy_live.sh
#   CLOUDFLARE_API_TOKEN='cfut_xxx' SERVER_ADDRESS='0x...' bash autonomous/deploy_live.sh

set -e
set -o pipefail

# ── log helpers ────────────────────────────────
if [ -t 1 ]; then
  G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; B='\033[0;34m'; BD='\033[1m'; N='\033[0m'
else
  G=''; Y=''; R=''; B=''; BD=''; N=''
fi
log()  { printf "${G}[deploy]${N} %s\n" "$*"; }
warn() { printf "${Y}[warn]${N}  %s\n" "$*"; }
err()  { printf "${R}[error]${N} %s\n" "$*"; }
hdr()  { printf "\n${BD}${B}━━━ %s ━━━${N}\n" "$*"; }

# ── env check ──────────────────────────────────
hdr "Environment Check"

if [ -z "${CLOUDFLARE_API_TOKEN:-}" ]; then
  err "CLOUDFLARE_API_TOKEN is not set."
  echo "Usage: CLOUDFLARE_API_TOKEN='cfut_xxx' bash $0"
  exit 1
fi
log "CLOUDFLARE_API_TOKEN: set (len=${#CLOUDFLARE_API_TOKEN})"

DEAD="0x000000000000000000000000000000000000dEaD"
USING_BURN="no"
if [ -z "${SERVER_ADDRESS:-}" ]; then
  SERVER_ADDRESS="$DEAD"
  USING_BURN="yes"
  warn "SERVER_ADDRESS not set -> using burn address (temporary)"
  warn "Real USDC sent to burn address is LOST. Update later."
else
  log "SERVER_ADDRESS: $SERVER_ADDRESS"
fi

command -v node >/dev/null || { err "node not installed (brew install node)"; exit 1; }
command -v npm  >/dev/null || { err "npm not installed";  exit 1; }
log "node: $(node --version)"
log "npm:  $(npm --version)"

export CI=true
export WRANGLER_SEND_METRICS=false

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PRODUCTS_DIR="$REPO_ROOT/autonomous/products"
log "repo root: $REPO_ROOT"

if [ ! -d "$PRODUCTS_DIR" ]; then
  err "products dir not found: $PRODUCTS_DIR"
  err "Are you on branch claude/progress-check-V3yFe?"
  exit 1
fi

# ── Cloudflare workers.dev subdomain 自動登録 ─
# 初回 deploy 前に一度だけ必要。ブラウザ不要。
# bash の pipefail を避けるため、JSON 処理は Node.js ヘルパーに委譲。

hdr "Cloudflare Subdomain Setup"

SETUP_OUT=$(node "$REPO_ROOT/autonomous/cf_subdomain_setup.mjs") || {
  err "cf_subdomain_setup.mjs failed"
  exit 1
}

ACCOUNT_ID=$(printf "%s" "$SETUP_OUT" | cut -f1)
CF_SUBDOMAIN=$(printf "%s" "$SETUP_OUT" | cut -f2)

if [ -z "$ACCOUNT_ID" ] || [ -z "$CF_SUBDOMAIN" ]; then
  err "failed to obtain account ID or subdomain"
  err "setup output: $SETUP_OUT"
  exit 1
fi

log "account ID:     $ACCOUNT_ID"
log "workers.dev:    $CF_SUBDOMAIN.workers.dev"

export CLOUDFLARE_ACCOUNT_ID="$ACCOUNT_ID"

# ── deploy function ────────────────────────────
deploy_one() {
  local name="$1"
  local dir="$PRODUCTS_DIR/$name"
  hdr "Deploying: $name"

  if [ ! -d "$dir" ]; then
    err "$name: directory not found"
    return 1
  fi

  cd "$dir"

  log "[1/4] npm install..."
  npm install --silent --no-progress --no-audit --no-fund 2>&1 | tail -10 || {
    err "$name: npm install failed"; return 1;
  }
  log "[1/4] npm install OK"

  log "[2/4] wrangler deploy..."
  local out
  out=$(npx --yes wrangler deploy 2>&1) || {
    err "$name: wrangler deploy FAILED"
    printf "%s\n" "$out" | tail -30
    return 1
  }
  printf "%s\n" "$out" | tail -10

  local url
  url=$(printf "%s" "$out" | grep -oE 'https://[a-zA-Z0-9.-]+\.workers\.dev' | head -1 || true)
  [ -z "$url" ] && url="?"
  log "[2/4] deploy OK: $url"

  log "[3/4] set SERVER_ADDRESS secret..."
  printf "%s\n" "$SERVER_ADDRESS" \
    | npx --yes wrangler secret put SERVER_ADDRESS >/dev/null 2>&1 \
    && log "[3/4] secret set OK" \
    || warn "[3/4] secret set failed (set manually later)"

  log "[4/4] smoke test..."
  if command -v curl >/dev/null && [ "$url" != "?" ]; then
    local hc
    hc=$(curl -s -m 10 "$url/health" 2>/dev/null || echo "timeout")
    log "/health: $(printf "%s" "$hc" | head -c 150)"
  fi

  printf "${G}✓${N} %s -> %s\n" "$name" "$url"
  RESULT_URLS+=("$name=$url")
  return 0
}

# ── run ────────────────────────────────────────
hdr "Autonomous AI Company - Live Deploy"
log "Products: 7 MCP servers"
log "Mode: $([ "$USING_BURN" = "yes" ] && echo burn-address-test || echo live)"

RESULT_URLS=()
deploy_one jp-subsidy-mcp      || true
deploy_one toyama-local-mcp    || true
deploy_one jp-business-docs-mcp || true
deploy_one jp-tax-calendar-mcp  || true
deploy_one jp-keigo-checker-mcp || true
deploy_one jp-startup-legal-mcp || true
deploy_one hokuriku-gourmet-mcp || true

# ── revenue watcher setup (real wallet only) ───
if [ "$USING_BURN" = "no" ]; then
  hdr "Revenue Watcher Setup"
  cd "$REPO_ROOT"
  node autonomous/revenue_watcher.mjs set-wallet "$SERVER_ADDRESS" 2>&1 | tail -5 || warn "set-wallet failed"
  node autonomous/revenue_watcher.mjs snapshot   2>&1 | tail -5 || warn "snapshot failed"
fi

# ── summary ────────────────────────────────────
hdr "Deploy Summary"
echo ""
printf "%-22s %s\n" "PRODUCT" "URL"
printf "%-22s %s\n" "----------------------" "-----------------------------------"
for entry in "${RESULT_URLS[@]}"; do
  name="${entry%%=*}"
  url="${entry#*=}"
  printf "%-22s %s\n" "$name" "$url"
done
echo ""

# ── next steps ─────────────────────────────────
hdr "Next Steps"
if [ "$USING_BURN" = "yes" ]; then
  cat <<'EOF'

IMPORTANT: Currently using BURN ADDRESS. Real USDC payments are LOST.

To accept real payments:

  1. Create a Coinbase Wallet on your phone (5 min, free, no KYC).
     App Store / Google Play → "Coinbase Wallet" (NOT the exchange app).
     Save the 12-word recovery phrase on PAPER, never share it.
     Copy your 0x... address (42 chars).

  2. Update the secret for each MCP:

     cd autonomous/products/jp-subsidy-mcp
     echo '0xYourRealAddress' | npx wrangler secret put SERVER_ADDRESS

     cd ../toyama-local-mcp
     echo '0xYourRealAddress' | npx wrangler secret put SERVER_ADDRESS

  3. Register in revenue_watcher:

     cd ../../..
     node autonomous/revenue_watcher.mjs set-wallet 0xYourRealAddress
     node autonomous/revenue_watcher.mjs snapshot

  4. From then on, any USDC paid via x402 goes directly to your wallet.
EOF
else
  echo ""
  echo "✓ Live deploy complete with a real wallet address."
  echo "  Monitor incoming USDC: node autonomous/revenue_watcher.mjs report"
  echo "  Run watcher (every 10 min): node autonomous/revenue_watcher.mjs watch"
fi

echo ""
log "Done."
