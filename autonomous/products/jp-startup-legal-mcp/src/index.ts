// jp-startup-legal-mcp / src/index.ts
//
// Cloudflare Workers で動く、日本のスタートアップ・フリーランス向け法務FAQ MCPサーバー。
// x402 payment middleware で有料アクセスを USDC で自動決済する。
//
// ⚠️ 免責事項: この情報は一般的な法務知識の提供を目的としており、法的助言ではありません。
// 具体的な法的問題については、必ず弁護士・司法書士・税理士等の専門家にご相談ください。
//
// 無料エンドポイント（広告・獲得目的）:
//   GET  /           - HTML ランディングページ
//   GET  /health     - ヘルスチェック
//   GET  /info       - サーバーメタ情報
//   GET  /free/faq   - FAQ1件だけランダム表示
//
// 有料エンドポイント（x402 支払い必須）:
//   POST /search     - キーワード検索（$0.05 USDC / req）
//   POST /detail     - 1件のFAQ詳細取得（$0.03 USDC / req）
//   POST /checklist  - 手続きチェックリスト取得（$0.10 USDC / req）
//   POST /mcp        - MCP JSON-RPC エンドポイント（$0.05 USDC / req）

import { Hono } from "hono";
import { paymentMiddleware } from "x402-hono";
import faqData from "../data/legal_faq.json";
import procedureData from "../data/procedures.json";

// ─────────────────────────────────────────────────────────────
// 型定義
// ─────────────────────────────────────────────────────────────

type Bindings = {
  X402_NETWORK: string;
  X402_PRICE_SEARCH: string;
  X402_PRICE_DETAIL: string;
  X402_PRICE_CHECKLIST: string;
  X402_CURRENCY: string;
  X402_FACILITATOR: string;
  SERVER_ADDRESS: string;
};

type FaqEntry = {
  id: string;
  question: string;
  answer: string;
  category: string;
  target: string;
  difficulty: string;
  related_procedures: string[];
  keywords: string[];
  disclaimer: string;
};

type Procedure = {
  id: string;
  name: string;
  category: string;
  required_documents: string[];
  estimated_days: number;
  cost_jpy: number;
  where_to_submit: string;
  online_available: boolean;
  steps: string[];
  tips: string;
  common_mistakes: string[];
};

// ─────────────────────────────────────────────────────────────
// データ読み込み
// ─────────────────────────────────────────────────────────────

const faqs = faqData.faqs as FaqEntry[];
const procedures = procedureData.procedures as Procedure[];

const GLOBAL_DISCLAIMER =
  "この情報は一般的な法務知識の提供を目的としており、法的助言ではありません。具体的な法的問題については、必ず弁護士・司法書士・税理士等の専門家にご相談ください。";

// ─────────────────────────────────────────────────────────────
// アプリ初期化
// ─────────────────────────────────────────────────────────────

const app = new Hono<{ Bindings: Bindings }>();

// ─────────────────────────────────────────────────────────────
// 無料エンドポイント
// ─────────────────────────────────────────────────────────────

app.get("/health", (c) =>
  c.json({
    ok: true,
    service: "jp-startup-legal-mcp",
    version: "0.1.0",
    time: new Date().toISOString(),
  })
);

app.get("/info", (c) =>
  c.json({
    name: "jp-startup-legal-mcp",
    version: "0.1.0",
    description_ja:
      "日本のスタートアップ・フリーランス向け法務FAQ・手続きガイドを提供する MCP サーバー。x402 で有料ゲート済み。",
    faq_count: faqs.length,
    procedure_count: procedures.length,
    categories: {
      faq: [...new Set(faqs.map((f) => f.category))],
      procedures: [...new Set(procedures.map((p) => p.category))],
    },
    last_updated: faqData._meta.last_updated,
    source: faqData._meta.source,
    disclaimer: GLOBAL_DISCLAIMER,
    pricing: {
      "/search": "$0.05 USDC per request",
      "/detail": "$0.03 USDC per request",
      "/checklist": "$0.10 USDC per request",
      "/mcp": "$0.05 USDC per request",
    },
    endpoints_free: ["/", "/health", "/info", "/free/faq"],
    endpoints_paid: ["/search", "/detail", "/checklist", "/mcp"],
  })
);

