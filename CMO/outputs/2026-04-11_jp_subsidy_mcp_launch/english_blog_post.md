# We built an autonomous AI company in rural Japan. Here's our first revenue product.

**Target platforms**: dev.to, Medium, personal blog, Anthropic Cookbook PR
**Length**: ~2,500 words
**Publication date**: jp-subsidy-mcp deploy day (or within 48 hours)

---

## TL;DR

- A solo developer in Toyama, Japan is running a "fully autonomous AI company" experiment
- First revenue product: `jp-subsidy-mcp` — MCP server that searches Japanese government subsidies for AI agents
- Deployed on Cloudflare Workers free tier
- Revenue via x402 (Coinbase × Cloudflare's HTTP 402 stablecoin protocol)
- Zero fiat operating cost, zero ongoing owner labor after deploy
- Source code is fully public
- Built entirely with Claude Code sessions

---

## The setup

I live in Toyama, a rural prefecture on Japan's west coast. I'm a solo technical operator with modest budget: about ¥30,000 ($200) a month allocated to Claude API usage. I don't have an audience, a co-founder, a sales team, or venture funding. I do have Claude Code, a GitHub account, and strong opinions about AI agent economics.

Two months ago, I started experimenting with building what I called an "autonomous AI company" — a repository where five AI "officers" (CDO, CFO, CMO, CPO, CSO) maintain their own work logs, collaborate on projects, and ship real products. The premise was simple:

> Can an AI-operated business framework actually produce revenue-generating work, or does it just produce research theater?

The honest answer after two months is: **research theater is what happens if you don't force a ship date**. So I forced one. On April 11, 2026, we shipped `jp-subsidy-mcp` — the first actual product with a plausible path to revenue.

This post is the technical and operational breakdown of that ship.

---

## Why Japanese subsidies?

Japan's SMB subsidy landscape is a mess. Dozens of national programs (IT導入補助金, 小規模事業者持続化補助金, ものづくり補助金...), layered on top of prefectural programs (Toyama's DX subsidy, traditional industry support), layered on top of municipal programs (Takaoka city creative grants, Toyama city startup grants). Each one has its own website, its own PDF application form, its own deadline schedule, its own eligibility quirks.

Small businesses leave billions of yen on the table every year because:
1. The information isn't indexed in a way AI can use
2. Matching a business profile to the right program is tedious
3. Every application is written in dense bureaucratic Japanese

Meanwhile, AI agents (Claude, ChatGPT, custom agents) are getting really good at answering questions like "what funding is available for my business?" — but only if they have access to structured data.

**That's the gap `jp-subsidy-mcp` fills**: structured, AI-queryable, x402-paid access to the Japanese subsidy landscape.

---

## Why x402 specifically?

If you're building a revenue product in 2026 and haven't looked at x402 yet, you should. It's the quietest big deal of this year.

x402 is Coinbase and Cloudflare's revival of the long-forgotten HTTP 402 "Payment Required" status code. It works like this:

1. A client (often an AI agent) requests a resource
2. The server returns `HTTP 402 Payment Required` with a payment descriptor (amount, currency, network, merchant address, nonce)
3. The client signs a stablecoin payment transaction
4. The client retries the request with a payment header
5. The server verifies the payment via an x402 facilitator (~2 second on-chain settlement)
6. The server delivers the resource

The entire flow takes about 2 seconds end-to-end. No Stripe. No API keys. No subscriptions. No bank accounts on either side. The agent's wallet pays the server's wallet, and that's it.

As of March 2026, x402 has processed:
- **119 million transactions** on Base
- **35 million transactions** on Solana
- **~$600 million annualized volume**
- **Zero protocol fees** (you only pay ~$0.001 blockchain gas)

Cloudflare has shipped `x402-hono` as a first-class middleware for Workers. Integration is **approximately five lines of code**:

```typescript
import { paymentMiddleware } from "x402-hono";

app.use(
  paymentMiddleware(
    SERVER_ADDRESS,
    {
      "/search": {
        price: "$0.05",
        network: "base",
        config: { description: "Search Japanese subsidies" },
      },
    },
    { url: "https://x402.org/facilitator" }
  )
);
```

That's the entire paywall. The middleware handles the 402 dance automatically.

For a solo operator in Japan, this is a watershed moment. Japanese payment infrastructure is notoriously hostile to solo developers (BASE takes 3.6%, Stripe requires corporate verification for most categories, PayPal is unreliable, bank-to-bank transfers are expensive and slow). x402 bypasses all of that. Revenue lands in my self-custody Coinbase Wallet as USDC, and I can cash out whenever I want via a Japanese crypto exchange (bitbank, bitFlyer) — or not at all, and just hold USDC.

---

## The architecture

Here's the complete stack:

```
User or AI agent
  ↓
Cloudflare Workers (free tier)
  ↓
Hono router
  ↓
x402-hono payment middleware (gates paid endpoints)
  ↓
Handler reads static JSON (30 subsidies)
  ↓
Returns filtered results
  ↓
Payment settles on Base → USDC to self-custody wallet
```

Key design choices:

**Free tier constraint**. Cloudflare Workers free tier gives you 100,000 requests per day. At $0.05 per paid request, that's $5,000 per day of theoretical maximum revenue before you need to upgrade. The free tier is a fine place to start.

**Static JSON for data**. I considered running this against a KV or D1 database, but for 30 records, a baked-in JSON file is smaller, simpler, and has zero DB costs. As the dataset grows, I'll migrate to R2 + KV, but by then the server should be paying for itself.

