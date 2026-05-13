// jp-tax-calendar-mcp / src/index.ts
//
// Cloudflare Workers で動く、日本の税務・届出・経理カレンダー MCP サーバー。
// x402 payment middleware で有料アクセスを USDC で自動決済する。
//
// 無料エンドポイント（広告・獲得目的）:
//   GET  /           - HTML ランディングページ
//   GET  /health     - ヘルスチェック
//   GET  /info       - サーバーメタ情報
//   GET  /free/next  - 直近の期限1件だけ表示
//
// 有料エンドポイント（x402 支払い必須）:
//   POST /search     - キーワード検索（$0.03 USDC / req）
//   POST /upcoming   - N日以内の期限一覧（$0.05 USDC / req）
//   POST /detail     - 1件の詳細取得（$0.02 USDC / req）
//   POST /mcp        - MCP JSON-RPC エンドポイント（$0.03 USDC / req）

import { Hono } from "hono";
import { paymentMiddleware } from "x402-hono";
import calendarData from "../data/calendar.json";

// ─────────────────────────────────────────────────────────────
// 型定義
// ─────────────────────────────────────────────────────────────

type Bindings = {
  X402_NETWORK: string;
  X402_PRICE_SEARCH: string;
  X402_PRICE_UPCOMING: string;
  X402_PRICE_DETAIL: string;
  X402_PRICE_MCP: string;
  X402_CURRENCY: string;
  X402_FACILITATOR: string;
  SERVER_ADDRESS: string;
};

type DatePattern = {
  type: "monthly" | "quarterly" | "annual";
  month?: number;
  day?: number;
  period_start_month?: number;
  period_start_day?: number;
  note: string;
};

type Deadline = {
  id: string;
  name: string;
  category: string;
  date_pattern: DatePattern;
  description: string;
  target: string;
  penalty_for_missing: string;
  keywords: string[];
  regions: string[];
};

const deadlines = calendarData.deadlines as Deadline[];

const app = new Hono<{ Bindings: Bindings }>();

// ─────────────────────────────────────────────────────────────
// ユーティリティ関数
// ─────────────────────────────────────────────────────────────

/**
 * 指定日付から N 日以内に期限が来る deadline を抽出する。
 * monthly の場合は毎月の期限、annual の場合は年1回の期限として判定。
 * day が -1（不定期）の場合は除外する。
 */
function getUpcomingDeadlines(
  fromDate: Date,
  withinDays: number,
  targetFilter?: string,
  categoryFilter?: string,
  regionFilter?: string
): (Deadline & { next_date: string; days_until: number })[] {
  const results: (Deadline & { next_date: string; days_until: number })[] = [];
  const fromTime = fromDate.getTime();
  const endDate = new Date(fromTime + withinDays * 24 * 60 * 60 * 1000);

  for (const dl of deadlines) {
    // フィルタ適用
    if (targetFilter && targetFilter !== "all") {
      if (dl.target !== "both" && dl.target !== targetFilter) continue;
    }
    if (categoryFilter && dl.category !== categoryFilter) continue;
    if (regionFilter && !dl.regions.some((r) => r.includes(regionFilter)))
      continue;

    const candidates = getNextDates(dl.date_pattern, fromDate, endDate);

    for (const nextDate of candidates) {
      const diffMs = nextDate.getTime() - fromTime;
      const daysUntil = Math.ceil(diffMs / (24 * 60 * 60 * 1000));

      if (daysUntil >= 0 && daysUntil <= withinDays) {
        results.push({
          ...dl,
          next_date: formatDate(nextDate),
          days_until: daysUntil,
        });
      }
    }
  }

  results.sort((a, b) => a.days_until - b.days_until);
  return results;
}

/**
 * DatePattern から次の期限日の候補を生成する。
 * fromDate〜endDate の範囲に含まれる日付を返す。
 */
