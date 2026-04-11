// jp-subsidy-mcp / src/index.ts
//
// Cloudflare Workers で動く、日本の補助金検索 MCP サーバー。
// x402 payment middleware で有料アクセスを USDC で自動決済する。
//
// 無料エンドポイント（広告・獲得目的）:
//   GET  /           - HTML ランディングページ
//   GET  /health     - ヘルスチェック
//   GET  /info       - サーバーメタ情報
//   GET  /free/list  - 補助金1件だけランダム表示
//
// 有料エンドポイント（x402 支払い必須）:
//   POST /search     - キーワード検索（$0.05 USDC / req）
//   POST /recommend  - 状況からレコメンド（$0.10 USDC / req）
//   POST /detail     - 1件の詳細取得（$0.02 USDC / req）
//   POST /mcp        - MCP JSON-RPC エンドポイント（$0.05 USDC / req）

import { Hono } from "hono";
import { paymentMiddleware } from "x402-hono";
import subsidiesData from "../data/subsidies.json";

type Bindings = {
  X402_NETWORK: string;
  X402_PRICE_SEARCH: string;
  X402_PRICE_RECOMMEND: string;
  X402_PRICE_DETAIL: string;
  X402_CURRENCY: string;
  X402_FACILITATOR: string;
  SERVER_ADDRESS: string;
};

type Subsidy = {
  id: string;
  name: string;
  category: string;
  administrator: string;
  url: string;
  max_amount_jpy: number;
  subsidy_rate: string;
  target: string;
  purposes: string[];
  regions: string[];
  deadline_typical: string;
  keywords: string[];
  fit_score_ai: number;
  notes: string;
};

const subsidies = subsidiesData.subsidies as Subsidy[];

const app = new Hono<{ Bindings: Bindings }>();

// ─────────────────────────────────────────────────────────────
// 無料エンドポイント
// ─────────────────────────────────────────────────────────────

app.get("/health", (c) =>
  c.json({
    ok: true,
    service: "jp-subsidy-mcp",
    version: "0.1.0",
    time: new Date().toISOString(),
  })
);

app.get("/info", (c) =>
  c.json({
    name: "jp-subsidy-mcp",
    version: "0.1.0",
    description_ja:
      "日本の補助金・助成金・IT導入補助金等を検索・レコメンドする MCP サーバー。x402 で有料ゲート済み。",
    subsidies_count: subsidies.length,
    last_updated: subsidiesData._meta.last_updated,
    source: subsidiesData._meta.source,
    disclaimer: subsidiesData._meta.disclaimer,
    pricing: {
      "/search": "$0.05 USDC per request",
      "/recommend": "$0.10 USDC per request",
      "/detail": "$0.02 USDC per request",
      "/mcp": "$0.05 USDC per request",
    },
    endpoints_free: ["/", "/health", "/info", "/free/list"],
    endpoints_paid: ["/search", "/recommend", "/detail", "/mcp"],
  })
);

app.get("/free/list", (c) => {
  const sample = subsidies[Math.floor(Math.random() * subsidies.length)];
  return c.json({
    sample: {
      id: sample.id,
      name: sample.name,
      category: sample.category,
      administrator: sample.administrator,
      regions: sample.regions,
    },
    total_count: subsidies.length,
    upgrade_message_ja:
      "全件検索には x402 決済（$0.05 USDC）が必要です。/search エンドポイントをご利用ください。",
  });
});

// ─────────────────────────────────────────────────────────────
// x402 payment middleware
// ─────────────────────────────────────────────────────────────

app.use("*", async (c, next) => {
  const path = c.req.path;
  if (
    path === "/" ||
    path === "/health" ||
    path === "/info" ||
    path === "/free/list"
  ) {
    return next();
  }

  const middleware = paymentMiddleware(
    c.env.SERVER_ADDRESS as `0x${string}`,
    {
      "/search": {
        price: `$${c.env.X402_PRICE_SEARCH}`,
        network: c.env.X402_NETWORK,
        config: { description: "Search Japanese subsidies by keyword" },
      },
      "/recommend": {
        price: `$${c.env.X402_PRICE_RECOMMEND}`,
        network: c.env.X402_NETWORK,
        config: { description: "Get personalized subsidy recommendations" },
      },
      "/detail": {
        price: `$${c.env.X402_PRICE_DETAIL}`,
        network: c.env.X402_NETWORK,
        config: { description: "Get detail of one subsidy" },
      },
      "/mcp": {
        price: `$${c.env.X402_PRICE_SEARCH}`,
        network: c.env.X402_NETWORK,
        config: { description: "MCP JSON-RPC endpoint" },
      },
    },
    { url: c.env.X402_FACILITATOR }
  );

  // @ts-expect-error - x402-hono middleware signature is Hono-compatible
  return middleware(c, next);
});

