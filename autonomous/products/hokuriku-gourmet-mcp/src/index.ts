// hokuriku-gourmet-mcp / src/index.ts
//
// 北陸三県（富山・石川・福井）のグルメ・食文化情報を検索する MCP サーバー。
// x402 protocol で有料ゲート、無料 demo エンドポイントあり。
//
// エンドポイント:
//   GET  /            HTML ランディング
//   GET  /health      ヘルスチェック
//   GET  /info        メタ情報
//   GET  /free/dish   ランダム1件（広告）
//   POST /search      $0.03 USDC  カテゴリ/県/エリア/季節検索
//   POST /recommend   $0.08 USDC  季節+県+予算からおすすめ料理をレコメンド
//   POST /detail      $0.02 USDC  1件の詳細
//   POST /mcp         $0.03 USDC  MCP JSON-RPC

import { Hono } from "hono";
import { paymentMiddleware } from "x402-hono";
import gourmetData from "../data/gourmet.json";

// ─────────────────────────────────────────────────────────────
// 型定義
// ─────────────────────────────────────────────────────────────

type Bindings = {
  X402_NETWORK: string;
  X402_PRICE_SEARCH: string;
  X402_PRICE_RECOMMEND: string;
  X402_PRICE_DETAIL: string;
  X402_FACILITATOR: string;
  SERVER_ADDRESS: string;
};

type FamousRestaurant = {
  name: string;
  area: string;
};

type Food = {
  id: string;
  name: string;
  category: string;
  prefecture: string;
  area: string;
  season_best: string[];
  description: string;
  price_range_jpy: { min: number; max: number };
  famous_restaurants: FamousRestaurant[];
  keywords: string[];
  ai_recommend_context: string;
  paired_with: string[];
};

type FishCalendar = {
  description: string;
  [month: string]: string | string[];
};

// ─────────────────────────────────────────────────────────────
// データ読み込み
// ─────────────────────────────────────────────────────────────

const foods = gourmetData.foods as Food[];
const fishCalendar = gourmetData._meta.toyama_bay_fish_calendar as FishCalendar;
const meta = gourmetData._meta;

// ─────────────────────────────────────────────────────────────
// ユーティリティ
// ─────────────────────────────────────────────────────────────

/** 月番号(1-12)から季節を推定する */
function monthToSeason(month: number): string {
  if (month >= 3 && month <= 5) return "春";
  if (month >= 6 && month <= 8) return "夏";
  if (month >= 9 && month <= 11) return "秋";
  return "冬";
}

/** 月番号(1-12)から富山湾の旬魚を返す */
function getToyamaBayFish(month: number): string[] {
  const key = `${month}月`;
  const entry = fishCalendar[key];
  if (Array.isArray(entry)) return entry;
  return [];
}

/** 現在の月の季節を取得 */
function currentSeason(): string {
  return monthToSeason(new Date().getMonth() + 1);
}

/** 現在の月番号を取得 */
function currentMonth(): number {
  return new Date().getMonth() + 1;
}

/** テキスト全文検索用ヘイスタック生成 */
function buildHaystack(food: Food): string {
  return [
    food.name,
    food.description,
    food.category,
    food.prefecture,
    food.area,
    food.ai_recommend_context,
    ...food.keywords,
    ...food.famous_restaurants.map((r) => r.name),
  ]
    .join(" ")
    .toLowerCase();
}

/** ペアリング先の食品情報を取得 */
function getPairedFoods(food: Food): { id: string; name: string; category: string; prefecture: string }[] {
  return food.paired_with
    .map((pid) => foods.find((f) => f.id === pid))
    .filter((f): f is Food => f !== undefined)
    .map((f) => ({
      id: f.id,
      name: f.name,
      category: f.category,
      prefecture: f.prefecture,
    }));
}

// ─────────────────────────────────────────────────────────────
// Hono アプリ初期化
// ─────────────────────────────────────────────────────────────

const app = new Hono<{ Bindings: Bindings }>();

// ─────────────────────────────────────────────────────────────
// 無料エンドポイント
// ─────────────────────────────────────────────────────────────

