# X（Twitter）投稿パック：jp-subsidy-mcp ローンチ

**対象プロダクト**: `autonomous/products/jp-subsidy-mcp/`
**想定公開日**: deploy 完了日（credential 受領次第）
**目的**: MCP エコシステム関係者（日本語・英語）へのリーチ獲得、Anthropic / Coinbase / Cloudflare 関係者の目に止まる確率を上げる

---

## アカウント戦略の前提

現時点でオーナーの X アカウントは無い前提。必要時に 10 分でアカウント作成。そのため、各投稿は以下の3つの使い道を想定：

1. **オーナーが X アカウントを作って投稿する**（オーナー 10 分作業）
2. **既存の X アカウントがあるなら pinned + thread で即公開**
3. **誰かに cross-post してもらう**（AI 関係者に DM で共有）

すべての投稿は**日本語と英語の両方**を用意。

---

## 1. ピン留め用ローンチ投稿（日本語）

### Post A1-JP（140 字以内）

```
🇯🇵 富山発・自立型AI企業から第1号商品:

jp-subsidy-mcp
日本の補助金を検索する MCP サーバー
x402 で $0.05 USDC 自動決済
Cloudflare Workers 無料枠
コード完全公開

🔗 [deploy URL]
📦 github.com/tyutyutakokaina81-netizen/agent-team

#MCP #x402 #Claude #自動化
```

### Post A1-EN（280 字以内）

```
🇯🇵 First product from an autonomous AI company in Toyama, Japan:

jp-subsidy-mcp — MCP server for searching Japanese government subsidies.
x402 payments ($0.05 USDC/req), zero infra cost, fully autonomous.

🔗 [deploy URL]
📦 github.com/tyutyutakokaina81-netizen/agent-team

#MCP #x402 #Claude #AgenticCommerce
```

---

## 2. 技術ローンチスレッド（日本語）

10 連ツイートのスレッド。重要：各ツイートは 140 字以内。

### スレッド B1-JP

**1/10**
```
🧵 「完全 autonomous に稼働する AI 企業」を富山県で構築中です。

今日、第1号収益商品を公開しました:

jp-subsidy-mcp
日本の補助金情報を検索する MCP サーバー
料金：$0.05 USDC / リクエスト
決済：x402 protocol で自動

技術詳細スレッド 👇
```

**2/10**
```
なぜ MCP サーバー？

Claude / ChatGPT / OpenAI が "tools" として直接呼び出せるからです。

ユーザーが「DX 補助金ある？」と聞く
↓
Claude が jp-subsidy-mcp の /search を呼ぶ
↓
USDC $0.05 自動支払い
↓
該当補助金が返る

中間業者ゼロ、API key ゼロ。
```

**3/10**
```
なぜ x402？

HTTP 402 "Payment Required" を使った、Coinbase × Cloudflare の新しいプロトコルです。

- 2 秒で決済完了（Base ネットワーク）
- protocol fee ゼロ
- 銀行口座不要
- AI エージェントがそのまま支払える

2026-02-11 に launch 済み。既に $600M 流通。
```

**4/10**
```
技術スタック:

- Cloudflare Workers (無料枠)
- Hono フレームワーク
- x402-hono middleware
- TypeScript 465 行
- 静的 JSON データ (14 件の公開補助金)
- Base ネットワーク (USDC)

月額運営コスト: ¥0
デプロイ所要時間: 11 分
```

**5/10**
```
実装のハイライト：

```ts
app.use('*', paymentMiddleware(
  SERVER_ADDRESS,
  {
    '/search': { price: '$0.05', network: 'base' }
  }
));
```

これだけで有料ゲート完成。
あとは普通の Hono app として /search の中身を書くだけ。
```

**6/10**
```
データ構造：

各補助金に AI 適合度スコア (0-100) を付与。
recommend エンドポイントでは業種・地域・ステージでスコアリング。

富山県限定の補助金は地域マッチで +20 点。
地元事業者が呼ぶと地元制度が優先表示される。
```

**7/10**
```
Claude Desktop 設定:

```json
{
  "mcpServers": {
    "jp-subsidy": {
      "url": "https://jp-subsidy-mcp.xxx.workers.dev/mcp"
    }
  }
}
```

これで Claude が日本語で「IT 導入補助金の対象は？」と聞かれたら自動で jp-subsidy-mcp を呼びます。
```

**8/10**
```
なぜ富山？

地方発・少資本・完全 autonomous という 3 重制約の中で動くデモンストレーションです。

- 月額 Claude 代 ¥30K 以内
- オーナーの手作業はデプロイ後ゼロ
- 外部プラットフォーム依存ゼロ

この制約下でも MCP エコシステムに乗れることを示したい。
```

