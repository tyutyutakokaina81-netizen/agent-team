/**
 * jp-business-docs-mcp — 日本のビジネス文書テンプレート MCP サーバー
 *
 * 法人設立・税務・請求書・契約書・届出・経理に関する
 * テンプレートと記入ガイドを提供する有料 API / MCP サーバー。
 *
 * Cloudflare Workers + Hono + x402 で稼働。
 */

import { Hono } from "hono";
import { cors } from "hono/cors";
import { paymentMiddleware } from "x402-hono";
import templatesData from "../data/templates.json";

// ─────────────────────────────────────────────
// 型定義
// ─────────────────────────────────────────────

interface TemplateSection {
  title: string;
  content: string;
}

interface Template {
  id: string;
  name: string;
  category: string;
  description: string;
  required_fields: string[];
  estimated_time_minutes: number;
  difficulty: "easy" | "medium" | "hard";
  related_subsidies: string[];
  template_outline: { sections: TemplateSection[] };
  keywords: string[];
  regions: string[];
}

interface Env {
  FACILITY_ADDRESS: string;
}

interface SearchRequest {
  query?: string;
  category?: string;
  difficulty?: string;
  max_results?: number;
}

interface GenerateRequest {
  template_id: string;
  field_values: Record<string, string>;
}

interface DetailRequest {
  template_id: string;
}

interface McpJsonRpcRequest {
  jsonrpc: "2.0";
  id: string | number;
  method: string;
  params?: Record<string, unknown>;
}

// ─────────────────────────────────────────────
// データ読み込み
// ─────────────────────────────────────────────

const templates: Template[] = templatesData as Template[];

// ─────────────────────────────────────────────
// ユーティリティ
// ─────────────────────────────────────────────

/** キーワードベースの簡易検索スコアリング */
function scoreTemplate(t: Template, query: string): number {
  const q = query.toLowerCase();
  const tokens = q.split(/[\s　,、]+/).filter(Boolean);
  let score = 0;
  for (const tok of tokens) {
    if (t.name.toLowerCase().includes(tok)) score += 10;
    if (t.category.toLowerCase().includes(tok)) score += 8;
    if (t.description.toLowerCase().includes(tok)) score += 5;
    if (t.keywords.some((k) => k.toLowerCase().includes(tok))) score += 7;
    if (t.required_fields.some((f) => f.toLowerCase().includes(tok))) score += 3;
  }
  return score;
}

/** テンプレートのフィールド値を埋めた文書を生成 */
function generateFilledDocument(
  template: Template,
  fieldValues: Record<string, string>
): string {
  const lines: string[] = [];
  lines.push(`${"=".repeat(60)}`);
  lines.push(`  ${template.name}`);
  lines.push(`${"=".repeat(60)}`);
  lines.push("");
  lines.push(`カテゴリ: ${template.category}`);
  lines.push(`難易度: ${template.difficulty}`);
  lines.push(`推定作成時間: ${template.estimated_time_minutes}分`);
  lines.push("");

  // 入力情報の一覧
  lines.push("【入力情報】");
  for (const field of template.required_fields) {
    const value = fieldValues[field] || "（未入力）";
    lines.push(`  ${field}: ${value}`);
  }
  lines.push("");

  // 各セクションの展開
  lines.push("【文書内容】");
  lines.push("");
  for (const section of template.template_outline.sections) {
    lines.push(`━━━ ${section.title} ━━━`);
    lines.push("");
    // セクション内容にフィールド値を反映
    let content = section.content;
    for (const [key, value] of Object.entries(fieldValues)) {
      content = content.replace(new RegExp(key, "g"), `${key}：${value}`);
    }
    lines.push(content);
    lines.push("");
  }

  // 注意事項
  lines.push("【注意事項】");
  lines.push(
    "・本テンプレートは一般的な書式であり、法的助言を構成するものではありません。"
  );
  lines.push("・重要な契約書・届出書は、税理士・弁護士・司法書士等の専門家にご確認ください。");
  lines.push("・法令改正により記載事項が変更される場合があります。最新の情報をご確認ください。");
  lines.push("");
  lines.push(`生成日時: ${new Date().toISOString()}`);

  return lines.join("\n");
}

/** 未入力フィールドのチェック */
function getMissingFields(
  template: Template,
  fieldValues: Record<string, string>
): string[] {
  return template.required_fields.filter(
    (f) => !fieldValues[f] || fieldValues[f].trim() === ""
  );
}

