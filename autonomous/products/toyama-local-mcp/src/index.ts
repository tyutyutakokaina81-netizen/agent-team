// toyama-local-mcp / src/index.ts
//
// 富山県の観光・グルメ・伝統工芸・祭り情報を検索する MCP サーバー。
// x402 protocol で有料ゲート、無料 demo エンドポイントあり。
//
// エンドポイント:
//   GET  /           HTML ランディング
//   GET  /health     ヘルスチェック
//   GET  /info       メタ情報
//   GET  /free/spot  ランダム1件（広告）
//   POST /search     $0.03 USDC  カテゴリ/エリア/季節検索
//   POST /recommend  $0.08 USDC  行動コンテキストからレコメンド
//   POST /detail     $0.02 USDC  1件の詳細
//   POST /mcp        $0.03 USDC  MCP JSON-RPC

import { Hono } from "hono";
import { paymentMiddleware } from "x402-hono";
import spotsData from "../data/spots.json";

type Bindings = {
  X402_NETWORK: string;
  X402_PRICE_SEARCH: string;
  X402_PRICE_RECOMMEND: string;
  X402_PRICE_DETAIL: string;
  X402_FACILITATOR: string;
  SERVER_ADDRESS: string;
};

type Spot = {
  id: string;
  name: string;
  category: string;
  area: string;
  season_best: string[];
  description: string;
  keywords: string[];
  access: string;
  official_url: string;
  budget_jpy_per_person: number;
  duration_hours: number;
  kid_friendly: boolean;
  ai_recommend_context: string[];
};

const spots = spotsData.spots as Spot[];

const app = new Hono<{ Bindings: Bindings }>();

// ─────────────────────────────────────────────────────────────
// 無料エンドポイント
// ─────────────────────────────────────────────────────────────

app.get("/health", (c) =>
  c.json({
    ok: true,
    service: "toyama-local-mcp",
    version: "0.1.0",
    time: new Date().toISOString(),
  })
);

app.get("/info", (c) =>
  c.json({
    name: "toyama-local-mcp",
    version: "0.1.0",
    description_ja:
      "富山県の観光・グルメ・伝統工芸・祭り情報を検索する MCP サーバー。",
    description_en:
      "MCP server for Toyama Prefecture local information: tourism, food, crafts, festivals.",
    spots_count: spots.length,
    categories: [...new Set(spots.map((s) => s.category))],
    areas: [...new Set(spots.map((s) => s.area))],
    last_updated: spotsData._meta.last_updated,
    pricing: {
      "/search": "$0.03 USDC",
      "/recommend": "$0.08 USDC",
      "/detail": "$0.02 USDC",
      "/mcp": "$0.03 USDC",
    },
  })
);