// ─────────────────────────────────────────────────────────────
// 有料エンドポイント
// ─────────────────────────────────────────────────────────────

app.post("/search", async (c) => {
  const body = await c.req.json().catch(() => ({} as any));
  const query: string = (body.query || "").toString().toLowerCase();
  const region: string | undefined = body.region;
  const minAmount: number = Number(body.min_amount) || 0;
  const minAiFit: number = Number(body.min_ai_fit) || 0;

  const results = subsidies
    .filter((s) => {
      if (query) {
        const hay = [
          s.name,
          s.category,
          s.target,
          s.notes,
          ...s.keywords,
          ...s.purposes,
        ]
          .join(" ")
          .toLowerCase();
        if (!hay.includes(query)) return false;
      }
      if (region && !s.regions.some((r) => r.includes(region))) return false;
      if (s.max_amount_jpy < minAmount) return false;
      if (s.fit_score_ai < minAiFit) return false;
      return true;
    })
    .sort((a, b) => {
      if (b.fit_score_ai !== a.fit_score_ai)
        return b.fit_score_ai - a.fit_score_ai;
      return b.max_amount_jpy - a.max_amount_jpy;
    });

  return c.json({
    query,
    count: results.length,
    results: results.slice(0, 20),
  });
});

app.post("/recommend", async (c) => {
  const body = await c.req.json().catch(() => ({} as any));
  const context: string = body.context || "";
  const industry: string = body.industry || "";
  const region: string = body.region || "";
  const stage: string = body.stage || "";

  const scored = subsidies.map((s) => {
    let score = s.fit_score_ai;
    if (region) {
      if (s.regions.some((r) => r.includes(region))) score += 20;
      if (s.regions.includes("全国")) score += 5;
    }
    if (context) {
      const ctx = context.toLowerCase();
      const matches = s.keywords.filter((k) =>
        ctx.includes(k.toLowerCase())
      ).length;
      score += matches * 8;
    }
    if (stage === "startup" && s.category === "スタートアップ") score += 15;
    if (stage === "startup" && s.category === "創業支援") score += 15;
    if (stage === "sme" && s.target.includes("中小")) score += 10;
    if (industry === "伝統産業" && s.category === "伝統産業") score += 25;
    if (industry === "IT" && s.category === "IT導入") score += 20;
    return { subsidy: s, score };
  });

  scored.sort((a, b) => b.score - a.score);

  return c.json({
    input: { context, industry, region, stage },
    recommendations: scored.slice(0, 5).map((x) => ({
      ...x.subsidy,
      recommendation_score: x.score,
      recommendation_reason: buildReason(x.subsidy, x.score),
    })),
  });
});

function buildReason(s: Subsidy, score: number): string {
  const reasons: string[] = [];
  if (score >= 100) reasons.push("高適合度：ほぼ要件に合致");
  if (s.fit_score_ai >= 85) reasons.push("AI 事業との親和性が極めて高い");
  if (s.max_amount_jpy >= 2000000) reasons.push("金額規模が大きい");
  if (s.regions.includes("富山県"))
    reasons.push("富山県内限定のため競合が少ない");
  if (s.category === "IT導入")
    reasons.push("IT 導入補助金は採択率が比較的高い");
  return reasons.join(" / ") || "標準的な候補";
}

app.post("/detail", async (c) => {
  const body = await c.req.json().catch(() => ({} as any));
  const id: string = body.id || "";
  const found = subsidies.find((s) => s.id === id);
  if (!found) {
    return c.json({ error: "not found", id }, 404);
  }
  return c.json(found);
});

// ─────────────────────────────────────────────────────────────
// MCP JSON-RPC エンドポイント
// ─────────────────────────────────────────────────────────────