// ─────────────────────────────────────────────
// HTML ランディングページ
// ─────────────────────────────────────────────

function renderLandingPage(): string {
  const categories = [...new Set(templates.map((t) => t.category))];
  const categoryCounts = categories.map((c) => ({
    name: c,
    count: templates.filter((t) => t.category === c).length,
  }));

  return `<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>JP Business Docs MCP — 日本ビジネス文書テンプレート API</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Hiragino Sans", sans-serif;
           background: #0a0a0a; color: #e0e0e0; line-height: 1.7; }
    .hero { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            padding: 80px 20px; text-align: center; }
    .hero h1 { font-size: 2.5rem; color: #fff; margin-bottom: 12px; }
    .hero .sub { font-size: 1.1rem; color: #8ec8f0; margin-bottom: 30px; }
    .badge { display: inline-block; background: #e94560; color: #fff; padding: 6px 18px;
             border-radius: 20px; font-size: 0.85rem; font-weight: 700; }
    .container { max-width: 900px; margin: 0 auto; padding: 40px 20px; }
    h2 { color: #fff; font-size: 1.5rem; margin-bottom: 20px; border-left: 4px solid #e94560;
         padding-left: 12px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 16px; margin-bottom: 40px; }
    .card { background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 12px;
            padding: 20px; transition: border-color 0.2s; }
    .card:hover { border-color: #e94560; }
    .card h3 { color: #fff; font-size: 1rem; margin-bottom: 8px; }
    .card .count { color: #e94560; font-weight: 700; font-size: 1.5rem; }
    .card p { color: #999; font-size: 0.85rem; margin-top: 4px; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 40px; }
    th, td { padding: 12px 16px; text-align: left; border-bottom: 1px solid #2a2a4a; }
    th { color: #8ec8f0; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.5px; }
    td { color: #ccc; font-size: 0.9rem; }
    .price { color: #e94560; font-weight: 700; }
    code { background: #1a1a2e; padding: 2px 8px; border-radius: 4px; font-size: 0.85rem; color: #8ec8f0; }
    pre { background: #111; padding: 20px; border-radius: 8px; overflow-x: auto;
          font-size: 0.85rem; color: #8ec8f0; margin-bottom: 20px; }
    .free { color: #4caf50; font-weight: 700; }
    .footer { text-align: center; padding: 40px 20px; color: #666; font-size: 0.8rem;
              border-top: 1px solid #222; }
    .mcp-badge { background: #16213e; border: 1px solid #0f3460; padding: 16px;
                 border-radius: 8px; margin-bottom: 20px; }
    .mcp-badge code { color: #4caf50; }
  </style>
</head>
<body>
  <div class="hero">
    <h1>JP Business Docs MCP</h1>
    <p class="sub">日本のビジネス文書テンプレート・記入ガイド API</p>
    <span class="badge">${templates.length} テンプレート収録</span>
  </div>

  <div class="container">
    <h2>カテゴリ一覧</h2>
    <div class="grid">
      ${categoryCounts
        .map(
          (c) => `
      <div class="card">
        <div class="count">${c.count}</div>
        <h3>${c.name}</h3>
        <p>テンプレート数</p>
      </div>`
        )
        .join("")}
    </div>

    <h2>API エンドポイント</h2>
    <table>
      <tr><th>エンドポイント</th><th>説明</th><th>価格</th></tr>
      <tr><td><code>GET /</code></td><td>このページ</td><td class="free">無料</td></tr>
      <tr><td><code>GET /health</code></td><td>ヘルスチェック</td><td class="free">無料</td></tr>
      <tr><td><code>GET /info</code></td><td>API 情報・統計</td><td class="free">無料</td></tr>
      <tr><td><code>GET /free/template</code></td><td>ランダムテンプレート1件</td><td class="free">無料</td></tr>
      <tr><td><code>POST /search</code></td><td>テンプレート検索</td><td class="price">$0.03</td></tr>
      <tr><td><code>POST /generate</code></td><td>文書生成</td><td class="price">$0.15</td></tr>
      <tr><td><code>POST /detail</code></td><td>テンプレート詳細</td><td class="price">$0.02</td></tr>
      <tr><td><code>POST /mcp</code></td><td>MCP JSON-RPC</td><td class="price">$0.05</td></tr>
    </table>

    <h2>MCP 接続</h2>
    <div class="mcp-badge">
      <p>Claude Desktop / MCP クライアントから接続：</p>
      <pre>{
  "mcpServers": {
    "jp-business-docs": {
      "url": "https://jp-business-docs-mcp.YOUR_SUBDOMAIN.workers.dev/mcp",
      "transport": "http"
    }
  }
}</pre>
    </div>

    <h2>使用例</h2>
    <pre>// テンプレート検索
curl -X POST https://jp-business-docs-mcp.YOUR_SUBDOMAIN.workers.dev/search \\
  -H "Content-Type: application/json" \\
  -H "X-Payment: ..." \\
  -d '{"query": "請求書 インボイス", "max_results": 5}'

// 文書生成
curl -X POST https://jp-business-docs-mcp.YOUR_SUBDOMAIN.workers.dev/generate \\
  -H "Content-Type: application/json" \\
  -H "X-Payment: ..." \\
  -d '{
    "template_id": "doc-008",
    "field_values": {
      "発行者名": "株式会社サンプル",
      "登録番号": "T1234567890123",
      "請求先名": "株式会社クライアント",
      "品目": "Webサイト制作",
      "数量": "1",
      "単価": "500000",
      "税率": "10%"
    }
  }'</pre>

    <h2>収録テンプレート一覧</h2>
    <table>
      <tr><th>ID</th><th>テンプレート名</th><th>カテゴリ</th><th>難易度</th></tr>
      ${templates
        .map(
          (t) =>
            `<tr><td><code>${t.id}</code></td><td>${t.name}</td><td>${t.category}</td><td>${t.difficulty}</td></tr>`
        )
        .join("")}
    </table>
  </div>

  <div class="footer">
    <p>JP Business Docs MCP Server &copy; 2026 — Powered by Cloudflare Workers + x402</p>
    <p>法人設立・税務・請求書・契約書・届出・経理テンプレート</p>
  </div>
</body>
</html>`;
}