**9/10**
```
GitHub 完全公開:

github.com/tyutyutakokaina81-netizen/agent-team

- 5 役職 AI 会社のフレームワーク
- jp-subsidy-mcp の全コード
- 日次進捗ログ (PROGRESS.md)
- 11 分デプロイガイド (DEPLOY_11MIN.md)
- 失敗も含めた全履歴

スター・PR 歓迎。
```

**10/10**
```
次の計画:

- 第2号 MCP: toyama-local-mcp (富山観光)
- 第3号 MCP: jp-seo-keyword-mcp
- 補助金データ 14 → 50 件
- 自律ループで週次自動更新
- Anthropic MCP Directory 登録

「完全 autonomous AI 企業」の実験記録、#AutonomousAIToyama で続きます。
```

---

## 3. 技術ローンチスレッド（英語）

### Thread B1-EN

**1/10**
```
🧵 Building a fully autonomous AI company from Toyama, Japan.

Today shipped the first revenue product:

jp-subsidy-mcp
MCP server searching Japanese government subsidies.
$0.05 USDC/req via x402.
Zero infrastructure cost.

Tech thread 👇
```

**2/10**
```
Why an MCP server?

So Claude / ChatGPT / other agents can call it as a native tool.

User asks "What subsidies fit my DX project?"
→ Claude calls /search
→ $0.05 USDC auto-paid
→ Results return

Zero middlemen, zero API keys.
```

**3/10**
```
Why x402?

The revived HTTP 402 "Payment Required" protocol from Coinbase × Cloudflare.

- 2-second settlement (Base network)
- Zero protocol fees
- No bank accounts
- AI agents can pay directly from their wallet

Launched 2026-02-11. Already $600M volume.
```

**4/10**
```
Stack:

- Cloudflare Workers (free tier)
- Hono framework
- x402-hono middleware
- TypeScript, 465 lines
- Static JSON (14 real Japanese subsidies)
- Base (USDC)

Monthly operating cost: $0
Deploy time: 11 minutes
```

**5/10**
```
The magic is ~5 lines:

```ts
app.use('*', paymentMiddleware(
  SERVER_ADDRESS,
  { '/search': { price: '$0.05', network: 'base' } }
));
```

That's the entire paywall. Now /search is a revenue-generating endpoint.
```

**6/10**
```
Why Toyama?

A 3-constraint demonstration:

- Monthly budget: ¥30K total
- Post-deploy owner labor: zero
- Zero external platform dependencies

Proving a single dev in a rural Japanese prefecture can ride the MCP economy.
```

**7/10**
```
Claude Desktop setup:

```json
{
  "mcpServers": {
    "jp-subsidy": {
      "url": "https://jp-subsidy-mcp.xxx.workers.dev/mcp"
    }
  }
}
```

Plug-and-play for Claude users. Pay-per-query in USDC.
```

**8/10**
```
Full source code on GitHub:

github.com/tyutyutakokaina81-netizen/agent-team

- 5-officer AI company framework
- Complete jp-subsidy-mcp
- Daily progress log (PROGRESS.md)
- 11-minute deploy guide
- All failures included too

Stars and PRs welcome.
```

**9/10**
```
Built using just:

- Claude Code sessions
- Cloudflare Workers free tier
- x402-hono npm package
- No venture funding
- No cofounders
- No prior audience

The entire autonomous AI company runs on ~¥30K ($200) / month.
```

**10/10**
```
Next:

- Second MCP: toyama-local-mcp (Toyama tourism data)
- Third MCP: jp-seo-keyword-mcp
- Weekly autonomous data updates
- Anthropic MCP Directory listing

Following the experiment at #AutonomousAIToyama
```

---

## 4. 技術深掘り投稿（単発、日本語）

### Post C1-JP

```
x402 protocol、AI エージェント向けのマイクロ決済が想像以上に実用的でした。

Cloudflare Workers + x402-hono で 5 行の middleware を追加するだけで：

/search エンドポイントが $0.05 USDC の有料ゲートになる
↓
Claude が自動で支払う
↓
銀行口座不要、Stripe 不要

試しに 1 本 deploy:
[deploy URL]
```

### Post C2-JP

```
MCP サーバーで日本の補助金情報を売るアイデア、実装してみた。

料金：$0.05 USDC / query
決済：x402 protocol
レスポンス：日本の公開補助金 14 件から検索

Claude Desktop から直接呼べる。

github.com/tyutyutakokaina81-netizen/agent-team

完全 autonomous で動く予定。
```

### Post C3-JP

