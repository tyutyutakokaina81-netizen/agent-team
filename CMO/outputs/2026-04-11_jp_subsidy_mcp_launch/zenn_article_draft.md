# 富山発・自立型AI企業が初めて収益商品を公開した話：日本補助金検索 MCP サーバーを x402 でマネタイズ

**公開予定日**：jp-subsidy-mcp deploy 完了後、即日

**Topics**: `mcp` `claude` `x402` `cloudflare` `autonomous-ai` `補助金`

---

## TL;DR

- 富山県在住のソロ開発者が、Claude / Claude Code で「自立型AI企業」を構築
- 第1号収益商品として **jp-subsidy-mcp**（日本の補助金検索 MCP サーバー）を Cloudflare Workers にデプロイ
- **x402 プロトコル**で $0.05 USDC / リクエストの自動決済ゲートを実装
- 運営コスト **¥0**、手数料 **0%**、完全 autonomous に動く
- コードは GitHub で公開、誰でも呼び出せる

**Live URL**: `https://jp-subsidy-mcp.<subdomain>.workers.dev`

---

## 背景：なぜ「自立型AI企業」を作ったか

2026年4月現在、AI エージェント経済のインフラは既に整いつつあります：

- **Coinbase Agentic Wallets**（2026-02-11 launch）: AI agent 専用の crypto wallet
- **x402 protocol**（Coinbase × Cloudflare）: HTTP 402 "Payment Required" を使った stablecoin マイクロ決済
- **Model Context Protocol (MCP)**: Claude と他の AI エージェントを tools でつなぐ標準
- **Cloudflare Workers**: 月 10 万 req まで無料の serverless プラットフォーム

これらを組み合わせると、**人間の介入を最小限に保ったまま**、AI agent 同士が自律的に価値交換する仕組みが、手元で動かせます。

富山県在住の個人開発者として、「完全自律で回る AI 企業」を実験的に構築し、その第1号商品がこの jp-subsidy-mcp です。

---

## なぜ「日本補助金検索」なのか

日本の中小企業は毎年、数百種類の補助金・助成金にアクセスできます。しかし：

- 情報がバラバラ（各省庁・各自治体のサイトに散在）
- 申請書作成が複雑（事業計画書・収支計画書など）
- マッチング判定が難しい（どの補助金が自分に合うか）

一方、**AI agent（Claude / ChatGPT 等）を使えば**：

- 自然言語で「DX 推進したいけど補助金ある？」と聞ける
- AI が自動で該当する制度を提示
- 申請書ドラフトまで生成できる

ただし、**最新の補助金データに AI がアクセスする方法** がこれまで無かった。MCP サーバーがそれを解決します。

そして、x402 protocol を使えば、**利用料を API key 不要・アカウント不要・決済手数料ゼロで徴収できます**。AI エージェントが自律的に USDC で支払うだけ。

---

## 技術スタック

| 要素 | 採用技術 |
|---|---|
| ランタイム | Cloudflare Workers（無料枠）|
| フレームワーク | Hono（軽量・Workers ネイティブ）|
| 決済 | x402-hono（Coinbase 公式 middleware）|
| 決済ネットワーク | Base（2 秒決済、ガス代 $0.001 以下）|
| ストレージ | 静的 JSON（data/subsidies.json）|
| プロトコル | MCP JSON-RPC over HTTP |
| 料金 | $0.02 〜 $0.10 USDC per request |

コード量：TypeScript 465 行のみ。

---

## 実装のハイライト

### 1. x402 payment middleware の適用

```typescript
import { paymentMiddleware } from "x402-hono";

app.use("*", async (c, next) => {
  // 無料エンドポイントはスキップ
  if (path === "/" || path === "/health" || path === "/info") {
    return next();
  }

  const middleware = paymentMiddleware(
    c.env.SERVER_ADDRESS as `0x${string}`,
    {
      "/search": {
        price: `$0.05`,
        network: "base",
        config: { description: "Search Japanese subsidies by keyword" },
      },
      // ...
    },
    { url: "https://x402.org/facilitator" }
  );
  return middleware(c, next);
});
```

