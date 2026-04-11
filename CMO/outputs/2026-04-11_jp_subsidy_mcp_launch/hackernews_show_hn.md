# Hacker News Show HN 投稿ドラフト

**投稿予定**: jp-subsidy-mcp deploy 完了日
**サブミット URL**: https://news.ycombinator.com/submit
**推奨時間帯**: 米国東部時間 8-10am (UTC-5) / 日本時間 21-23時

---

## Title（推奨、最も成功しやすい順）

### Option A（技術フックを全面）
```
Show HN: Autonomous AI company in rural Japan ships its first x402 MCP server
```

### Option B（興味を引きやすい）
```
Show HN: Jp-subsidy-mcp – x402-paid MCP server for Japanese government subsidies
```

### Option C（具体的な数字）
```
Show HN: We built a Japanese subsidy MCP server (x402 paywall, $0 ops cost)
```

**推奨**: **Option A** — "rural Japan" + "autonomous AI company" + "x402" で HN の好奇心を 3 つ同時に引く。

---

## URL

```
https://jp-subsidy-mcp.<your-subdomain>.workers.dev
```

または GitHub リポジトリ:
```
https://github.com/tyutyutakokaina81-netizen/agent-team
```

**推奨**: live URL を主 URL、GitHub はコメントで追加。

---

## 本文（HN 投稿本文、80 wordcount 目安）

HN の Show HN 投稿は本文なしか、短い 1-2 段落でも OK。以下は本文を付ける場合のドラフト。

### Post Body Draft（英語、140 words 以内）

```
Hi HN — solo dev in Toyama, Japan here. I shipped an x402-paid MCP server that searches Japanese government subsidies. Claude Desktop / other agents can pay $0.05 USDC per query via the x402 protocol, settle on Base in ~2 seconds, and get back structured subsidy data.

Stack: Cloudflare Workers (free tier) + Hono + x402-hono middleware. ~470 lines of TypeScript. Zero fiat operating cost.

The bigger experiment is "can an autonomous AI company actually ship a revenue product from a rural Japanese prefecture with no audience, no funding, and no manual labor after deploy?" This server is the first data point. Source code, data, and daily progress log all public.

Happy to answer questions about x402 integration, the autonomous company framework, or Japan's subsidy landscape.
```

---

## 初期コメントでセルフ返信（推奨）

HN の慣例として、OP 自身が最初のコメントで追加情報を置くと upvote されやすい。

### First comment draft

```
A few technical notes I couldn't fit in the body:

1. x402-hono integration is literally ~5 lines. The middleware handles the 402 dance, signature verification, and facilitator callback. I spent more time tuning the JSON schema than the payment logic.

2. The "free endpoints" (/health, /info, /free/list) are critical for discovery. Claude agents will hit /info first to understand pricing before calling /search. If /info is paid, agents skip you entirely.

3. Self-custody Coinbase Wallet works fine for Japan-residents to *receive* USDC. KYC is only needed to *convert* USDC to JPY via bitbank / bitFlyer. I'm deferring that until the first few payments arrive.

4. The 30 subsidies in the initial dataset are hand-curated from public Japanese government sources. The plan is to have the autonomous AI loop refresh them weekly once the broader framework is running live.

5. Full source at github.com/tyutyutakokaina81-netizen/agent-team — the jp-subsidy-mcp server is under autonomous/products/jp-subsidy-mcp/. The repository also contains the complete 5-officer autonomous AI company framework (budget_guard, orchestrator, officer_runner, memory, dashboard, revenue watcher).

Would love feedback on both the MCP server itself and the broader "autonomous AI company" architecture. Roast me.
```

---

## 想定質問と回答テンプレート

HN コメントでよく聞かれるであろう質問と、事前に準備した回答。

### Q: Why x402 instead of Stripe?

```
Three reasons:
1. Stripe requires corporate verification for my category in Japan (financial data services). That's months of paperwork for a solo dev.
2. x402's $0.001 micropayment floor is unreachable with Stripe's 3.6% + fixed fee structure.
3. x402 is protocol-level integration — an AI agent can pay without human involvement. Stripe always requires a human to sign up for a subscription.

For an AI-agent-facing paid API, x402 is strictly better.
```

### Q: What's the incentive for users to pay instead of using free alternatives?

```
There are basically zero free Japanese subsidy APIs. The "free alternatives" are:
- Manually scraping government PDFs (brittle, hours of work)
- Paying a consultant ¥50,000+ per advisory session
- Reading 10+ government websites in Japanese

$0.05 per query is ~1/1,000,000 the cost of the consultant alternative. The price-to-value ratio is absurdly in favor of paying.
```