app.get("/health", (c) =>
  c.json({
    ok: true,
    service: "hokuriku-gourmet-mcp",
    version: "0.1.0",
    time: new Date().toISOString(),
  })
);

app.get("/info", (c) => {
  const month = currentMonth();
  return c.json({
    name: "hokuriku-gourmet-mcp",
    version: "0.1.0",
    description_ja:
      "北陸三県（富山・石川・福井）のグルメ・郷土料理・B級グルメ・和菓子・地酒・伝統食情報を検索する MCP サーバー。",
    description_en:
      "MCP server for Hokuriku region (Toyama, Ishikawa, Fukui) gourmet guide: seafood, local cuisine, B-grade gourmet, wagashi, sake, traditional foods.",
    foods_count: foods.length,
    categories: [...new Set(foods.map((f) => f.category))],
    prefectures: [...new Set(foods.map((f) => f.prefecture))],
    areas: [...new Set(foods.map((f) => f.area))],
    last_updated: meta.last_updated,
    current_season: currentSeason(),
    toyama_bay_fish_this_month: getToyamaBayFish(month),
    pricing: {
      "/search": "$0.03 USDC",
      "/recommend": "$0.08 USDC",
      "/detail": "$0.02 USDC",
      "/mcp": "$0.03 USDC",
    },
  });
});