// ─────────────────────────────────────────────
// MCP JSON-RPC ハンドラ
// ─────────────────────────────────────────────

const MCP_TOOLS = [
  {
    name: "search_templates",
    description:
      "日本のビジネス文書テンプレートを検索します。キーワード・カテゴリ・難易度で絞り込み可能。カテゴリ: 法人設立, 税務, 請求書, 契約書, 届出, 経理",
    inputSchema: {
      type: "object" as const,
      properties: {
        query: {
          type: "string",
          description: "検索キーワード（例: 請求書 インボイス）",
        },
        category: {
          type: "string",
          description:
            "カテゴリで絞り込み（法人設立/税務/請求書/契約書/届出/経理）",
        },
        difficulty: {
          type: "string",
          description: "難易度で絞り込み（easy/medium/hard）",
        },
        max_results: {
          type: "number",
          description: "最大件数（デフォルト10）",
        },
      },
    },
  },
  {
    name: "generate_document",
    description:
      "テンプレートIDとフィールド値を指定し、記入済みのビジネス文書を生成します。必須フィールドはテンプレート詳細で確認してください。",
    inputSchema: {
      type: "object" as const,
      properties: {
        template_id: {
          type: "string",
          description: "テンプレートID（例: doc-008）",
        },
        field_values: {
          type: "object",
          description:
            "フィールド名と値のペア（例: {\"発行者名\": \"株式会社サンプル\", ...}）",
        },
      },
      required: ["template_id", "field_values"],
    },
  },
  {
    name: "get_template_detail",
    description:
      "テンプレートIDを指定して詳細情報（必須フィールド・テンプレート構成・関連補助金等）を取得します。",
    inputSchema: {
      type: "object" as const,
      properties: {
        template_id: {
          type: "string",
          description: "テンプレートID（例: doc-001）",
        },
      },
      required: ["template_id"],
    },
  },
];

