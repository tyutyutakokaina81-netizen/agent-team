# jp-subsidy-mcp

A Japan-first MCP server that searches and recommends Japanese government subsidies, grants, and IT procurement support programs — with built-in x402 payment gating.

**Built by**: An autonomous AI company operating from Toyama, Japan.
**First revenue product** in a series of self-operating MCP servers.

## What It Does

- Hosts 30 real Japanese subsidy programs (national + Toyama prefecture + municipal)
- Each program tagged with AI-compatibility score (0-100)
- Accepts natural-language queries via MCP or REST
- Auto-charges $0.02–$0.10 USDC per call via x402 protocol
- Runs on Cloudflare Workers free tier
- Zero ongoing infrastructure cost

## Why It Matters

The Japanese subsidy landscape is:
- Scattered across ministries and local governments
- Poorly indexed for AI agents
- Updated on rolling quarterly cycles
- Almost entirely Japanese-language

Japanese SMBs leave billions of yen on the table every year because they don't know which programs they qualify for. An AI agent with access to this data can surface matches in one natural-language call.

**This MCP is the connective tissue** between Claude (and other agents) and Japan's public funding infrastructure.

## Pricing (x402 auto-settlement)

| Endpoint | Price | Description |
|----------|-------|-------------|
| `GET /` | Free | HTML landing page |
| `GET /health` | Free | Health check |
| `GET /info` | Free | Server metadata |
| `GET /free/list` | Free | Single random sample (advertising) |
| `POST /search` | **$0.05 USDC** | Keyword search |
| `POST /recommend` | **$0.10 USDC** | Context-aware recommendations |
| `POST /detail` | **$0.02 USDC** | Single program lookup |
| `POST /mcp` | **$0.05 USDC** | MCP JSON-RPC endpoint |

All payments settle on Base network in ~2 seconds. Zero protocol fees. No Stripe, no bank accounts, no KYC for receiving.

## How It Works

1. An AI agent (Claude Desktop, ChatGPT, custom agent) asks a user-level question like "what IT subsidies are available for a small business doing DX in Toyama?"
2. The agent calls `POST /search` on this server
3. The server returns HTTP 402 "Payment Required" with x402 payment details
4. The agent's wallet auto-signs a USDC payment on Base
5. The server verifies the payment via the x402 facilitator
6. The server returns the search results
7. USDC lands directly in the operator's self-custody wallet

**Total round-trip: ~2 seconds**. No human involvement after deployment.

## Claude Desktop Setup

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac) or equivalent:

```json
{
  "mcpServers": {
    "jp-subsidy": {
      "url": "https://jp-subsidy-mcp.<your-subdomain>.workers.dev/mcp"
    }
  }
}
```

Your Claude Desktop will now automatically call this server when you ask about Japanese subsidies.

## Technology Stack

- **Runtime**: Cloudflare Workers (free tier, 100K req/day)
- **Framework**: Hono (Workers-native, zero-config)
- **Payment**: x402-hono middleware (~5 lines to integrate)
- **Network**: Base (Coinbase L2, USDC)
- **Language**: TypeScript, ~470 lines
- **Data**: Static JSON (30 programs, will grow to 50+ autonomously)
- **Protocol**: MCP JSON-RPC over HTTP

## Running Cost

| Item | Monthly |
|------|---------|
| Cloudflare Workers | $0 (free tier) |
| Coinbase Wallet | $0 (self-custody) |
| x402 protocol fees | $0 |
| Domain | $0 (workers.dev subdomain) |
| **Total** | **$0** |

There is no revenue floor. The server can sit idle with zero users and still cost zero to operate.

## Source Code

Full source: [github.com/tyutyutakokaina81-netizen/agent-team](https://github.com/tyutyutakokaina81-netizen/agent-team) — specifically `autonomous/products/jp-subsidy-mcp/`.

MIT licensed. PRs welcome, especially for adding new subsidy data.

## Deployment

See [DEPLOY_11MIN.md](./DEPLOY_11MIN.md) for the 11-minute setup walkthrough.

Required owner actions (one-time, free):
1. Create Coinbase Wallet (self-custody) — 5 min
2. Create Cloudflare account — 3 min
3. Generate Cloudflare API token — 2 min
4. Pass wallet address and API token to deployer — 1 min

Zero fiat spend, zero ongoing labor.

## Data Quality & Disclaimer

All subsidy information is sourced from public Japanese government websites. It is a snapshot; always verify current eligibility, amounts, and deadlines with the official sources before applying.

Not financial, tax, or legal advice.

## What Makes This Different

1. **First-mover in Japanese-language MCP**: Of the 20,000+ MCP servers currently listed, almost none target Japan-specific use cases in Japanese.

2. **Revenue-native, not donation-native**: Unlike free MCP servers that decay from neglect, x402 micropayments create a financial incentive for the operator (or, in this case, the autonomous AI company) to keep the data fresh.

3. **Deployed by an AI company**: This server is designed, implemented, and maintained by a 5-officer AI company framework. The human operator's only job is a one-time 11-minute setup.

4. **Region-aware**: Toyama Prefecture programs get a recommendation boost when queries come from users in Toyama. The same pattern applies to other prefectures as data expands.

## Roadmap

- [x] 30 subsidies (national + Toyama)
- [ ] 50+ subsidies by end of April 2026
- [ ] Weekly autonomous data refresh (5-officer loop reads public sources)
- [ ] Other prefecture packs (Ishikawa, Fukui to start)
- [ ] Subsidy application draft generator (as separate paid MCP)
- [ ] Anthropic MCP Directory listing
- [ ] Integration with Anthropic Cookbook examples

## Building Along With Us

This is part of a larger experiment: **can a solo developer in a rural Japanese prefecture ride the MCP economy using only Claude Code, a Coinbase Wallet, and Cloudflare Workers?**

Follow the experiment:
- GitHub: [tyutyutakokaina81-netizen/agent-team](https://github.com/tyutyutakokaina81-netizen/agent-team)
- Progress log: `autonomous/products/jp-subsidy-mcp/PROGRESS.md`
- Daily commits: all decisions, failures, and pivots are in the git history

---

🤖 Built and maintained by an autonomous AI company based in Toyama, Japan.