### Q: Isn't this just going to be replaced by the LLM directly answering the question?

```
LLMs hallucinate subsidy details constantly. I tested Claude 4.5 on "Toyama DX subsidy" and got wrong amounts, wrong deadlines, wrong URLs. Structured data with provenance is the moat. If anything, as LLMs get better at *asking* for real data (via MCP), structured data servers get more valuable, not less.
```

### Q: How does USDC → JPY actually work for a Japanese resident?

```
I haven't converted any USDC yet (waiting for the first payments). The path is:
1. Self-custody wallet receives USDC on Base
2. Bridge or send to a Japanese licensed exchange (bitbank, bitFlyer, SBI VC Trade — Circle launched USDC on SBI VC Trade in March 2025)
3. Complete KYC once (~1 business day)
4. Sell USDC for JPY, withdraw to bank
5. Report as miscellaneous income on tax return

For my volume, I might not convert at all and just hold USDC as a dollar-denominated savings vehicle.
```

### Q: Why "rural Japan"?

```
Partially honest framing: Toyama is 200km+ from Tokyo, no real tech scene, no AI meetup community, no venture capital ecosystem, no easy access to customers. It's a hard mode test of whether the MCP + x402 economics can actually work for someone outside the usual SF/NY/Tokyo bubble.

If it works here, it works anywhere. If it doesn't work here, that's valuable data too.
```

### Q: What's the autonomous AI company framework?

```
It's 5 "officer" AIs (CDO, CFO, CMO, CPO, CSO) that run in a daily loop via Cloudflare Workers cron. Each officer reads context, decides a daily task, writes to their own directory, updates an index, and commits. There's a budget_guard that hard-caps Claude API spend at ¥2000/month with a revenue-gated mode (only spends if revenue exists).

Full code: `autonomous/` in the repo. The framework is roughly 2000 lines of TypeScript/JavaScript. jp-subsidy-mcp is the first *product* output of this framework, though honestly I'm still ramping the framework itself and this first product was built by me (with heavy Claude Code assistance) not the fully autonomous loop.
```

### Q: Can I fork this?

```
MIT licensed, fork away. The stack is genuinely reusable for any domain where structured data + paid access makes sense. I'd suggest starting with your own domain knowledge (legal docs for your country, industry-specific reference data, niche technical docs) rather than copying the Japanese subsidy angle.
```

### Q: Any tips on getting discovered on the MCP directory?

```
PulseMCP accepts submissions via GitHub PR. Anthropic's official MCP directory is still selective but public. The better strategy might be submitting a cookbook example to the Anthropic cookbook repo — that gets you official visibility without having to go through a directory's gate.

I'm planning all three paths: PulseMCP submission, Anthropic cookbook PR, and hoping to get noticed organically via HN / Twitter.
```

---

## 投稿後の 24 時間チェックリスト

- [ ] 投稿直後（～30 分）: 最初のセルフコメントを投下
- [ ] 1 時間後: コメントに返信、質問にテンプレで対応
- [ ] 3 時間後: Traffic のピークなので、コメント対応に集中
- [ ] 6 時間後: Twitter / Zenn にクロスポスト
- [ ] 12 時間後: 有用なフィードバックを GitHub issue に切り出し
- [ ] 24 時間後: 投稿の振り返り（upvote 数・コメント数・GitHub stars 増加・MCP への実アクセス数）

---

## 成功指標（Show HN の現実的な数字）

| 指標 | 控えめ | 基本 | 強気 |
|---|---|---|---|
| Upvote (24h 時点) | 5-15 | 30-80 | 150+ (front page) |
| コメント数 | 2-5 | 10-25 | 50+ |
| GitHub stars 増加 | 3-10 | 15-40 | 100+ |
| /info エンドポイントアクセス | 20-50 | 100-300 | 500+ |
| 初 USDC 入金 | 0 件 | 0-2 件 | 2-10 件 |

**front page 到達** (upvote 50+ in 1 hour) できれば最良シナリオ。そうでなくても 30 upvote 以上で十分な二次流通（Reddit, Twitter, blogs）が期待できる。

---

## 投稿に関する注意

1. **投稿前に必ず deploy を完了**。リンク切れは即死
2. **タイトルに "Show HN:" を必ず付ける**。HN 慣例
3. **URL にはクエリパラメータを含めない**（トラッキング用 `?utm_source=hn` 等は reject される傾向）
4. **本文に絵文字を使わない**（HN 慣例的に嫌われる）
5. **自慢や誇張を避ける**（"revolutionary", "game-changing" は禁句）
6. **質問されたら 1 時間以内に返信**。最初の数時間がすべて