app.get("/free/dish", (c) => {
  const sample = foods[Math.floor(Math.random() * foods.length)];
  const month = currentMonth();
  return c.json({
    sample: {
      id: sample.id,
      name: sample.name,
      category: sample.category,
      prefecture: sample.prefecture,
      area: sample.area,
      season_best: sample.season_best,
    },
    total_count: foods.length,
    current_season: currentSeason(),
    toyama_bay_fish_this_month: getToyamaBayFish(month),
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
    path === "/free/dish"
  ) {
    return next();
  }

  const middleware = paymentMiddleware(
    c.env.SERVER_ADDRESS as `0x${string}`,
    {
      "/search": {
        price: `$${c.env.X402_PRICE_SEARCH}`,
        network: c.env.X402_NETWORK,
        config: { description: "Search Hokuriku gourmet foods" },
      },
      "/recommend": {
        price: `$${c.env.X402_PRICE_RECOMMEND}`,
        network: c.env.X402_NETWORK,
        config: { description: "Get Hokuriku meal plan recommendations" },
      },
      "/detail": {
        price: `$${c.env.X402_PRICE_DETAIL}`,
        network: c.env.X402_NETWORK,
        config: { description: "Get Hokuriku food detail" },
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
// 有料エンドポイント: /search
// ─────────────────────────────────────────────────────────────

app.post("/search", async (c) => {
  const body = await c.req.json().catch(() => ({} as any));
  const query: string = (body.query || "").toString().toLowerCase();
  const category: string | undefined = body.category;
  const prefecture: string | undefined = body.prefecture;
  const area: string | undefined = body.area;
  const season: string | undefined = body.season;
  const maxBudget: number | undefined = body.max_budget_jpy;
  const minBudget: number | undefined = body.min_budget_jpy;

  const results = foods.filter((f) => {
    // フリーテキスト検索
    if (query) {
      const hay = buildHaystack(f);
      if (!hay.includes(query)) return false;
    }
    // カテゴリフィルタ
    if (category && f.category !== category) return false;
    // 県フィルタ
    if (prefecture && f.prefecture !== prefecture) return false;
    // エリアフィルタ
    if (area && !f.area.includes(area)) return false;
    // 季節フィルタ（通年は常にマッチ）
    if (season) {
      const isAllSeason =
        f.season_best.length === 4 &&
        f.season_best.includes("春") &&
        f.season_best.includes("夏") &&
        f.season_best.includes("秋") &&
        f.season_best.includes("冬");
      if (!isAllSeason && !f.season_best.includes(season)) return false;
    }
    // 予算フィルタ
    if (maxBudget && f.price_range_jpy.min > maxBudget) return false;
    if (minBudget && f.price_range_jpy.max < minBudget) return false;
    return true;
  });

  const month = currentMonth();

  return c.json({
    query,
    filters: { category, prefecture, area, season, maxBudget, minBudget },
    count: results.length,
    results: results.map((f) => ({
      ...f,
      paired_foods: getPairedFoods(f),
    })),
    toyama_bay_fish_this_month: getToyamaBayFish(month),
  });
});

// ─────────────────────────────────────────────────────────────
// 有料エンドポイント: /recommend
// ─────────────────────────────────────────────────────────────

app.post("/recommend", async (c) => {
  const body = await c.req.json().catch(() => ({} as any));
  const context: string = (body.context || "").toString().toLowerCase();
  const prefecture: string | undefined = body.prefecture;
  const season: string = body.season || currentSeason();
  const totalBudget: number = Number(body.total_budget_jpy) || 10000;
  const mealType: string | undefined = body.meal_type; // 朝食/昼食/夕食/おやつ/お土産
  const partySize: number = Number(body.party_size) || 1;
  const month: number = Number(body.month) || currentMonth();

  const perPersonBudget = totalBudget / partySize;

  // スコアリング
  const scored = foods.map((f) => {
    let score = 0;

    // コンテキストマッチ（フリーテキスト）
    if (context) {
      const hay = buildHaystack(f);
      const words = context.split(/\s+/).filter(Boolean);
      for (const w of words) {
        if (hay.includes(w)) score += 10;
      }
    }

    // 季節マッチ
    if (f.season_best.includes(season)) {
      score += 20;
    }
    // 通年メニューは少しボーナス
    if (
      f.season_best.length === 4 &&
      f.season_best.includes("春") &&
      f.season_best.includes("夏") &&
      f.season_best.includes("秋") &&
      f.season_best.includes("冬")
    ) {
      score += 5;
    }

    // 県マッチ
    if (prefecture && f.prefecture === prefecture) {
      score += 15;
    }

    // 予算適合
    if (f.price_range_jpy.min <= perPersonBudget) {
      score += 10;
    }
    if (f.price_range_jpy.max > perPersonBudget * 2) {
      score -= 10; // 予算の2倍以上は減点
    }

    // 食事タイプマッチ
    if (mealType) {
      const typeContext = mealType.toLowerCase();
      if (typeContext.includes("朝") && f.keywords.some((k) => k.includes("朝"))) score += 10;
      if (typeContext.includes("土産") || typeContext.includes("おみやげ")) {
        if (f.keywords.some((k) => k.includes("土産") || k.includes("お土産"))) score += 15;
      }
      if (typeContext.includes("おやつ") || typeContext.includes("甘")) {
        if (f.category === "和菓子") score += 15;
      }
      if (typeContext.includes("夕") || typeContext.includes("ディナー")) {
        if (f.category === "海鮮" || f.category === "郷土料理") score += 10;
      }
      if (typeContext.includes("酒") || typeContext.includes("飲")) {
        if (f.category === "地酒") score += 20;
      }
    }

    // カテゴリ多様性ボーナス（後で調整）
    return { food: f, score };
  });

  // スコア順ソート
  scored.sort((a, b) => b.score - a.score);

  // 上位から、カテゴリの多様性を考慮して選出
  const selected: typeof scored = [];
  const categoryCount: Record<string, number> = {};
  const maxPerCategory = 3;

  for (const item of scored) {
    if (selected.length >= 10) break;
    const cat = item.food.category;
    if ((categoryCount[cat] || 0) >= maxPerCategory) continue;
    selected.push(item);
    categoryCount[cat] = (categoryCount[cat] || 0) + 1;
  }

  // 富山湾旬魚カレンダー
  const seasonalFish = getToyamaBayFish(month);

  // 予算配分提案
  const budgetPlan = {
    total_jpy: totalBudget,
    per_person_jpy: perPersonBudget,
    party_size: partySize,
    suggested_allocation: {
      メインの食事: Math.round(perPersonBudget * 0.5),
      軽食_おやつ: Math.round(perPersonBudget * 0.2),
      お土産: Math.round(perPersonBudget * 0.2),
      飲み物_地酒: Math.round(perPersonBudget * 0.1),
    },
  };

  return c.json({
    input: { context, prefecture, season, totalBudget, mealType, partySize, month },
    recommendation: selected.map((x) => ({
      ...x.food,
      recommend_score: x.score,
      paired_foods: getPairedFoods(x.food),
    })),
    toyama_bay_seasonal_fish: seasonalFish,
    budget_plan: budgetPlan,
    tip_ja: `${month}月の北陸は${season}の味覚が楽しめます。${seasonalFish.length > 0 ? `富山湾では${seasonalFish.join("・")}が旬です。` : ""}`,
  });
});

// ─────────────────────────────────────────────────────────────
// 有料エンドポイント: /detail
// ─────────────────────────────────────────────────────────────

app.post("/detail", async (c) => {
  const body = await c.req.json().catch(() => ({} as any));
  const id: string = body.id || "";
  const found = foods.find((f) => f.id === id);
  if (!found) {
    return c.json({ error: "not found", id }, 404);
  }

  const month = currentMonth();
  const pairedFoods = getPairedFoods(found);
  const isInSeason = found.season_best.includes(currentSeason()) ||
    (found.season_best.length === 4 &&
      found.season_best.includes("春") &&
      found.season_best.includes("夏") &&
      found.season_best.includes("秋") &&
      found.season_best.includes("冬"));

  return c.json({
    ...found,
    paired_foods: pairedFoods,
    is_in_season_now: isInSeason,
    current_season: currentSeason(),
    toyama_bay_fish_this_month: getToyamaBayFish(month),
    season_tip_ja: isInSeason
      ? `今は${found.name}の旬の時期です！ぜひお楽しみください。`
      : `${found.name}の旬は${found.season_best.join("・")}です。時期を合わせて訪問するのがおすすめです。`,
  });
});

// ─────────────────────────────────────────────────────────────
// MCP JSON-RPC
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
        serverInfo: { name: "hokuriku-gourmet-mcp", version: "0.1.0" },
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
            name: "search_hokuriku_food",
            description:
              "北陸三県（富山・石川・福井）のグルメ・郷土料理・B級グルメ・和菓子・地酒・伝統食を検索する。カテゴリ・県・季節・予算でフィルタ可能。",
            inputSchema: {
              type: "object",
              properties: {
                query: {
                  type: "string",
                  description: "フリーテキスト検索（料理名・食材・キーワード）",
                },
                category: {
                  type: "string",
                  description: "カテゴリで絞り込み",
                  enum: ["海鮮", "郷土料理", "B級グルメ", "和菓子", "地酒", "伝統食"],
                },
                prefecture: {
                  type: "string",
                  description: "県で絞り込み",
                  enum: ["富山", "石川", "福井"],
                },
                area: {
                  type: "string",
                  description: "エリア名で絞り込み（部分一致）",
                },
                season: {
                  type: "string",
                  description: "季節で絞り込み",
                  enum: ["春", "夏", "秋", "冬"],
                },
                max_budget_jpy: {
                  type: "number",
                  description: "予算上限（円）",
                },
              },
            },
          },
          {
            name: "recommend_meal_plan",
            description:
              "季節・県・予算・人数・シーンに応じて北陸の食事プランをレコメンドする。富山湾の旬魚情報付き。",
            inputSchema: {
              type: "object",
              properties: {
                context: {
                  type: "string",
                  description:
                    "どんな食事を探しているかの自由記述（例: 「冬の金沢で蟹を食べたい」「家族旅行のランチ」）",
                },
                prefecture: {
                  type: "string",
                  description: "県で絞り込み",
                  enum: ["富山", "石川", "福井"],
                },
                season: {
                  type: "string",
                  description: "季節（省略時は現在の季節）",
                  enum: ["春", "夏", "秋", "冬"],
                },
                total_budget_jpy: {
                  type: "number",
                  description: "グループ全体の食事予算（円）",
                },
                meal_type: {
                  type: "string",
                  description: "食事タイプ",
                  enum: ["朝食", "昼食", "夕食", "おやつ", "お土産", "飲み"],
                },
                party_size: {
                  type: "number",
                  description: "人数（デフォルト1）",
                },
                month: {
                  type: "number",
                  description: "月（1-12、富山湾旬魚カレンダー連動）",
                },
              },
            },
          },
          {
            name: "get_food_detail",
            description:
              "北陸グルメ1件の詳細情報を取得する。ペアリング情報・旬の判定・レストラン情報付き。",
            inputSchema: {
              type: "object",
              properties: {
                id: {
                  type: "string",
                  description: "料理のID（search結果から取得）",
                },
              },
              required: ["id"],
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

    // ─── search_hokuriku_food ───
    if (toolName === "search_hokuriku_food") {
      const q = (args.query || "").toString().toLowerCase();
      const results = foods
        .filter((f) => {
          if (q) {
            const hay = buildHaystack(f);
            if (!hay.includes(q)) return false;
          }
          if (args.category && f.category !== args.category) return false;
          if (args.prefecture && f.prefecture !== args.prefecture) return false;
          if (args.area && !f.area.includes(args.area)) return false;
          if (args.season) {
            const isAllSeason =
              f.season_best.length === 4 &&
              f.season_best.includes("春") &&
              f.season_best.includes("夏") &&
              f.season_best.includes("秋") &&
              f.season_best.includes("冬");
            if (!isAllSeason && !f.season_best.includes(args.season)) return false;
          }
          if (args.max_budget_jpy && f.price_range_jpy.min > args.max_budget_jpy) return false;
          return true;
        })
        .slice(0, 15)
        .map((f) => ({
          ...f,
          paired_foods: getPairedFoods(f),
        }));

      const month = currentMonth();
      const responseData = {
        count: results.length,
        results,
        toyama_bay_fish_this_month: getToyamaBayFish(month),
      };

      return c.json({
        jsonrpc: "2.0",
        id,
        result: {
          content: [
            { type: "text", text: JSON.stringify(responseData, null, 2) },
          ],
        },
      });
    }

    // ─── recommend_meal_plan ───
    if (toolName === "recommend_meal_plan") {
      const ctx = (args.context || "").toString().toLowerCase();
      const prefecture = args.prefecture;
      const season = args.season || currentSeason();
      const totalBudget = Number(args.total_budget_jpy) || 10000;
      const mealType = args.meal_type;
      const partySize = Number(args.party_size) || 1;
      const month = Number(args.month) || currentMonth();
      const perPersonBudget = totalBudget / partySize;

      const scored = foods.map((f) => {
        let score = 0;

        // コンテキストマッチ
        if (ctx) {
          const hay = buildHaystack(f);
          const words = ctx.split(/\s+/).filter(Boolean);
          for (const w of words) {
            if (hay.includes(w)) score += 10;
          }
        }

        // 季節マッチ
        if (f.season_best.includes(season)) score += 20;

        // 県マッチ
        if (prefecture && f.prefecture === prefecture) score += 15;

        // 予算適合
        if (f.price_range_jpy.min <= perPersonBudget) score += 10;
        if (f.price_range_jpy.max > perPersonBudget * 2) score -= 10;

        // 食事タイプマッチ
        if (mealType) {
          const mt = mealType.toLowerCase();
          if (mt.includes("土産") && f.keywords.some((k) => k.includes("土産"))) score += 15;
          if (mt.includes("おやつ") && f.category === "和菓子") score += 15;
          if ((mt.includes("夕") || mt.includes("ディナー")) && (f.category === "海鮮" || f.category === "郷土料理")) score += 10;
          if (mt.includes("飲") && f.category === "地酒") score += 20;
        }

        return { food: f, score };
      });

      scored.sort((a, b) => b.score - a.score);

      // カテゴリ多様性
      const selected: typeof scored = [];
      const catCount: Record<string, number> = {};
      for (const item of scored) {
        if (selected.length >= 8) break;
        const cat = item.food.category;
        if ((catCount[cat] || 0) >= 3) continue;
        selected.push(item);
        catCount[cat] = (catCount[cat] || 0) + 1;
      }

      const seasonalFish = getToyamaBayFish(month);

      const responseData = {
        recommendation: selected.map((x) => ({
          ...x.food,
          recommend_score: x.score,
          paired_foods: getPairedFoods(x.food),
        })),
        toyama_bay_seasonal_fish: seasonalFish,
        budget_plan: {
          total_jpy: totalBudget,
          per_person_jpy: perPersonBudget,
          party_size: partySize,
        },
        tip_ja: `${month}月の北陸は${season}の味覚が楽しめます。${seasonalFish.length > 0 ? `富山湾では${seasonalFish.join("・")}が旬です。` : ""}`,
      };

      return c.json({
        jsonrpc: "2.0",
        id,
        result: {
          content: [
            { type: "text", text: JSON.stringify(responseData, null, 2) },
          ],
        },
      });
    }

    // ─── get_food_detail ───
    if (toolName === "get_food_detail") {
      const found = foods.find((f) => f.id === args.id);
      if (!found) {
        return c.json({
          jsonrpc: "2.0",
          id,
          error: { code: -32602, message: `not found: ${args.id}` },
        });
      }

      const month = currentMonth();
      const isInSeason = found.season_best.includes(currentSeason()) ||
        (found.season_best.length === 4 &&
          found.season_best.includes("春") &&
          found.season_best.includes("夏") &&
          found.season_best.includes("秋") &&
          found.season_best.includes("冬"));

      const detail = {
        ...found,
        paired_foods: getPairedFoods(found),
        is_in_season_now: isInSeason,
        current_season: currentSeason(),
        toyama_bay_fish_this_month: getToyamaBayFish(month),
        season_tip_ja: isInSeason
          ? `今は${found.name}の旬の時期です！`
          : `${found.name}の旬は${found.season_best.join("・")}です。`,
      };

      return c.json({
        jsonrpc: "2.0",
        id,
        result: {
          content: [
            { type: "text", text: JSON.stringify(detail, null, 2) },
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
  const month = currentMonth();
  const season = currentSeason();
  const fish = getToyamaBayFish(month);
  const categories = [...new Set(foods.map((f) => f.category))];
  const prefectures = [...new Set(foods.map((f) => f.prefecture))];

  // 季節のおすすめをピックアップ
  const seasonalPicks = foods
    .filter((f) => f.season_best.includes(season))
    .slice(0, 5);

  return c.html(`<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>hokuriku-gourmet-mcp — 北陸グルメガイド</title>
<style>
  body { font-family: -apple-system, "Hiragino Kaku Gothic ProN", sans-serif; max-width: 780px; margin: 40px auto; padding: 20px; color: #24292f; line-height: 1.8; }
  code { background: #f6f8fa; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }
  pre { background: #0d1117; color: #c9d1d9; padding: 16px; border-radius: 8px; overflow-x: auto; font-size: 0.85em; }
  h1 { border-bottom: 2px solid #d73a49; padding-bottom: 8px; }
  h2 { color: #0969da; margin-top: 32px; }
  .badge { display: inline-block; background: #1f883d; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; }
  .season-badge { display: inline-block; background: #d73a49; color: white; padding: 2px 10px; border-radius: 12px; font-size: 0.8em; margin-right: 4px; }
  table { border-collapse: collapse; width: 100%; margin: 12px 0; }
  th, td { border: 1px solid #d0d7de; padding: 8px 12px; text-align: left; font-size: 0.9em; }
  th { background: #f6f8fa; }
  .fish-list { background: #ddf4ff; padding: 12px 16px; border-radius: 8px; margin: 12px 0; }
  .pick { background: #fff8dc; padding: 8px 12px; border-radius: 6px; margin: 6px 0; border-left: 4px solid #d73a49; }
</style></head><body>

<h1>北陸グルメガイド MCP</h1>
<p><span class="badge">x402 対応</span> <span class="season-badge">${season}の味覚</span>
北陸三県（富山・石川・福井）の海鮮・郷土料理・B級グルメ・和菓子・地酒・伝統食 ${foods.length} 品を収録した AI エージェント向けグルメ MCP サーバー。</p>

<div class="fish-list">
<strong>${month}月の富山湾 旬魚:</strong> ${fish.length > 0 ? fish.join("・") : "情報なし"}
</div>

<h2>今${season}のおすすめ</h2>
${seasonalPicks.map((f) => `<div class="pick"><strong>${f.name}</strong>（${f.prefecture}・${f.category}）— ${f.description.slice(0, 60)}…</div>`).join("\n")}

<h2>収録カテゴリ</h2>
<p>${categories.map((cat) => `<code>${cat}</code>`).join(" ")}　｜　${prefectures.map((p) => `<code>${p}</code>`).join(" ")}</p>

<h2>料金（USDC）</h2>
<table>
<tr><th>エンドポイント</th><th>料金</th><th>説明</th></tr>
<tr><td><code>GET /</code></td><td>無料</td><td>ランディングページ</td></tr>
<tr><td><code>GET /health</code></td><td>無料</td><td>ヘルスチェック</td></tr>
<tr><td><code>GET /info</code></td><td>無料</td><td>メタ情報・旬魚カレンダー</td></tr>
<tr><td><code>GET /free/dish</code></td><td>無料</td><td>ランダム1品（お試し）</td></tr>
<tr><td><code>POST /search</code></td><td><strong>$0.03</strong></td><td>カテゴリ/県/季節/予算で検索</td></tr>
<tr><td><code>POST /recommend</code></td><td><strong>$0.08</strong></td><td>食事プランレコメンド</td></tr>
<tr><td><code>POST /detail</code></td><td><strong>$0.02</strong></td><td>1品の詳細</td></tr>
<tr><td><code>POST /mcp</code></td><td><strong>$0.03</strong></td><td>MCP JSON-RPC</td></tr>
</table>

<h2>無料で試す</h2>
<pre>curl ${origin}/info
curl ${origin}/free/dish</pre>

<h2>Claude Desktop 設定</h2>
<pre>{
  "mcpServers": {
    "hokuriku-gourmet": { "url": "${origin}/mcp" }
  }
}</pre>

<h2>MCP ツール一覧</h2>
<table>
<tr><th>ツール名</th><th>説明</th></tr>
<tr><td><code>search_hokuriku_food</code></td><td>カテゴリ・県・季節・予算でグルメ検索</td></tr>
<tr><td><code>recommend_meal_plan</code></td><td>シーンに合わせた食事プランレコメンド</td></tr>
<tr><td><code>get_food_detail</code></td><td>1品の詳細情報（ペアリング・レストラン・旬判定）</td></tr>
</table>

<h2>富山湾 旬魚カレンダー</h2>
<table>
<tr><th>月</th><th>旬の魚介</th></tr>
<tr><td>1月</td><td>寒ブリ・ズワイガニ・アンコウ・タラ</td></tr>
<tr><td>2月</td><td>寒ブリ・ズワイガニ・メジマグロ・ヤリイカ</td></tr>
<tr><td>3月</td><td>ホタルイカ・サヨリ・メバル・ヤリイカ</td></tr>
<tr><td>4月</td><td>ホタルイカ・白えび・サクラマス・フクラギ</td></tr>
<tr><td>5月</td><td>白えび・岩ガキ・サクラマス・キジハタ</td></tr>
<tr><td>6月</td><td>白えび・岩ガキ・バイ貝・マアジ</td></tr>
<tr><td>7月</td><td>岩ガキ・バイ貝・マアジ・キス</td></tr>
<tr><td>8月</td><td>バイ貝・マアジ・カワハギ・キス</td></tr>
<tr><td>9月</td><td>甘えび・フクラギ・カワハギ・アオリイカ</td></tr>
<tr><td>10月</td><td>甘えび・フクラギ・ベニズワイガニ・アオリイカ</td></tr>
<tr><td>11月</td><td>寒ブリ・ズワイガニ・甘えび・カワハギ</td></tr>
<tr><td>12月</td><td>寒ブリ・ズワイガニ・甘えび・アンコウ</td></tr>
</table>

<p><small>Built by an autonomous AI company in Toyama, Japan. Data is public tourism information.</small></p>
</body></html>`);
});

export default app;