function handleMcpRequest(request: McpJsonRpcRequest): object {
  const { method, id, params } = request;

  // initialize
  if (method === "initialize") {
    return {
      jsonrpc: "2.0",
      id,
      result: {
        protocolVersion: "2024-11-05",
        capabilities: { tools: {} },
        serverInfo: {
          name: "jp-business-docs-mcp",
          version: "1.0.0",
          description:
            "日本のビジネス文書テンプレート・記入ガイドを提供する MCP サーバー",
        },
      },
    };
  }

  // tools/list
  if (method === "tools/list") {
    return {
      jsonrpc: "2.0",
      id,
      result: { tools: MCP_TOOLS },
    };
  }

  // tools/call
  if (method === "tools/call") {
    const toolName = (params as { name: string })?.name;
    const args = (params as { arguments?: Record<string, unknown> })
      ?.arguments || {};

    if (toolName === "search_templates") {
      const results = executeSearch(args as unknown as SearchRequest);
      return {
        jsonrpc: "2.0",
        id,
        result: {
          content: [{ type: "text", text: JSON.stringify(results, null, 2) }],
        },
      };
    }

    if (toolName === "generate_document") {
      const result = executeGenerate(args as unknown as GenerateRequest);
      return {
        jsonrpc: "2.0",
        id,
        result: {
          content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
        },
      };
    }

    if (toolName === "get_template_detail") {
      const result = executeDetail(args as unknown as DetailRequest);
      return {
        jsonrpc: "2.0",
        id,
        result: {
          content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
        },
      };
    }

    return {
      jsonrpc: "2.0",
      id,
      error: { code: -32601, message: `不明なツール: ${toolName}` },
    };
  }

  // notifications (no response needed but return empty for safety)
  if (method === "notifications/initialized") {
    return { jsonrpc: "2.0", id, result: {} };
  }

  return {
    jsonrpc: "2.0",
    id,
    error: { code: -32601, message: `不明なメソッド: ${method}` },
  };
}

// ─────────────────────────────────────────────
// ビジネスロジック
// ─────────────────────────────────────────────

function executeSearch(params: SearchRequest) {
  const { query, category, difficulty, max_results = 10 } = params;

  let results = [...templates];

  // カテゴリフィルタ
  if (category) {
    results = results.filter((t) => t.category === category);
  }

  // 難易度フィルタ
  if (difficulty) {
    results = results.filter((t) => t.difficulty === difficulty);
  }

  // キーワード検索（スコア順）
  if (query && query.trim()) {
    results = results
      .map((t) => ({ template: t, score: scoreTemplate(t, query) }))
      .filter((r) => r.score > 0)
      .sort((a, b) => b.score - a.score)
      .map((r) => r.template);
  }

  // 最大件数
  results = results.slice(0, Math.min(max_results, 24));

  return {
    total: results.length,
    templates: results.map((t) => ({
      id: t.id,
      name: t.name,
      category: t.category,
      difficulty: t.difficulty,
      description: t.description,
      estimated_time_minutes: t.estimated_time_minutes,
      required_fields_count: t.required_fields.length,
      keywords: t.keywords,
    })),
  };
}

function executeGenerate(params: GenerateRequest) {
  const { template_id, field_values } = params;

  const template = templates.find((t) => t.id === template_id);
  if (!template) {
    return {
      error: true,
      message: `テンプレートが見つかりません: ${template_id}`,
      available_ids: templates.map((t) => t.id),
    };
  }

  const missingFields = getMissingFields(template, field_values);

  const document = generateFilledDocument(template, field_values);

  return {
    template_id: template.id,
    template_name: template.name,
    category: template.category,
    filled_fields: Object.keys(field_values).length,
    total_required_fields: template.required_fields.length,
    missing_fields: missingFields,
    warnings:
      missingFields.length > 0
        ? `${missingFields.length}件の未入力フィールドがあります: ${missingFields.join(", ")}`
        : null,
    document,
    related_subsidies: template.related_subsidies,
    generated_at: new Date().toISOString(),
  };
}

function executeDetail(params: DetailRequest) {
  const { template_id } = params;

  const template = templates.find((t) => t.id === template_id);
  if (!template) {
    return {
      error: true,
      message: `テンプレートが見つかりません: ${template_id}`,
      available_ids: templates.map((t) => t.id),
    };
  }

  return {
    ...template,
    sections_count: template.template_outline.sections.length,
    cross_references: {
      related_subsidies: template.related_subsidies,
      subsidy_server: "jp-subsidy-mcp",
      note: "related_subsidies のIDは jp-subsidy-mcp サーバーで詳細を取得できます",
    },
  };
}

// ─────────────────────────────────────────────
// Hono アプリケーション
// ─────────────────────────────────────────────

const app = new Hono<{ Bindings: Env }>();

// CORS
app.use("*", cors());

// ─── 無料エンドポイント ─────────────────────

// ランディングページ
app.get("/", (c) => {
  return c.html(renderLandingPage());
});

// ヘルスチェック
app.get("/health", (c) => {
  return c.json({
    status: "ok",
    service: "jp-business-docs-mcp",
    version: "1.0.0",
    templates_count: templates.length,
    timestamp: new Date().toISOString(),
  });
});