これだけで、`/search` を叩いてくる AI エージェントは自動的に HTTP 402 を受け取り、x402 facilitator 経由で Base ネットワーク上の USDC を自動支払いし、2 秒後にレスポンスを受け取れます。

### 2. MCP JSON-RPC のシンプル実装

MCP は JSON-RPC 2.0 over HTTP なので、特別な SDK 無しでも Hono で直接書けます：

```typescript
app.post("/mcp", async (c) => {
  const { method, params, id } = await c.req.json();

  if (method === "tools/list") {
    return c.json({
      jsonrpc: "2.0",
      id,
      result: {
        tools: [
          {
            name: "search_subsidies",
            description: "日本の補助金・助成金を検索する",
            inputSchema: { type: "object", properties: { query: { type: "string" } } },
          },
          // ...
        ],
      },
    });
  }
  // tools/call の実装...
});
```

Claude Desktop から呼び出す場合は、設定ファイルに以下を追加するだけ：

```json
{
  "mcpServers": {
    "jp-subsidy": { "url": "https://jp-subsidy-mcp.yourdomain.workers.dev/mcp" }
  }
}
```

### 3. AI 適合度スコア付きレコメンド

14 件の seed データ各件に `fit_score_ai` フィールド（0-100）を付けています。`/recommend` エンドポイントでは事業コンテキスト（業種・地域・ステージ）からスコアを重み付けして上位 5 件を返します。

富山県内限定の補助金は、地域マッチで +20 点のボーナスが入るので、富山の事業者が呼ぶと地元の制度が優先表示されます。

---

## 運営コスト

| 項目 | 月額 |
|---|---|
| Cloudflare Workers（無料枠）| $0 |
| Coinbase Wallet（self-custody）| $0 |
| x402 protocol fee | $0 |
| ドメイン（workers.dev サブドメイン）| $0 |
| **合計** | **$0** |

**GitHub Sponsor も集客用アドも使っていません**。コード公開・無料チャネル・organic 発見のみ。

---

## リアルな期待値

- 初月の売上：$0 〜 $30 程度（MCP ディスカバリーは始まったばかり）
- 3 ヶ月後：月 $10 〜 $100 の range を想定
- ベスト case：Anthropic/Coinbase の公式 directory に取り上げられて $500/月 まで伸びる可能性

重要なのは**金額よりも、"完全 autonomous で回る収益経路"が1本開通すること**です。これが起点となって、第2号・第3号の MCP サーバーを同じパターンで量産できます。

---

## GitHub

コード・データ・デプロイ手順：

- GitHub: `github.com/tyutyutakokaina81-netizen/agent-team`
- 直接パス: `autonomous/products/jp-subsidy-mcp/`
- ライセンス: MIT

Issue / PR ウェルカムです。特に「この補助金が抜けている」の情報提供は大歓迎。

---

## 次にやること

- [ ] 補助金データを 14 件 → 50 件に拡充
- [ ] 自律ループで週次自動更新（各省庁の公開 RSS をクロール）
- [ ] 第2号 MCP: `toyama-local-mcp`（富山観光・飲食・イベント）
- [ ] 第3号 MCP: `jp-seo-keyword-mcp`（日本語 SEO 分析）
- [ ] Anthropic MCP Directory 登録申請

---

## 最後に

**富山発**の完全自律型 AI 企業の実験として、公開しています。コード・進捗・失敗も全て GitHub で可視化しています。

もし興味があれば：

- GitHub でスターを付けてもらえると励みになります ⭐
- Twitter / X では `#autonomous_ai_toyama` タグを使います
- 質問・アドバイスは GitHub Issue まで

2026 年の AI agent economy は、始まったばかりです。この実験がその小さな一歩になれば。

🤖 Built in Toyama, Japan