app.get("/free/spot", (c) => {
  const sample = spots[Math.floor(Math.random() * spots.length)];
  return c.json({
    sample: {
      id: sample.id,
      name: sample.name,
      category: sample.category,
      area: sample.area,
    },
    total_count: spots.length,
    upgrade_message_ja:
      "詳細検索・レコメンドには x402 決済（$0.02-0.08 USDC）が必要です。",
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
    path === "/free/spot"
  ) {
    return next();
  }

  const middleware = paymentMiddleware(
    c.env.SERVER_ADDRESS as `0x${string}`,
    {
      "/search": {
        price: `$${c.env.X402_PRICE_SEARCH}`,
        network: c.env.X402_NETWORK,
        config: { description: "Search Toyama spots" },
      },
      "/recommend": {
        price: `$${c.env.X402_PRICE_RECOMMEND}`,
        network: c.env.X402_NETWORK,
        config: { description: "Get Toyama spot recommendations" },
      },
      "/detail": {
        price: `$${c.env.X402_PRICE_DETAIL}`,
        network: c.env.X402_NETWORK,
        config: { description: "Get Toyama spot detail" },
      },
      "/mcp": {
        price: `$${c.env.X402_PRICE_SEARCH}`,
        network: c.env.X402_NETWORK,
        config: { description: "MCP JSON-RPC endpoint" },
      },
    },
    { url: c.env.X402_FACILITATOR }
  );

  // @ts-expect-error - middleware signature compatible
  return middleware(c, next);
});

// ─────────────────────────────────────────────────────────────
// 有料エンドポイント
// ─────────────────────────────────────────────────────────────

app.post("/search", async (c) => {
  const body = await c.req.json().catch(() => ({} as any));
  const query: string = (body.query || "").toString().toLowerCase();
  const category: string | undefined = body.category;
  const area: string | undefined = body.area;
  const season: string | undefined = body.season;
  const kidFriendly: boolean | undefined = body.kid_friendly;
  const maxBudget: number | undefined = body.max_budget_jpy;

  const results = spots.filter((s) => {
    if (query) {
      const hay = [s.name, s.description, ...s.keywords].join(" ").toLowerCase();
      if (!hay.includes(query)) return false;
    }
    if (category && s.category !== category) return false;
    if (area && !s.area.includes(area)) return false;
    if (season && !s.season_best.includes(season) && !s.season_best.includes("通年")) return false;
    if (kidFriendly === true && !s.kid_friendly) return false;
    if (maxBudget && s.budget_jpy_per_person > maxBudget) return false;
    return true;
  });

  return c.json({
    query,
    filters: { category, area, season, kidFriendly, maxBudget },
    count: results.length,
    results,
  });
});

app.post("/recommend", async (c) => {
  const body = await c.req.json().catch(() => ({} as any));
  const context: string = (body.context || "").toString().toLowerCase();
  const days: number = Number(body.days) || 1;
  const budget: number = Number(body.total_budget_jpy) || 30000;
  const season: string = body.season || "通年";
  const withKids: boolean = Boolean(body.with_kids);

  const scored = spots.map((s) => {
    let score = 0;
    // コンテキストマッチ
    if (context) {
      const hay = [
        s.name,
        s.description,
        ...s.keywords,
        ...s.ai_recommend_context,
      ]
        .join(" ")
        .toLowerCase();
      const words = context.split(/\s+/).filter(Boolean);
      for (const w of words) {
        if (hay.includes(w)) score += 10;
      }
    }
    // 季節
    if (s.season_best.includes(season) || s.season_best.includes("通年")) {
      score += 15;
    }
    // 家族
    if (withKids && s.kid_friendly) score += 10;
    if (withKids && !s.kid_friendly) score -= 5;
    // 予算適合
    if (s.budget_jpy_per_person <= budget * 0.3) score += 5;
    return { spot: s, score };
  });

  scored.sort((a, b) => b.score - a.score);

  // days に応じて適切な件数
  const count = Math.min(days * 4, 10);

  return c.json({
    input: { context, days, budget, season, withKids },
    itinerary: scored.slice(0, count).map((x) => ({
      ...x.spot,
      recommend_score: x.score,
    })),
  });
});

app.post("/detail", async (c) => {
  const body = await c.req.json().catch(() => ({} as any));
  const id: string = body.id || "";
  const found = spots.find((s) => s.id === id);
  if (!found) {
    return c.json({ error: "not found", id }, 404);
  }
  return c.json(found);
});

// ─────────────────────────────────────────────────────────────
// MCP JSON-RPC
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
        serverInfo: { name: "toyama-local-mcp", version: "0.1.0" },
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
            name: "search_toyama_spots",
            description:
              "富山県の観光スポット・グルメ・祭り・伝統工芸を検索する",
            inputSchema: {
              type: "object",
              properties: {
                query: { type: "string" },
                category: { type: "string" },
                area: { type: "string" },
                season: { type: "string", enum: ["春", "夏", "秋", "冬", "通年"] },
                kid_friendly: { type: "boolean" },
                max_budget_jpy: { type: "number" },
              },
            },
          },
          {
            name: "recommend_toyama_itinerary",
            description:
              "行動コンテキストから富山旅行の行程をレコメンドする",
            inputSchema: {
              type: "object",
              properties: {
                context: { type: "string" },
                days: { type: "number" },
                total_budget_jpy: { type: "number" },
                season: { type: "string" },
                with_kids: { type: "boolean" },
              },
            },
          },
          {
            name: "get_toyama_spot_detail",
            description: "1 件の富山スポットの詳細を取得する",
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

    if (toolName === "search_toyama_spots") {
      const q = (args.query || "").toString().toLowerCase();
      const results = spots
        .filter((s) => {
          if (q) {
            const hay = [s.name, s.description, ...s.keywords].join(" ").toLowerCase();
            if (!hay.includes(q)) return false;
          }
          if (args.category && s.category !== args.category) return false;
          if (args.area && !s.area.includes(args.area)) return false;
          if (args.season && !s.season_best.includes(args.season) && !s.season_best.includes("通年")) return false;
          if (args.kid_friendly === true && !s.kid_friendly) return false;
          if (args.max_budget_jpy && s.budget_jpy_per_person > args.max_budget_jpy) return false;
          return true;
        })
        .slice(0, 10);
      return c.json({
        jsonrpc: "2.0",
        id,
        result: { content: [{ type: "text", text: JSON.stringify(results, null, 2) }] },
      });
    }

    if (toolName === "recommend_toyama_itinerary") {
      const ctx = (args.context || "").toString().toLowerCase();
      const season = args.season || "通年";
      const scored = spots.map((s) => {
        let score = 0;
        const hay = [s.name, ...s.keywords, ...s.ai_recommend_context].join(" ").toLowerCase();
        for (const w of ctx.split(/\s+/).filter(Boolean)) {
          if (hay.includes(w)) score += 10;
        }
        if (s.season_best.includes(season) || s.season_best.includes("通年")) score += 15;
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
                scored.slice(0, (args.days || 1) * 4).map((x) => x.s),
                null,
                2
              ),
            },
          ],
        },
      });
    }

    if (toolName === "get_toyama_spot_detail") {
      const found = spots.find((s) => s.id === args.id);
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
        result: { content: [{ type: "text", text: JSON.stringify(found, null, 2) }] },
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
// ランディング
// ─────────────────────────────────────────────────────────────

app.get("/", (c) => {
  const origin = new URL(c.req.url).origin;
  return c.html(`<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>toyama-local-mcp</title>
<style>
  body { font-family: -apple-system, sans-serif; max-width: 720px; margin: 40px auto; padding: 20px; color: #24292f; line-height: 1.7; }
  code { background: #f6f8fa; padding: 2px 6px; border-radius: 4px; }
  pre { background: #0d1117; color: #c9d1d9; padding: 16px; border-radius: 8px; overflow-x: auto; }
  h1 { border-bottom: 1px solid #e1e4e8; padding-bottom: 8px; }
  h2 { color: #0969da; margin-top: 32px; }
  .badge { display: inline-block; background: #1f883d; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; }
</style></head><body>
<h1>🗾 toyama-local-mcp</h1>
<p><span class="badge">x402 対応</span> 富山県の観光・グルメ・伝統工芸・祭り情報を AI エージェントに提供する MCP サーバー。${spots.length} 件の公開情報を収録。</p>

<h2>料金（USDC）</h2>
<ul>
  <li><code>/search</code> — $0.03 per request</li>
  <li><code>/recommend</code> — $0.08 per request</li>
  <li><code>/detail</code> — $0.02 per request</li>
</ul>

<h2>無料で試す</h2>
<pre>curl ${origin}/info
curl ${origin}/free/spot</pre>

<h2>Claude Desktop 設定</h2>
<pre>{
  "mcpServers": {
    "toyama-local": { "url": "${origin}/mcp" }
  }
}</pre>

<p><small>Built with 🤖 by an autonomous AI company in Toyama, Japan.</small></p>
</body></html>`);
});

export default app;