function getNextDates(
  pattern: DatePattern,
  fromDate: Date,
  endDate: Date
): Date[] {
  const dates: Date[] = [];

  // day が -1 の場合は不定期なので日付計算できない
  if (pattern.day === -1 || pattern.month === -1) {
    return dates;
  }

  const fromYear = fromDate.getFullYear();
  const endYear = endDate.getFullYear();

  if (pattern.type === "monthly") {
    // 毎月の期限
    const day = pattern.day!;
    for (let y = fromYear; y <= endYear; y++) {
      const startMonth = y === fromYear ? fromDate.getMonth() : 0;
      const endMonth = y === endYear ? endDate.getMonth() : 11;
      for (let m = startMonth; m <= endMonth; m++) {
        // 月末日の場合は月の最終日を使用
        const lastDay = new Date(y, m + 1, 0).getDate();
        const actualDay = Math.min(day, lastDay);
        const candidate = new Date(y, m, actualDay);
        if (candidate >= fromDate && candidate <= endDate) {
          dates.push(candidate);
        }
      }
    }
  } else if (pattern.type === "quarterly") {
    // 四半期ごとの期限
    const quarterMonths = [2, 5, 8, 11]; // 3月、6月、9月、12月
    const day = pattern.day!;
    for (let y = fromYear; y <= endYear; y++) {
      for (const m of quarterMonths) {
        const lastDay = new Date(y, m + 1, 0).getDate();
        const actualDay = Math.min(day, lastDay);
        const candidate = new Date(y, m, actualDay);
        if (candidate >= fromDate && candidate <= endDate) {
          dates.push(candidate);
        }
      }
    }
  } else {
    // annual の場合
    const month = pattern.month! - 1; // 0-indexed
    const day = pattern.day!;
    for (let y = fromYear; y <= endYear; y++) {
      const lastDay = new Date(y, month + 1, 0).getDate();
      const actualDay = Math.min(day, lastDay);
      const candidate = new Date(y, month, actualDay);
      if (candidate >= fromDate && candidate <= endDate) {
        dates.push(candidate);
      }
    }
  }

  return dates;
}

/**
 * Date を YYYY-MM-DD 形式の文字列にフォーマットする。
 */
function formatDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/**
 * キーワードで deadline を検索する。
 */
function searchDeadlines(
  query: string,
  targetFilter?: string,
  categoryFilter?: string,
  regionFilter?: string
): Deadline[] {
  const q = query.toLowerCase();

  return deadlines.filter((dl) => {
    // テキスト検索
    if (q) {
      const searchable = [
        dl.name,
        dl.category,
        dl.description,
        dl.target,
        dl.penalty_for_missing,
        ...dl.keywords,
        dl.date_pattern.note,
      ]
        .join(" ")
        .toLowerCase();
      if (!searchable.includes(q)) return false;
    }

    // フィルタ適用
    if (targetFilter && targetFilter !== "all") {
      if (dl.target !== "both" && dl.target !== targetFilter) return false;
    }
    if (categoryFilter && dl.category !== categoryFilter) return false;
    if (regionFilter && !dl.regions.some((r) => r.includes(regionFilter)))
      return false;

    return true;
  });
}

/**
 * カテゴリ一覧を取得する。
 */
function getCategories(): { category: string; count: number }[] {
  const map = new Map<string, number>();
  for (const dl of deadlines) {
    map.set(dl.category, (map.get(dl.category) || 0) + 1);
  }
  return Array.from(map.entries())
    .map(([category, count]) => ({ category, count }))
    .sort((a, b) => b.count - a.count);
}

/**
 * 緊急度を判定する。
 */
function getUrgencyLevel(daysUntil: number): string {
  if (daysUntil < 0) return "期限超過";
  if (daysUntil === 0) return "本日期限";
  if (daysUntil <= 3) return "至急";
  if (daysUntil <= 7) return "要注意";
  if (daysUntil <= 14) return "2週間以内";
  if (daysUntil <= 30) return "1ヶ月以内";
  return "余裕あり";
}

/**
 * 緊急度に応じた優先度スコアを返す。
 */
function getUrgencyScore(daysUntil: number): number {
  if (daysUntil < 0) return 100;
  if (daysUntil === 0) return 95;
  if (daysUntil <= 3) return 90;
  if (daysUntil <= 7) return 80;
  if (daysUntil <= 14) return 60;
  if (daysUntil <= 30) return 40;
  return 20;
}

// ─────────────────────────────────────────────────────────────
// 無料エンドポイント
// ─────────────────────────────────────────────────────────────

app.get("/health", (c) =>
  c.json({
    ok: true,
    service: "jp-tax-calendar-mcp",
    version: "0.1.0",
    time: new Date().toISOString(),
  })
);