// API 情報
app.get("/info", (c) => {
  const categories = [...new Set(templates.map((t) => t.category))];
  const difficultyStats = {
    easy: templates.filter((t) => t.difficulty === "easy").length,
    medium: templates.filter((t) => t.difficulty === "medium").length,
    hard: templates.filter((t) => t.difficulty === "hard").length,
  };

  return c.json({
    name: "jp-business-docs-mcp",
    version: "1.0.0",
    description:
      "日本のビジネス文書テンプレート・記入ガイドを提供する API / MCP サーバー",
    templates_count: templates.length,
    categories: categories.map((cat) => ({
      name: cat,
      count: templates.filter((t) => t.category === cat).length,
    })),
    difficulty_distribution: difficultyStats,
    pricing: {
      search: "$0.03",
      generate: "$0.15",
      detail: "$0.02",
      mcp: "$0.05",
    },
    free_endpoints: ["/", "/health", "/info", "/free/template"],
    paid_endpoints: ["/search", "/generate", "/detail", "/mcp"],
    cross_references: ["jp-subsidy-mcp", "toyama-local-mcp"],
  });
});

// 無料サンプル — ランダム1件
app.get("/free/template", (c) => {
  const idx = Math.floor(Math.random() * templates.length);
  const t = templates[idx];
  return c.json({
    sample: true,
    note: "これは無料サンプルです。全テンプレートへのアクセスには有料エンドポイントをご利用ください。",
    template: {
      id: t.id,
      name: t.name,
      category: t.category,
      difficulty: t.difficulty,
      description: t.description,
      required_fields: t.required_fields,
      estimated_time_minutes: t.estimated_time_minutes,
      keywords: t.keywords,
    },
  });
});

// ─── 有料エンドポイント ─────────────────────

// テンプレート検索 — $0.03
app.post(
  "/search",
  paymentMiddleware(app, {
    price: "$0.03",
    network: "base-sepolia",
    config: {
      description: "日本ビジネス文書テンプレート検索",
    },
  }),
  async (c) => {
    const body = await c.req.json<SearchRequest>();
    const results = executeSearch(body);
    return c.json(results);
  }
);

// 文書生成 — $0.15
app.post(
  "/generate",
  paymentMiddleware(app, {
    price: "$0.15",
    network: "base-sepolia",
    config: {
      description: "ビジネス文書テンプレート生成",
    },
  }),
  async (c) => {
    const body = await c.req.json<GenerateRequest>();

    if (!body.template_id) {
      return c.json({ error: "template_id は必須です" }, 400);
    }
    if (!body.field_values || typeof body.field_values !== "object") {
      return c.json({ error: "field_values（オブジェクト）は必須です" }, 400);
    }

    const result = executeGenerate(body);
    return c.json(result);
  }
);

// テンプレート詳細 — $0.02
app.post(
  "/detail",
  paymentMiddleware(app, {
    price: "$0.02",
    network: "base-sepolia",
    config: {
      description: "ビジネス文書テンプレート詳細取得",
    },
  }),
  async (c) => {
    const body = await c.req.json<DetailRequest>();

    if (!body.template_id) {
      return c.json({ error: "template_id は必須です" }, 400);
    }

    const result = executeDetail(body);
    return c.json(result);
  }
);

// MCP JSON-RPC エンドポイント — $0.05
app.post(
  "/mcp",
  paymentMiddleware(app, {
    price: "$0.05",
    network: "base-sepolia",
    config: {
      description: "MCP JSON-RPC（ビジネス文書テンプレート）",
    },
  }),
  async (c) => {
    const body = await c.req.json<McpJsonRpcRequest>();

    if (!body.jsonrpc || body.jsonrpc !== "2.0") {
      return c.json({ error: "JSON-RPC 2.0 形式で送信してください" }, 400);
    }

    const result = handleMcpRequest(body);
    return c.json(result);
  }
);

// ─── 404 ─────────────────────────────────────

app.notFound((c) => {
  return c.json(
    {
      error: "Not Found",
      available_endpoints: {
        free: ["GET /", "GET /health", "GET /info", "GET /free/template"],
        paid: [
          "POST /search ($0.03)",
          "POST /generate ($0.15)",
          "POST /detail ($0.02)",
          "POST /mcp ($0.05)",
        ],
      },
    },
    404
  );
});

export default app;