app.get("/free/faq", (c) => {
  const sample = faqs[Math.floor(Math.random() * faqs.length)];
  return c.json({
    sample: {
      id: sample.id,
      question: sample.question,
      category: sample.category,
      target: sample.target,
      difficulty: sample.difficulty,
    },
    total_faq_count: faqs.length,
    total_procedure_count: procedures.length,
    disclaimer: GLOBAL_DISCLAIMER,
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
    path === "/free/faq"
  ) {
    return next();
  }

  const middleware = paymentMiddleware(
    c.env.SERVER_ADDRESS as `0x${string}`,
    {
      "/search": {
        price: `$${c.env.X402_PRICE_SEARCH}`,
        network: c.env.X402_NETWORK,
        config: { description: "Search Japanese startup/freelance legal FAQs" },
      },
      "/detail": {
        price: `$${c.env.X402_PRICE_DETAIL}`,
        network: c.env.X402_NETWORK,
        config: { description: "Get detailed legal FAQ entry" },
      },
      "/checklist": {
        price: `$${c.env.X402_PRICE_CHECKLIST}`,
        network: c.env.X402_NETWORK,
        config: {
          description:
            "Get full procedure checklist with steps and documents",
        },
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
// 検索ヘルパー関数
// ─────────────────────────────────────────────────────────────

function searchFaqs(options: {
  query?: string;
  category?: string;
  target?: string;
  difficulty?: string;
}): FaqEntry[] {
  const { query, category, target, difficulty } = options;
  const q = (query || "").toLowerCase();

  return faqs
    .filter((f) => {
      // キーワード検索
      if (q) {
        const hay = [
          f.question,
          f.answer,
          f.category,
          f.target,
          ...f.keywords,
        ]
          .join(" ")
          .toLowerCase();
        if (!hay.includes(q)) return false;
      }
      // カテゴリフィルタ
      if (category && f.category !== category) return false;
      // ターゲットフィルタ
      if (target && f.target !== target && f.target !== "all") return false;
      // 難易度フィルタ
      if (difficulty && f.difficulty !== difficulty) return false;
      return true;
    })
    .sort((a, b) => {
      // クエリとの関連度でソート
      if (!q) return 0;
      const aScore = computeRelevance(a, q);
      const bScore = computeRelevance(b, q);
      return bScore - aScore;
    });
}

function computeRelevance(faq: FaqEntry, query: string): number {
  let score = 0;
  const q = query.toLowerCase();

  // 質問文にクエリが含まれる場合は高スコア
  if (faq.question.toLowerCase().includes(q)) score += 30;

  // カテゴリにクエリが含まれる場合
  if (faq.category.toLowerCase().includes(q)) score += 20;

  // キーワードにクエリが含まれる場合
  const keywordMatches = faq.keywords.filter((k) =>
    k.toLowerCase().includes(q)
  ).length;
  score += keywordMatches * 15;

  // 回答にクエリが含まれる場合
  if (faq.answer.toLowerCase().includes(q)) score += 10;

  return score;
}

function searchProcedures(options: {
  query?: string;
  category?: string;
  online_only?: boolean;
}): Procedure[] {
  const { query, category, online_only } = options;
  const q = (query || "").toLowerCase();

  return procedures.filter((p) => {
    if (q) {
      const hay = [
        p.name,
        p.category,
        p.tips,
        ...p.steps,
        ...p.required_documents,
        ...p.common_mistakes,
      ]
        .join(" ")
        .toLowerCase();
      if (!hay.includes(q)) return false;
    }
    if (category && p.category !== category) return false;
    if (online_only && !p.online_available) return false;
    return true;
  });
}

function buildChecklistMarkdown(proc: Procedure): string {
  const lines: string[] = [];
  lines.push(`# ${proc.name}`);
  lines.push(`カテゴリ: ${proc.category}`);
  lines.push(`推定所要日数: ${proc.estimated_days}日`);
  lines.push(
    `費用: ${proc.cost_jpy > 0 ? `${proc.cost_jpy.toLocaleString()}円` : "無料"}`
  );
  lines.push(`提出先: ${proc.where_to_submit}`);
  lines.push(
    `オンライン申請: ${proc.online_available ? "可能" : "不可（窓口または郵送）"}`
  );
  lines.push("");
  lines.push("## 必要書類チェックリスト");
  proc.required_documents.forEach((doc, i) => {
    lines.push(`- [ ] ${i + 1}. ${doc}`);
  });
  lines.push("");
  lines.push("## 手続きステップ");
  proc.steps.forEach((step, i) => {
    lines.push(`${i + 1}. ${step}`);
  });
  lines.push("");
  lines.push("## ヒント");
  lines.push(proc.tips);
  lines.push("");
  lines.push("## よくあるミス");
  proc.common_mistakes.forEach((mistake) => {
    lines.push(`- ${mistake}`);
  });
  lines.push("");
  lines.push("---");
  lines.push(`${GLOBAL_DISCLAIMER}`);
  return lines.join("\n");
}

// ─────────────────────────────────────────────────────────────
// 有料エンドポイント
// ─────────────────────────────────────────────────────────────

app.post("/search", async (c) => {
  const body = await c.req.json().catch(() => ({} as any));
  const query: string = (body.query || "").toString();
  const category: string | undefined = body.category;
  const target: string | undefined = body.target;
  const difficulty: string | undefined = body.difficulty;
  const include_procedures: boolean = body.include_procedures !== false;

  const faqResults = searchFaqs({ query, category, target, difficulty });

  let procedureResults: Procedure[] = [];
  if (include_procedures) {
    procedureResults = searchProcedures({ query, category });
  }

  return c.json({
    query,
    filters: { category, target, difficulty },
    faq_count: faqResults.length,
    procedure_count: procedureResults.length,
    faqs: faqResults.slice(0, 20).map((f) => ({
      id: f.id,
      question: f.question,
      category: f.category,
      target: f.target,
      difficulty: f.difficulty,
      keywords: f.keywords,
      related_procedures: f.related_procedures,
    })),
    procedures: procedureResults.slice(0, 10).map((p) => ({
      id: p.id,
      name: p.name,
      category: p.category,
      estimated_days: p.estimated_days,
      cost_jpy: p.cost_jpy,
      online_available: p.online_available,
    })),
    disclaimer: GLOBAL_DISCLAIMER,
  });
});

app.post("/detail", async (c) => {
  const body = await c.req.json().catch(() => ({} as any));
  const id: string = body.id || "";

  // FAQ の検索
  const foundFaq = faqs.find((f) => f.id === id);
  if (foundFaq) {
    // 関連手続きの概要を付与
    const relatedProcedures = foundFaq.related_procedures
      .map((procId) => procedures.find((p) => p.id === procId))
      .filter(Boolean)
      .map((p) => ({
        id: p!.id,
        name: p!.name,
        category: p!.category,
        estimated_days: p!.estimated_days,
        cost_jpy: p!.cost_jpy,
      }));

    return c.json({
      type: "faq",
      data: foundFaq,
      related_procedures: relatedProcedures,
      disclaimer: GLOBAL_DISCLAIMER,
    });
  }

  // 手続きの検索
  const foundProc = procedures.find((p) => p.id === id);
  if (foundProc) {
    // この手続きを参照しているFAQを検索
    const relatedFaqs = faqs
      .filter((f) => f.related_procedures.includes(id))
      .map((f) => ({
        id: f.id,
        question: f.question,
        category: f.category,
      }));

    return c.json({
      type: "procedure",
      data: foundProc,
      related_faqs: relatedFaqs,
      disclaimer: GLOBAL_DISCLAIMER,
    });
  }

  return c.json({ error: "not found", id, disclaimer: GLOBAL_DISCLAIMER }, 404);
});

app.post("/checklist", async (c) => {
  const body = await c.req.json().catch(() => ({} as any));
  const id: string = body.id || "";
  const format: string = body.format || "json";

  const foundProc = procedures.find((p) => p.id === id);
  if (!foundProc) {
    // ID 未指定の場合はカテゴリで手続き一覧を返す
    if (!id && body.category) {
      const categoryProcs = procedures.filter(
        (p) => p.category === body.category
      );
      return c.json({
        category: body.category,
        procedures: categoryProcs.map((p) => ({
          id: p.id,
          name: p.name,
          estimated_days: p.estimated_days,
          cost_jpy: p.cost_jpy,
          online_available: p.online_available,
          steps_count: p.steps.length,
          documents_count: p.required_documents.length,
        })),
        disclaimer: GLOBAL_DISCLAIMER,
      });
    }

    return c.json({
      error: "not found",
      id,
      available_ids: procedures.map((p) => ({ id: p.id, name: p.name })),
      disclaimer: GLOBAL_DISCLAIMER,
    }, 404);
  }

  // 関連FAQを取得
  const relatedFaqs = faqs
    .filter((f) => f.related_procedures.includes(id))
    .map((f) => ({
      id: f.id,
      question: f.question,
      category: f.category,
    }));

  if (format === "markdown") {
    const markdown = buildChecklistMarkdown(foundProc);
    return c.json({
      type: "procedure_checklist",
      format: "markdown",
      markdown,
      related_faqs: relatedFaqs,
      disclaimer: GLOBAL_DISCLAIMER,
    });
  }

  return c.json({
    type: "procedure_checklist",
    format: "json",
    procedure: {
      id: foundProc.id,
      name: foundProc.name,
      category: foundProc.category,
      estimated_days: foundProc.estimated_days,
      cost_jpy: foundProc.cost_jpy,
      where_to_submit: foundProc.where_to_submit,
      online_available: foundProc.online_available,
    },
    checklist: {
      required_documents: foundProc.required_documents.map((doc, i) => ({
        order: i + 1,
        document: doc,
        checked: false,
      })),
      steps: foundProc.steps.map((step, i) => ({
        order: i + 1,
        description: step,
        completed: false,
      })),
    },
    tips: foundProc.tips,
    common_mistakes: foundProc.common_mistakes,
    related_faqs: relatedFaqs,
    disclaimer: GLOBAL_DISCLAIMER,
  });
});

// ─────────────────────────────────────────────────────────────
// MCP JSON-RPC エンドポイント
// ─────────────────────────────────────────────────────────────

app.post("/mcp", async (c) => {
  const body = await c.req.json().catch(() => ({} as any));
  const { method, params, id } = body;

  // ─── initialize ───
  if (method === "initialize") {
    return c.json({
      jsonrpc: "2.0",
      id,
      result: {
        protocolVersion: "2024-11-05",
        capabilities: { tools: {} },
        serverInfo: {
          name: "jp-startup-legal-mcp",
          version: "0.1.0",
        },
      },
    });
  }

  // ─── tools/list ───
  if (method === "tools/list") {
    return c.json({
      jsonrpc: "2.0",
      id,
      result: {
        tools: [
          {
            name: "search_legal_faq",
            description:
              "日本のスタートアップ・フリーランス向け法務FAQを検索する。キーワード、カテゴリ（会社設立/契約/知的財産/税務/労務/許認可/個人情報/フリーランス）、対象者、難易度でフィルタ可能。法的助言ではありません。",
            inputSchema: {
              type: "object",
              properties: {
                query: {
                  type: "string",
                  description:
                    "検索キーワード（例: 開業届、契約書、商標、インボイス）",
                },
                category: {
                  type: "string",
                  description: "カテゴリでフィルタ",
                  enum: [
                    "会社設立",
                    "契約",
                    "知的財産",
                    "税務",
                    "労務",
                    "許認可",
                    "個人情報",
                    "フリーランス",
                  ],
                },
                target: {
                  type: "string",
                  description: "対象者でフィルタ",
                  enum: [
                    "個人事業主",
                    "法人",
                    "フリーランス",
                    "all",
                  ],
                },
                difficulty: {
                  type: "string",
                  description: "難易度でフィルタ",
                  enum: ["初級", "中級", "上級"],
                },
                include_procedures: {
                  type: "boolean",
                  description:
                    "関連する手続きも検索結果に含めるか（デフォルト: true）",
                },
              },
            },
          },
          {
            name: "get_faq_detail",
            description:
              "1件の法務FAQ または手続きの詳細を取得する。関連する手続き・FAQ も返す。法的助言ではありません。",
            inputSchema: {
              type: "object",
              properties: {
                id: {
                  type: "string",
                  description:
                    "FAQ ID（faq-001 等）または手続き ID（proc-001 等）",
                },
              },
              required: ["id"],
            },
          },
          {
            name: "get_procedure_checklist",
            description:
              "法的手続きの完全なチェックリストを取得する。必要書類、手順、費用、所要日数、よくあるミスを含む。法的助言ではありません。",
            inputSchema: {
              type: "object",
              properties: {
                id: {
                  type: "string",
                  description: "手続き ID（proc-001 等）",
                },
                category: {
                  type: "string",
                  description:
                    "ID 未指定の場合、カテゴリで手続き一覧を取得",
                  enum: [
                    "会社設立",
                    "税務",
                    "労務",
                    "契約",
                    "知的財産",
                    "個人情報",
                    "許認可",
                    "フリーランス",
                  ],
                },
                format: {
                  type: "string",
                  description: "出力形式（json または markdown）",
                  enum: ["json", "markdown"],
                },
              },
            },
          },
        ],
      },
    });
  }

  // ─── tools/call ───
  if (method === "tools/call") {
    const toolName = params?.name;
    const args = params?.arguments || {};

    // search_legal_faq
    if (toolName === "search_legal_faq") {
      const faqResults = searchFaqs({
        query: args.query,
        category: args.category,
        target: args.target,
        difficulty: args.difficulty,
      });

      let procResults: Procedure[] = [];
      if (args.include_procedures !== false) {
        procResults = searchProcedures({
          query: args.query,
          category: args.category,
        });
      }

      const result = {
        query: args.query || "",
        faq_count: faqResults.length,
        procedure_count: procResults.length,
        faqs: faqResults.slice(0, 10).map((f) => ({
          id: f.id,
          question: f.question,
          category: f.category,
          target: f.target,
          difficulty: f.difficulty,
          keywords: f.keywords,
        })),
        procedures: procResults.slice(0, 5).map((p) => ({
          id: p.id,
          name: p.name,
          category: p.category,
          estimated_days: p.estimated_days,
          cost_jpy: p.cost_jpy,
        })),
        disclaimer: GLOBAL_DISCLAIMER,
      };

      return c.json({
        jsonrpc: "2.0",
        id,
        result: {
          content: [
            { type: "text", text: JSON.stringify(result, null, 2) },
          ],
        },
      });
    }

    // get_faq_detail
    if (toolName === "get_faq_detail") {
      const faqId = args.id || "";

      const foundFaq = faqs.find((f) => f.id === faqId);
      if (foundFaq) {
        const relatedProcs = foundFaq.related_procedures
          .map((procId: string) => procedures.find((p) => p.id === procId))
          .filter(Boolean)
          .map((p: Procedure | undefined) => ({
            id: p!.id,
            name: p!.name,
            category: p!.category,
            estimated_days: p!.estimated_days,
            cost_jpy: p!.cost_jpy,
          }));

        const result = {
          type: "faq",
          data: foundFaq,
          related_procedures: relatedProcs,
          disclaimer: GLOBAL_DISCLAIMER,
        };

        return c.json({
          jsonrpc: "2.0",
          id,
          result: {
            content: [
              { type: "text", text: JSON.stringify(result, null, 2) },
            ],
          },
        });
      }

      const foundProc = procedures.find((p) => p.id === faqId);
      if (foundProc) {
        const relatedFaqList = faqs
          .filter((f) => f.related_procedures.includes(faqId))
          .map((f) => ({
            id: f.id,
            question: f.question,
            category: f.category,
          }));

        const result = {
          type: "procedure",
          data: foundProc,
          related_faqs: relatedFaqList,
          disclaimer: GLOBAL_DISCLAIMER,
        };

        return c.json({
          jsonrpc: "2.0",
          id,
          result: {
            content: [
              { type: "text", text: JSON.stringify(result, null, 2) },
            ],
          },
        });
      }

      return c.json({
        jsonrpc: "2.0",
        id,
        error: {
          code: -32602,
          message: `not found: ${faqId}。${GLOBAL_DISCLAIMER}`,
        },
      });
    }

    // get_procedure_checklist
    if (toolName === "get_procedure_checklist") {
      const procId = args.id || "";
      const format = args.format || "json";

      if (!procId && args.category) {
        const categoryProcs = procedures.filter(
          (p) => p.category === args.category
        );
        const result = {
          category: args.category,
          procedures: categoryProcs.map((p) => ({
            id: p.id,
            name: p.name,
            estimated_days: p.estimated_days,
            cost_jpy: p.cost_jpy,
            online_available: p.online_available,
            steps_count: p.steps.length,
            documents_count: p.required_documents.length,
          })),
          disclaimer: GLOBAL_DISCLAIMER,
        };

        return c.json({
          jsonrpc: "2.0",
          id,
          result: {
            content: [
              { type: "text", text: JSON.stringify(result, null, 2) },
            ],
          },
        });
      }

      const foundProc = procedures.find((p) => p.id === procId);
      if (!foundProc) {
        return c.json({
          jsonrpc: "2.0",
          id,
          error: {
            code: -32602,
            message: `not found: ${procId}。利用可能なID: ${procedures.map((p) => p.id).join(", ")}`,
          },
        });
      }

      const relatedFaqList = faqs
        .filter((f) => f.related_procedures.includes(procId))
        .map((f) => ({
          id: f.id,
          question: f.question,
          category: f.category,
        }));

      let resultData: any;

      if (format === "markdown") {
        const markdown = buildChecklistMarkdown(foundProc);
        resultData = {
          type: "procedure_checklist",
          format: "markdown",
          markdown,
          related_faqs: relatedFaqList,
          disclaimer: GLOBAL_DISCLAIMER,
        };
      } else {
        resultData = {
          type: "procedure_checklist",
          format: "json",
          procedure: {
            id: foundProc.id,
            name: foundProc.name,
            category: foundProc.category,
            estimated_days: foundProc.estimated_days,
            cost_jpy: foundProc.cost_jpy,
            where_to_submit: foundProc.where_to_submit,
            online_available: foundProc.online_available,
          },
          checklist: {
            required_documents: foundProc.required_documents.map(
              (doc, i) => ({
                order: i + 1,
                document: doc,
                checked: false,
              })
            ),
            steps: foundProc.steps.map((step, i) => ({
              order: i + 1,
              description: step,
              completed: false,
            })),
          },
          tips: foundProc.tips,
          common_mistakes: foundProc.common_mistakes,
          related_faqs: relatedFaqList,
          disclaimer: GLOBAL_DISCLAIMER,
        };
      }

      return c.json({
        jsonrpc: "2.0",
        id,
        result: {
          content: [
            { type: "text", text: JSON.stringify(resultData, null, 2) },
          ],
        },
      });
    }

    return c.json({
      jsonrpc: "2.0",
      id,
      error: { code: -32601, message: `unknown tool: ${toolName}` },
    });
  }

  // ─── unknown method ───
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
  const faqCategories = [...new Set(faqs.map((f) => f.category))];
  const procCategories = [...new Set(procedures.map((p) => p.category))];

  return c.html(`<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>jp-startup-legal-mcp - 日本のスタートアップ・フリーランス法務FAQ</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", sans-serif; max-width: 720px; margin: 40px auto; padding: 20px; color: #24292f; line-height: 1.7; }
  code { background: #f6f8fa; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }
  pre { background: #0d1117; color: #c9d1d9; padding: 16px; border-radius: 8px; overflow-x: auto; }
  h1 { border-bottom: 1px solid #e1e4e8; padding-bottom: 8px; }
  h2 { color: #0969da; margin-top: 32px; }
  a { color: #0969da; }
  .badge { display: inline-block; background: #1f883d; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; }
  .warn { display: inline-block; background: #d1242f; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; }
  table { border-collapse: collapse; width: 100%; margin: 12px 0; }
  th, td { border: 1px solid #d0d7de; padding: 8px 12px; text-align: left; }
  th { background: #f6f8fa; }
  .disclaimer { background: #fff8c5; border: 1px solid #d4a72c; padding: 12px; border-radius: 8px; margin: 16px 0; font-size: 0.9em; }
  .category-list { display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0; }
  .category-tag { background: #ddf4ff; color: #0969da; padding: 2px 8px; border-radius: 12px; font-size: 0.85em; }
</style>
</head>
<body>
<h1>jp-startup-legal-mcp</h1>
<p><span class="badge">x402 対応</span> <span class="warn">法的助言ではありません</span></p>
<p>日本のスタートアップ・フリーランス向け法務FAQ・手続きガイドを AI エージェント（Claude / OpenAI / その他）に提供する MCP サーバー。${faqs.length} 件の法務FAQ と ${procedures.length} 件の手続きガイドを収録。</p>

<div class="disclaimer">
<strong>免責事項:</strong> この情報は一般的な法務知識の提供を目的としており、法的助言ではありません。具体的な法的問題については、必ず弁護士・司法書士・税理士等の専門家にご相談ください。法令は改正される場合がありますので、最新の法令を確認してください。
</div>

<h2>カバーするカテゴリ</h2>
<p><strong>FAQ:</strong></p>
<div class="category-list">
${faqCategories.map((cat) => `<span class="category-tag">${cat}</span>`).join("\n")}
</div>
<p><strong>手続きガイド:</strong></p>
<div class="category-list">
${procCategories.map((cat) => `<span class="category-tag">${cat}</span>`).join("\n")}
</div>

<h2>料金</h2>
<table>
<tr><th>エンドポイント</th><th>料金（USDC）</th><th>説明</th></tr>
<tr><td><code>GET /</code></td><td>無料</td><td>ランディングページ</td></tr>
<tr><td><code>GET /health</code></td><td>無料</td><td>ヘルスチェック</td></tr>
<tr><td><code>GET /info</code></td><td>無料</td><td>サーバーメタ情報</td></tr>
<tr><td><code>GET /free/faq</code></td><td>無料</td><td>FAQ 1件ランダム表示</td></tr>
<tr><td><code>POST /search</code></td><td><strong>$0.05</strong></td><td>キーワード・カテゴリ検索</td></tr>
<tr><td><code>POST /detail</code></td><td><strong>$0.03</strong></td><td>FAQ・手続きの詳細取得</td></tr>
<tr><td><code>POST /checklist</code></td><td><strong>$0.10</strong></td><td>手続きチェックリスト（全ステップ・書類付き）</td></tr>
<tr><td><code>POST /mcp</code></td><td><strong>$0.05</strong></td><td>MCP JSON-RPC</td></tr>
</table>
<p>支払いは x402 protocol 経由で自動決済（Base / Solana、2 秒・手数料 ほぼ0）</p>

<h2>無料で試す</h2>
<pre>curl ${origin}/info
curl ${origin}/free/faq</pre>

<h2>Claude Desktop 設定例</h2>
<pre>{
  "mcpServers": {
    "jp-legal": { "url": "${origin}/mcp" }
  }
}</pre>

<h2>MCP ツール</h2>
<table>
<tr><th>ツール名</th><th>説明</th></tr>
<tr><td><code>search_legal_faq</code></td><td>法務FAQの検索（カテゴリ・対象者・難易度フィルタ付き）</td></tr>
<tr><td><code>get_faq_detail</code></td><td>FAQ・手続きの詳細取得（関連情報付き）</td></tr>
<tr><td><code>get_procedure_checklist</code></td><td>手続きの完全チェックリスト（書類・ステップ・注意点）</td></tr>
</table>

<p><small>Built and maintained by an autonomous AI company based in Toyama, Japan.</small></p>
</body>
</html>`);
});

export default app;