app.get("/info", (c) =>
  c.json({
    name: "jp-tax-calendar-mcp",
    version: "0.1.0",
    description_ja:
      "日本の税務・届出・補助金・経理・季節行事の期限カレンダーを提供する MCP サーバー。x402 で有料ゲート済み。",
    deadlines_count: deadlines.length,
    categories: getCategories(),
    last_updated: calendarData._meta.last_updated,
    source: calendarData._meta.source,
    disclaimer: calendarData._meta.disclaimer,
    pricing: {
      "/search": "$0.03 USDC per request",
      "/upcoming": "$0.05 USDC per request",
      "/detail": "$0.02 USDC per request",
      "/mcp": "$0.03 USDC per request",
    },
    endpoints_free: ["/", "/health", "/info", "/free/next"],
    endpoints_paid: ["/search", "/upcoming", "/detail", "/mcp"],
  })
);

app.get("/free/next", (c) => {
  const now = new Date();
  const upcoming = getUpcomingDeadlines(now, 30);

  if (upcoming.length === 0) {
    return c.json({
      message_ja: "30日以内に期限のある項目はありません。",
      total_deadlines: deadlines.length,
      upgrade_message_ja:
        "全件検索やカスタム期間指定には x402 決済が必要です。/search または /upcoming エンドポイントをご利用ください。",
    });
  }

  const next = upcoming[0];
  return c.json({
    next_deadline: {
      id: next.id,
      name: next.name,
      category: next.category,
      next_date: next.next_date,
      days_until: next.days_until,
      urgency: getUrgencyLevel(next.days_until),
      target: next.target,
    },
    upcoming_count: upcoming.length,
    total_deadlines: deadlines.length,
    upgrade_message_ja:
      "全件表示やカスタム検索には x402 決済（$0.03〜$0.05 USDC）が必要です。/upcoming エンドポイントをご利用ください。",
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
    path === "/free/next"
  ) {
    return next();
  }

  const middleware = paymentMiddleware(
    c.env.SERVER_ADDRESS as `0x${string}`,
    {
      "/search": {
        price: `$${c.env.X402_PRICE_SEARCH}`,
        network: c.env.X402_NETWORK,
        config: { description: "Search Japanese tax/business deadlines by keyword" },
      },
      "/upcoming": {
        price: `$${c.env.X402_PRICE_UPCOMING}`,
        network: c.env.X402_NETWORK,
        config: { description: "Get upcoming deadlines within N days" },
      },
      "/detail": {
        price: `$${c.env.X402_PRICE_DETAIL}`,
        network: c.env.X402_NETWORK,
        config: { description: "Get detail of one deadline" },
      },
      "/mcp": {
        price: `$${c.env.X402_PRICE_MCP}`,
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
// 有料エンドポイント: /search
// キーワード検索（$0.03 USDC / req）
// ─────────────────────────────────────────────────────────────

app.post("/search", async (c) => {
  const body = await c.req.json().catch(() => ({} as any));
  const query: string = (body.query || "").toString();
  const target: string | undefined = body.target;
  const category: string | undefined = body.category;
  const region: string | undefined = body.region;

  if (!query && !target && !category && !region) {
    return c.json({
      error: "検索条件を指定してください。query, target, category, region のいずれかが必要です。",
      available_categories: getCategories().map((c) => c.category),
      available_targets: ["個人事業主", "法人", "both"],
    }, 400);
  }

  const results = searchDeadlines(query, target, category, region);

  // 次回の期限日を付与
  const now = new Date();
  const endDate = new Date(now.getTime() + 365 * 24 * 60 * 60 * 1000);
  const enriched = results.map((dl) => {
    const nextDates = getNextDates(dl.date_pattern, now, endDate);
    const nextDate = nextDates.length > 0 ? nextDates[0] : null;
    const daysUntil = nextDate
      ? Math.ceil((nextDate.getTime() - now.getTime()) / (24 * 60 * 60 * 1000))
      : null;

    return {
      ...dl,
      next_date: nextDate ? formatDate(nextDate) : "不定期",
      days_until: daysUntil,
      urgency: daysUntil !== null ? getUrgencyLevel(daysUntil) : "要確認",
    };
  });

  // 期限が近い順にソート（不定期は末尾）
  enriched.sort((a, b) => {
    if (a.days_until === null && b.days_until === null) return 0;
    if (a.days_until === null) return 1;
    if (b.days_until === null) return -1;
    return a.days_until - b.days_until;
  });

  return c.json({
    query,
    filters: { target, category, region },
    count: enriched.length,
    results: enriched.slice(0, 20),
    categories: getCategories(),
  });
});

// ─────────────────────────────────────────────────────────────
// 有料エンドポイント: /upcoming
// N日以内の期限一覧（$0.05 USDC / req）
// ─────────────────────────────────────────────────────────────

app.post("/upcoming", async (c) => {
  const body = await c.req.json().catch(() => ({} as any));
  const days: number = Math.min(Math.max(Number(body.days) || 30, 1), 365);
  const target: string | undefined = body.target;
  const category: string | undefined = body.category;
  const region: string | undefined = body.region;
  const fromDateStr: string | undefined = body.from_date;

  // 基準日の設定
  let fromDate: Date;
  if (fromDateStr) {
    const parsed = new Date(fromDateStr);
    fromDate = isNaN(parsed.getTime()) ? new Date() : parsed;
  } else {
    fromDate = new Date();
  }

  const upcoming = getUpcomingDeadlines(fromDate, days, target, category, region);

  // 緊急度別のサマリーを生成
  const urgencySummary = {
    overdue: upcoming.filter((u) => u.days_until < 0).length,
    today: upcoming.filter((u) => u.days_until === 0).length,
    within_3_days: upcoming.filter((u) => u.days_until > 0 && u.days_until <= 3).length,
    within_7_days: upcoming.filter((u) => u.days_until > 3 && u.days_until <= 7).length,
    within_14_days: upcoming.filter((u) => u.days_until > 7 && u.days_until <= 14).length,
    within_30_days: upcoming.filter((u) => u.days_until > 14 && u.days_until <= 30).length,
    later: upcoming.filter((u) => u.days_until > 30).length,
  };

  // カテゴリ別集計
  const categoryBreakdown = new Map<string, number>();
  for (const u of upcoming) {
    categoryBreakdown.set(u.category, (categoryBreakdown.get(u.category) || 0) + 1);
  }

  const enriched = upcoming.map((u) => ({
    id: u.id,
    name: u.name,
    category: u.category,
    next_date: u.next_date,
    days_until: u.days_until,
    urgency: getUrgencyLevel(u.days_until),
    urgency_score: getUrgencyScore(u.days_until),
    target: u.target,
    penalty_for_missing: u.penalty_for_missing,
    date_note: u.date_pattern.note,
  }));

  return c.json({
    from_date: formatDate(fromDate),
    within_days: days,
    filters: { target, category, region },
    count: enriched.length,
    urgency_summary: urgencySummary,
    category_breakdown: Object.fromEntries(categoryBreakdown),
    results: enriched,
  });
});

// ─────────────────────────────────────────────────────────────
// 有料エンドポイント: /detail
// 1件の詳細取得（$0.02 USDC / req）
// ─────────────────────────────────────────────────────────────

app.post("/detail", async (c) => {
  const body = await c.req.json().catch(() => ({} as any));
  const id: string = body.id || "";
  const found = deadlines.find((dl) => dl.id === id);

  if (!found) {
    return c.json(
      {
        error: "not found",
        id,
        available_ids: deadlines.map((dl) => ({ id: dl.id, name: dl.name })),
      },
      404
    );
  }

  // 次回の期限日を計算
  const now = new Date();
  const endDate = new Date(now.getTime() + 365 * 24 * 60 * 60 * 1000);
  const nextDates = getNextDates(found.date_pattern, now, endDate);
  const nextDate = nextDates.length > 0 ? nextDates[0] : null;
  const daysUntil = nextDate
    ? Math.ceil((nextDate.getTime() - now.getTime()) / (24 * 60 * 60 * 1000))
    : null;

  // 関連する deadline を検索
  const relatedKeywords = found.keywords.slice(0, 3);
  const related = deadlines
    .filter((dl) => {
      if (dl.id === found.id) return false;
      return dl.keywords.some((k) =>
        relatedKeywords.some((rk) => k.includes(rk) || rk.includes(k))
      );
    })
    .slice(0, 5)
    .map((dl) => ({ id: dl.id, name: dl.name, category: dl.category }));

  return c.json({
    ...found,
    next_date: nextDate ? formatDate(nextDate) : "不定期",
    days_until: daysUntil,
    urgency: daysUntil !== null ? getUrgencyLevel(daysUntil) : "要確認",
    upcoming_dates: nextDates.slice(0, 5).map((d) => formatDate(d)),
    related_deadlines: related,
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
        serverInfo: { name: "jp-tax-calendar-mcp", version: "0.1.0" },
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
            name: "search_deadlines",
            description:
              "日本の税務・届出・補助金・経理の期限をキーワード検索する。カテゴリ（税務/届出/補助金/季節行事/経理）、対象者（個人事業主/法人/both）、地域でフィルタ可能。",
            inputSchema: {
              type: "object",
              properties: {
                query: {
                  type: "string",
                  description: "検索キーワード（例：確定申告、インボイス、源泉徴収）",
                },
                target: {
                  type: "string",
                  description: "対象者フィルタ",
                  enum: ["個人事業主", "法人", "both", "all"],
                },
                category: {
                  type: "string",
                  description: "カテゴリフィルタ",
                  enum: ["税務", "届出", "補助金", "季節行事", "経理"],
                },
                region: {
                  type: "string",
                  description: "地域フィルタ（例：全国、富山県）",
                },
              },
            },
          },
          {
            name: "get_upcoming",
            description:
              "指定日から N 日以内に期限が到来する税務・届出・経理イベントの一覧を取得する。緊急度付き。",
            inputSchema: {
              type: "object",
              properties: {
                days: {
                  type: "number",
                  description: "何日以内の期限を取得するか（デフォルト: 30、最大: 365）",
                },
                from_date: {
                  type: "string",
                  description: "基準日（YYYY-MM-DD形式、デフォルト: 今日）",
                },
                target: {
                  type: "string",
                  description: "対象者フィルタ",
                  enum: ["個人事業主", "法人", "both", "all"],
                },
                category: {
                  type: "string",
                  description: "カテゴリフィルタ",
                  enum: ["税務", "届出", "補助金", "季節行事", "経理"],
                },
                region: {
                  type: "string",
                  description: "地域フィルタ",
                },
              },
            },
          },
          {
            name: "get_deadline_detail",
            description:
              "1件の期限の詳細情報を取得する。次回期限日、ペナルティ、関連する期限なども含む。",
            inputSchema: {
              type: "object",
              properties: {
                id: {
                  type: "string",
                  description: "期限ID（例：kakutei-shinkoku, gensen-choushu-monthly）",
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

    // ─── search_deadlines ───
    if (toolName === "search_deadlines") {
      const q = (args.query || "").toString();
      const results = searchDeadlines(q, args.target, args.category, args.region);

      // 次回期限日を付与
      const now = new Date();
      const endDate = new Date(now.getTime() + 365 * 24 * 60 * 60 * 1000);
      const enriched = results.map((dl) => {
        const nextDates = getNextDates(dl.date_pattern, now, endDate);
        const nextDate = nextDates.length > 0 ? nextDates[0] : null;
        const daysUntil = nextDate
          ? Math.ceil(
              (nextDate.getTime() - now.getTime()) / (24 * 60 * 60 * 1000)
            )
          : null;
        return {
          id: dl.id,
          name: dl.name,
          category: dl.category,
          target: dl.target,
          next_date: nextDate ? formatDate(nextDate) : "不定期",
          days_until: daysUntil,
          urgency: daysUntil !== null ? getUrgencyLevel(daysUntil) : "要確認",
          description: dl.description,
          penalty_for_missing: dl.penalty_for_missing,
        };
      });

      enriched.sort((a, b) => {
        if (a.days_until === null && b.days_until === null) return 0;
        if (a.days_until === null) return 1;
        if (b.days_until === null) return -1;
        return a.days_until - b.days_until;
      });

      return c.json({
        jsonrpc: "2.0",
        id,
        result: {
          content: [
            {
              type: "text",
              text: JSON.stringify(
                {
                  query: q,
                  count: enriched.length,
                  results: enriched.slice(0, 15),
                },
                null,
                2
              ),
            },
          ],
        },
      });
    }

    // ─── get_upcoming ───
    if (toolName === "get_upcoming") {
      const days = Math.min(Math.max(Number(args.days) || 30, 1), 365);
      let fromDate: Date;
      if (args.from_date) {
        const parsed = new Date(args.from_date);
        fromDate = isNaN(parsed.getTime()) ? new Date() : parsed;
      } else {
        fromDate = new Date();
      }

      const upcoming = getUpcomingDeadlines(
        fromDate,
        days,
        args.target,
        args.category,
        args.region
      );

      const enriched = upcoming.map((u) => ({
        id: u.id,
        name: u.name,
        category: u.category,
        next_date: u.next_date,
        days_until: u.days_until,
        urgency: getUrgencyLevel(u.days_until),
        target: u.target,
        penalty_for_missing: u.penalty_for_missing,
      }));

      // 緊急度サマリー
      const urgentCount = enriched.filter(
        (e) => e.urgency === "至急" || e.urgency === "本日期限" || e.urgency === "期限超過"
      ).length;

      return c.json({
        jsonrpc: "2.0",
        id,
        result: {
          content: [
            {
              type: "text",
              text: JSON.stringify(
                {
                  from_date: formatDate(fromDate),
                  within_days: days,
                  count: enriched.length,
                  urgent_count: urgentCount,
                  results: enriched,
                },
                null,
                2
              ),
            },
          ],
        },
      });
    }

    // ─── get_deadline_detail ───
    if (toolName === "get_deadline_detail") {
      const found = deadlines.find((dl) => dl.id === args.id);
      if (!found) {
        return c.json({
          jsonrpc: "2.0",
          id,
          error: {
            code: -32602,
            message: `期限が見つかりません: ${args.id}`,
            data: {
              available_ids: deadlines.map((dl) => dl.id),
            },
          },
        });
      }

      // 次回期限日を計算
      const now = new Date();
      const endDate = new Date(now.getTime() + 365 * 24 * 60 * 60 * 1000);
      const nextDates = getNextDates(found.date_pattern, now, endDate);
      const nextDate = nextDates.length > 0 ? nextDates[0] : null;
      const daysUntil = nextDate
        ? Math.ceil(
            (nextDate.getTime() - now.getTime()) / (24 * 60 * 60 * 1000)
          )
        : null;

      // 関連する deadline を検索
      const relatedKeywords = found.keywords.slice(0, 3);
      const related = deadlines
        .filter((dl) => {
          if (dl.id === found.id) return false;
          return dl.keywords.some((k) =>
            relatedKeywords.some((rk) => k.includes(rk) || rk.includes(k))
          );
        })
        .slice(0, 5)
        .map((dl) => ({ id: dl.id, name: dl.name, category: dl.category }));

      return c.json({
        jsonrpc: "2.0",
        id,
        result: {
          content: [
            {
              type: "text",
              text: JSON.stringify(
                {
                  ...found,
                  next_date: nextDate ? formatDate(nextDate) : "不定期",
                  days_until: daysUntil,
                  urgency:
                    daysUntil !== null
                      ? getUrgencyLevel(daysUntil)
                      : "要確認",
                  upcoming_dates: nextDates
                    .slice(0, 5)
                    .map((d) => formatDate(d)),
                  related_deadlines: related,
                },
                null,
                2
              ),
            },
          ],
        },
      });
    }

    // ─── unknown tool ───
    return c.json({
      jsonrpc: "2.0",
      id,
      error: {
        code: -32601,
        message: `不明なツール: ${toolName}`,
        data: {
          available_tools: [
            "search_deadlines",
            "get_upcoming",
            "get_deadline_detail",
          ],
        },
      },
    });
  }

  // ─── unknown method ───
  return c.json({
    jsonrpc: "2.0",
    id,
    error: {
      code: -32601,
      message: `不明なメソッド: ${method}`,
      data: {
        available_methods: [
          "initialize",
          "tools/list",
          "tools/call",
        ],
      },
    },
  });
});

// ─────────────────────────────────────────────────────────────
// ランディングページ
// ─────────────────────────────────────────────────────────────

app.get("/", (c) => {
  const origin = new URL(c.req.url).origin;
  const categories = getCategories();
  const now = new Date();
  const upcoming = getUpcomingDeadlines(now, 30);
  const urgentCount = upcoming.filter(
    (u) => u.days_until <= 7
  ).length;

  return c.html(`<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>jp-tax-calendar-mcp — 日本の税務・届出カレンダー</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", sans-serif; max-width: 720px; margin: 40px auto; padding: 20px; color: #24292f; line-height: 1.7; }
  code { background: #f6f8fa; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }
  pre { background: #0d1117; color: #c9d1d9; padding: 16px; border-radius: 8px; overflow-x: auto; }
  h1 { border-bottom: 1px solid #e1e4e8; padding-bottom: 8px; }
  h2 { color: #0969da; margin-top: 32px; }
  a { color: #0969da; }
  .badge { display: inline-block; background: #1f883d; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; }
  .badge-warn { display: inline-block; background: #d1242f; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; }
  .category-list { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; }
  .category-tag { background: #ddf4ff; color: #0969da; padding: 4px 12px; border-radius: 16px; font-size: 0.85em; }
  table { border-collapse: collapse; width: 100%; margin: 16px 0; }
  th, td { border: 1px solid #d0d7de; padding: 8px 12px; text-align: left; font-size: 0.9em; }
  th { background: #f6f8fa; }
</style>
</head>
<body>
<h1>jp-tax-calendar-mcp</h1>
<p><span class="badge">x402 対応</span>${urgentCount > 0 ? ` <span class="badge-warn">${urgentCount}件が7日以内に期限</span>` : ""} 日本の税務・届出・補助金・経理の期限カレンダーを AI エージェントに提供する MCP サーバー。${deadlines.length} 件の期限情報を収録。</p>

<h2>カテゴリ</h2>
<div class="category-list">
${categories.map((cat) => `  <span class="category-tag">${cat.category}（${cat.count}件）</span>`).join("\n")}
</div>

<h2>料金</h2>
<table>
<tr><th>エンドポイント</th><th>料金</th><th>説明</th></tr>
<tr><td><code>/search</code></td><td>$0.03 USDC</td><td>キーワード検索</td></tr>
<tr><td><code>/upcoming</code></td><td>$0.05 USDC</td><td>N日以内の期限一覧</td></tr>
<tr><td><code>/detail</code></td><td>$0.02 USDC</td><td>1件の詳細取得</td></tr>
<tr><td><code>/mcp</code></td><td>$0.03 USDC</td><td>MCP JSON-RPC</td></tr>
</table>
<p>支払いは x402 protocol 経由で自動決済（Base / Solana、2秒・手数料ほぼゼロ）</p>

<h2>無料で試す</h2>
<pre>curl ${origin}/info
curl ${origin}/free/next</pre>

<h2>有料エンドポイントの使い方</h2>
<pre># キーワード検索
curl -X POST ${origin}/search \\
  -H 'Content-Type: application/json' \\
  -d '{"query":"確定申告","target":"個人事業主"}'

# 30日以内の期限一覧
curl -X POST ${origin}/upcoming \\
  -H 'Content-Type: application/json' \\
  -d '{"days":30,"target":"個人事業主"}'

# 1件の詳細取得
curl -X POST ${origin}/detail \\
  -H 'Content-Type: application/json' \\
  -d '{"id":"kakutei-shinkoku"}'</pre>

<h2>Claude Desktop 設定例</h2>
<pre>{
  "mcpServers": {
    "jp-tax-calendar": { "url": "${origin}/mcp" }
  }
}</pre>

<h2>ユースケース</h2>
<ul>
  <li>フリーランスが「今月中にやるべき税務手続きは？」と Claude に質問 → 期限一覧を自動取得</li>
  <li>経理担当者が「源泉徴収の期限はいつ？遅れたらどうなる？」→ 詳細情報を取得</li>
  <li>AI エージェントが毎月の経理タスクリマインダーを自動生成</li>
  <li>補助金の公募期間を自動チェックし、申請タイミングを逃さない</li>
</ul>

<p><small>この情報は公開情報の要約です。正式な届出・申告前に必ず税理士または各制度の公式サイトで最新情報を確認してください。</small></p>
<p><small>Built and maintained by an autonomous AI company based in Toyama, Japan.</small></p>
</body>
</html>`);
});

export default app;