**Free and paid endpoints coexist**. The landing page, health check, and one sample record are free. This is pure marketing: I want people to be able to look at this server without hitting a paywall. All the real value (filter, recommend, detail, full MCP) sits behind x402.

**MCP JSON-RPC support**. On top of the REST API, the server exposes `POST /mcp` for Claude Desktop and other MCP-native clients. They can list tools, call tools, and pay per call, all automatically.

---

## The data

The first release ships with 30 real Japanese government subsidy programs. Here's the breakdown:

**National programs (21)**:
- IT Introduction Subsidy 2026 (up to ¥4.5M)
- SME Sustainability Subsidy (up to ¥2M)
- Manufacturing Subsidy (up to ¥10M)
- Business Restructuring Subsidy (up to ¥15M)
- J-Startup Support (up to ¥5M)
- Career-Up Subsidy (up to ¥800K/employee)
- Work Environment Improvement Grant (up to ¥6M)
- Business Succession Subsidy (up to ¥8M)
- JETRO Export Support (non-monetary)
- R&D Tax Credit (up to ¥25M)
- DX Certification (meta program)
- Tourism DX Promotion (up to ¥5M)
- Regional Revitalization Grant (up to ¥30M)
- Energy Saving Investment (up to ¥10M)
- Green Innovation Fund (up to ¥100M)
- ...plus 6 more

**Toyama prefecture / municipal (9)**:
- Toyama DX Promotion Subsidy (up to ¥500K)
- Toyama Startup Support (up to ¥1M)
- Toyama Traditional Industry Innovation (up to ¥3M)
- Toyama Manufacturing Strengthening (up to ¥5M)
- Toyama Women's Empowerment (up to ¥500K)
- Takaoka City Startup Subsidy (up to ¥500K)
- Toyama City Startup Support (up to ¥1M)
- Nanto City Inami Wood Carving Successor Support (up to ¥2M)
- ...

Each record has an AI compatibility score (0-100) and weighted keywords. The recommend endpoint uses this plus user-supplied context to rank results.

---

## The honest economics

Let me be direct about the expected revenue curve, because every indie hacker writeup is terrible about this.

**Month 1 (April 2026)**: I expect $0–30 in revenue. The MCP discovery ecosystem is still early. Even if everything works perfectly, there are maybe a few thousand people who regularly install new MCP servers on Claude Desktop, and only a fraction will discover this one.

**Months 2-3**: Growing discovery, maybe $10–200/month. Depends entirely on whether the data is genuinely useful and whether I can get a few mentions from AI-interested Japanese Twitter accounts or bigger venues like this blog post.

**Month 6**: If the experiment "works", I'd expect $100–1,000/month. This is the target: a server that covers its non-existent operating cost many times over and generates a modest but real income stream.

**Month 12**: Honestly unknown. The entire MCP economy might consolidate into a few big marketplaces, or it might fragment into thousands of niche servers. This bet is that niche servers with genuine domain data will do fine either way.

The key number is **zero**. Zero operating cost. Zero ongoing labor cost after the 11-minute deploy. Zero downside. At worst, I end up with a great side project and a real case study of x402 deployment from a Japanese solo dev's perspective.

---

## What I used (tools and costs)

This is the full budget:

| Item | Cost |
|------|------|
| Claude Pro + API (for development) | ~¥30,000 / month |
| Cloudflare Workers | $0 |
| Coinbase Wallet (self-custody) | $0 |
| x402 protocol | $0 |
| Hono, x402-hono (npm packages) | $0 |
| Domain (workers.dev subdomain) | $0 |
| **Marginal cost of launching** | **$0** |

My Claude usage was mostly going into building the autonomous AI company framework anyway, so this product is a natural output of that work, not a new expense line item.

---

## What's next

A few things are in the pipeline:

1. **Second MCP server**: `toyama-local-mcp` — Toyama tourism / food / festivals / crafts data, same payment model. Already implemented, deploy pending.

2. **Data expansion**: Moving from 30 to 50+ subsidies in April. The autonomous loop will handle weekly data refreshes once the five AI officers are running in live mode.

3. **MCP Directory submissions**: Once live, I'll submit to PulseMCP, Anthropic's cookbook directory, and any other public MCP registries.

4. **Open source the framework**: The entire 5-officer autonomous AI company framework is already public at `github.com/tyutyutakokaina81-netizen/agent-team`. I'll write a separate post on the framework architecture.

5. **Experiment documentation**: Daily progress lives in `PROGRESS.md`. Failures included. The git history is the honest story.

---

## Can you replicate this?

Yes, and you probably should. The components are:

1. A domain you care about (substitute your country / language / industry for "Japanese subsidies")
2. Structured data for that domain (static JSON is fine to start)
3. A Cloudflare Workers account (free)
4. A self-custody crypto wallet (free)
5. About 200-500 lines of TypeScript
6. The x402-hono npm package

That's it. If you want a working template, fork `autonomous/products/jp-subsidy-mcp/` as a starting point.

The gatekeepers you don't need:
- Stripe approval
- A corporation
- A bank
- Investors
- An existing audience
- A sales team
- Engineers (Claude writes most of this)

What you do need:
- Domain knowledge (about the data you're exposing)
- A willingness to ship a tiny, ugly first version
- An acceptance that month 1 revenue is probably $0

---

## Getting in touch

GitHub issues are my preferred channel. Bug reports, data corrections, and feature requests are all welcome.

Follow the autonomous AI company experiment at `github.com/tyutyutakokaina81-netizen/agent-team`.

The repo is MIT. The company is fictional. The USDC is real.

---

🤖 Built and maintained by an autonomous AI company based in Toyama, Japan.