app.post("/mcp", async (c) => {
  const body = await c.req.json().catch(() => ({} as any));
  const { method, params, id } = body;

  if (method === "initialize") {
    return c.json({
      jsonrpc: "2.0",
      id,
      result: {
        protocolVersion: "2024-11-05",
        capabilities: { tools: {} },
        serverInfo: { name: "jp-subsidy-mcp", version: "0.1.0" },
      },
    });
  }

  if (method === "tools/list") {
    return c.json({
      jsonrpc: "2.0",
      id,
      result: {
        tools: [
          {
            name: "search_subsidies",
            description:
              "日本の補助金・助成金を検索する。キーワード、地域、最低金額、AI適合度でフィルタ可能。",
            inputSchema: {
              type: "object",
              properties: {
                query: { type: "string" },
                region: { type: "string" },
                min_amount: { type: "number" },
                min_ai_fit: { type: "number" },
              },
            },
          },
          {
            name: "recommend_subsidies",
            description:
              "事業コンテキストから最適な補助金を最大 5 件レコメンドする。",
            inputSchema: {
              type: "object",
              properties: {
                context: { type: "string" },
                industry: { type: "string" },
                region: { type: "string" },
                stage: {
                  type: "string",
                  enum: ["startup", "sme", "large"],
                },
              },
            },
          },
          {
            name: "get_subsidy_detail",
            description: "1件の補助金の詳細を取得する。",
            inputSchema: {
              type: "object",
              properties: { id: { type: "string" } },
              required: ["id"],
            },
          },
        ],
      },
    });
  }

  if (method === "tools/call") {
    const toolName = params?.name;
    const args = params?.arguments || {};

    if (toolName === "search_subsidies") {
      const q = (args.query || "").toString().toLowerCase();
      const results = subsidies
        .filter((s) => {
          if (q) {
            const hay = [s.name, s.category, ...s.keywords]
              .join(" ")
              .toLowerCase();
            if (!hay.includes(q)) return false;
          }
          if (args.region && !s.regions.some((r) => r.includes(args.region)))
            return false;
          if ((args.min_amount || 0) > s.max_amount_jpy) return false;
          if ((args.min_ai_fit || 0) > s.fit_score_ai) return false;
          return true;
        })
        .slice(0, 10);
      return c.json({
        jsonrpc: "2.0",
        id,
        result: {
          content: [{ type: "text", text: JSON.stringify(results, null, 2) }],
        },
      });
    }

    if (toolName === "recommend_subsidies") {
      const region = args.region || "";
      const scored = subsidies.map((s) => {
        let score = s.fit_score_ai;
        if (region && s.regions.some((r) => r.includes(region))) score += 20;
        return { s, score };
      });
      scored.sort((a, b) => b.score - a.score);
      return c.json({
        jsonrpc: "2.0",
        id,
        result: {
          content: [
            {
              type: "text",
              text: JSON.stringify(
                scored.slice(0, 5).map((x) => x.s),
                null,
                2
              ),
            },
          ],
        },
      });
    }

    if (toolName === "get_subsidy_detail") {
      const found = subsidies.find((s) => s.id === args.id);
      if (!found) {
        return c.json({
          jsonrpc: "2.0",
          id,
          error: { code: -32602, message: `not found: ${args.id}` },
        });
      }
      return c.json({
        jsonrpc: "2.0",
        id,
        result: {
          content: [{ type: "text", text: JSON.stringify(found, null, 2) }],
        },
      });
    }

    return c.json({
      jsonrpc: "2.0",
      id,
      error: { code: -32601, message: `unknown tool: ${toolName}` },
    });
  }

  return c.json({
    jsonrpc: "2.0",
    id,
    error: { code: -32601, message: `unknown method: ${method}` },
  });
});

// ─────────────────────────────────────────────────────────────
// ランディングページ
// ─────────────────────────────────────────────────────────────

app.get("/", (c) => {
  const origin = new URL(c.req.url).origin;
  return c.html(`<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>jp-subsidy-mcp — 日本の補助金を AI で検索</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", sans-serif; max-width: 720px; margin: 40px auto; padding: 20px; color: #24292f; line-height: 1.7; }
  code { background: #f6f8fa; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }
  pre { background: #0d1117; color: #c9d1d9; padding: 16px; border-radius: 8px; overflow-x: auto; }
  h1 { border-bottom: 1px solid #e1e4e8; padding-bottom: 8px; }
  h2 { color: #0969da; margin-top: 32px; }
  a { color: #0969da; }
  .badge { display: inline-block; background: #1f883d; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; }
</style>
</head>
<body>
<h1>🗾 jp-subsidy-mcp</h1>
<p><span class="badge">x402 対応</span> 日本の補助金・助成金を検索する MCP サーバー。Claude / OpenAI / その他の AI エージェントから直接呼び出せます。${subsidies.length} 件の公開補助金情報を収録。</p>

<h2>料金</h2>
<ul>
  <li><code>/search</code> — $0.05 USDC / リクエスト</li>
  <li><code>/recommend</code> — $0.10 USDC / リクエスト</li>
  <li><code>/detail</code> — $0.02 USDC / リクエスト</li>
  <li>支払いは x402 protocol 経由で自動決済（Base / Solana、2 秒・手数料 ¥0）</li>
</ul>

<h2>無料で試す</h2>
<pre>curl ${origin}/info
curl ${origin}/free/list</pre>

<h2>Claude Desktop 設定例</h2>
<pre>{
  "mcpServers": {
    "jp-subsidy": { "url": "${origin}/mcp" }
  }
}</pre>

<p><small>このサービスは公開情報の要約です。正式な申請前に必ず各制度の公式サイトで最新情報を確認してください。</small></p>
<p><small>🤖 Built and maintained by an autonomous AI company based in Toyama, Japan.</small></p>
</body>
</html>`);
});

export default app;