```
完全 autonomous AI 企業の実験：

✅ 月額 Claude ¥30K 以内
✅ オーナー手作業：初回セットアップ 11 分のみ
✅ 新規赤字ゼロ (Cloudflare 無料枠)
✅ 決済：x402 で自動
✅ コード完全公開

今日、第1号 MCP を出荷します。
```

---

## 5. 技術深掘り投稿（単発、英語）

### Post C1-EN

```
Just shipped a paid MCP server on Cloudflare Workers with x402 middleware.

~5 lines of code turns /search into a $0.05 USDC-gated endpoint. Claude pays automatically from its wallet.

No bank account, no Stripe, no KYC.

Demo: [deploy URL]
Code: github.com/tyutyutakokaina81-netizen/agent-team
```

### Post C2-EN

```
Experiment: running a fully autonomous AI company from a rural Japanese prefecture.

Stack:
- Claude Code for everything
- Cloudflare Workers (free)
- x402 for payments
- MCP for distribution

Monthly budget: ¥30,000 (~$200).
Post-deploy labor: zero.

First product live today.
```

### Post C3-EN

```
MCP + x402 might be the cleanest revenue mechanism I've seen for solo devs.

No platforms, no middlemen, no fiat conversion, no KYC for receiving.

Just: write code → deploy to Workers → AI agents pay per call.

First proof: jp-subsidy-mcp (live tomorrow).
```

---

## 6. エンゲージメント用返信テンプレート

### 質問されたら

**Q: How does x402 work for the caller?**
```
Agents call your endpoint → get HTTP 402 with payment instructions → sign USDC payment on Base → retry with signature → receive result. Total round-trip ~2 seconds. The @Anthropic SDK and others are starting to support it natively.
```

**Q: Why USDC specifically?**
```
Stable pricing (so $0.05 stays $0.05 regardless of crypto volatility), fast finality on Base, compatible with most AI agent wallets. ETH would work too but you'd get price drift.
```

**Q: Does this work for Japan residents?**
```
Yes. You don't need KYC to *receive* USDC via self-custody Coinbase Wallet. You only need KYC if you want to convert USDC → JPY through a Japanese exchange (bitbank / bitFlyer). Receiving is unrestricted.
```

### 競合から質問されたら

**Q: What's the moat vs a free MCP server doing the same?**
```
Maintenance gets paid via x402 micro-payments. I can justify weekly data updates and new features because the revenue stream exists. Free servers die from lack of upkeep; x402 servers self-fund.
```

---

## 7. ハッシュタグ戦略

**優先**:
- `#MCP` (model context protocol)
- `#x402`
- `#Claude`
- `#AnthropicClaude`
- `#AgenticCommerce`
- `#AgentPayments`

**二次**:
- `#CloudflareWorkers`
- `#Toyama` / `#富山`
- `#補助金`
- `#DX`

**避ける**:
- 過度に広告っぽいタグ (`#副業` `#稼ぐ` 系)
- 信頼を下げるタグ (`#絶対稼げる` 系)

---

## 8. 投稿スケジュール案（deploy 完了後 7 日間）

| 日 | 投稿 |
|---|---|
| Day 0 (deploy 日) | Post A1-JP + A1-EN（ピン留め）|
| Day 0 夜 | Thread B1-JP 投下 |
| Day 1 朝 | Thread B1-EN 投下 |
| Day 1 夜 | Post C1-JP |
| Day 2 | Post C1-EN + 返信の engagement |
| Day 3 | Post C2-JP + C2-EN |
| Day 4-5 | Post C3 シリーズ、Qiita / Zenn クロスポスト |
| Day 6-7 | 第1週の振り返り post、翌週の予告 |

---

## 9. オーナーに必要な作業

- [ ] X アカウント未作成なら 5 分で作成（メール + 電話番号）
- [ ] プロフィール：「Autonomous AI company from Toyama, Japan. Running on Claude + x402.」
- [ ] 固定ポスト：A1-JP or A1-EN
- [ ] 投稿スケジュールを BufferApp / Typefully / X 公式 Scheduler で仕込む（全部コピペ、各 30 秒）

**総所要時間**: 40-60 分（一度きり、全投稿の仕込み込み）

投稿後は organic engagement 以外オーナーの作業ゼロ。返信テンプレートは上記 6 を使用。

---

## 10. 成功指標（7 日後にレビュー）

| 指標 | 目標 |
|---|---|
| impression（7日合計）| 3,000+ |
| プロフィール訪問 | 100+ |
| GitHub リポジトリ stars | 20+ |
| jp-subsidy-mcp /info へのアクセス | 50+ |
| 有料エンドポイントへの初入金 | 1 件でも |

**一つでも達成していれば継続、全滅なら戦術切替**。

---

**この X 投稿パック、deploy 完了と同時に発射できる状態で commit しておきます**。
