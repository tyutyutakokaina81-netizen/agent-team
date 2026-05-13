// jp-keigo-checker-mcp / src/index.ts
//
// Cloudflare Workers で動く、日本語ビジネス敬語チェック・変換 MCP サーバー。
// x402 payment middleware で有料アクセスを USDC で自動決済する。
//
// 無料エンドポイント（広告・獲得目的）:
//   GET  /           - HTML ランディングページ
//   GET  /health     - ヘルスチェック
//   GET  /info       - サーバーメタ情報
//   GET  /free/rule  - 敬語ルール1件だけランダム表示
//
// 有料エンドポイント（x402 支払い必須）:
//   POST /check      - テキストの敬語エラーを分析（$0.05 USDC / req）
//   POST /convert    - カジュアル文を敬語に変換（$0.08 USDC / req）
//   POST /template   - ビジネスメールテンプレートを取得（$0.03 USDC / req）
//   POST /mcp        - MCP JSON-RPC エンドポイント（$0.05 USDC / req）

import { Hono } from "hono";
import { paymentMiddleware } from "x402-hono";
import keigoData from "../data/keigo_rules.json";
import emailData from "../data/email_templates.json";

// ─────────────────────────────────────────────────────────────
// 型定義
// ─────────────────────────────────────────────────────────────

type Bindings = {
  X402_NETWORK: string;
  X402_PRICE_CHECK: string;
  X402_PRICE_CONVERT: string;
  X402_PRICE_TEMPLATE: string;
  X402_CURRENCY: string;
  X402_FACILITATOR: string;
  SERVER_ADDRESS: string;
};

type KeigoRule = {
  id: string;
  casual_form: string;
  keigo_form: string;
  category: string;
  context: string[];
  example_sentence_casual: string;
  example_sentence_keigo: string;
  common_mistakes: string[];
  difficulty: string;
};

type EmailTemplate = {
  id: string;
  name: string;
  category: string;
  subject_template: string;
  body_template: string;
  tone: string;
  keywords: string[];
};

type KeigoIssue = {
  original: string;
  suggestion: string;
  rule_id: string;
  category: string;
  position: number;
  explanation: string;
};

type ConversionResult = {
  original_segment: string;
  converted_segment: string;
  rule_id: string;
  category: string;
};

// ─────────────────────────────────────────────────────────────
// データ読み込み
// ─────────────────────────────────────────────────────────────

const rules = keigoData.rules as KeigoRule[];
const templates = emailData.templates as EmailTemplate[];

const app = new Hono<{ Bindings: Bindings }>();

// ─────────────────────────────────────────────────────────────
// ユーティリティ関数
// ─────────────────────────────────────────────────────────────

/**
 * テキスト内のカジュアル表現を検出し、敬語の問題点を返す
 */
function analyzeKeigoIssues(text: string, contextFilter?: string): KeigoIssue[] {
  const issues: KeigoIssue[] = [];
  const processedPositions = new Set<string>();

  for (const rule of rules) {
    // コンテキストフィルタが指定されている場合、マッチしないルールはスキップ
    if (contextFilter && !rule.context.includes(contextFilter)) {
      continue;
    }

    const casualForm = rule.casual_form;
    let searchStart = 0;

    while (searchStart < text.length) {
      const position = text.indexOf(casualForm, searchStart);
      if (position === -1) break;

      // 同じ位置で同じルールが既に適用されていないか確認
      const posKey = `${position}-${rule.id}`;
      if (!processedPositions.has(posKey)) {
        // 既に敬語形が使われている場合はスキップ
        const keigoForms = rule.keigo_form.split("／");
        const surroundingText = text.substring(
          Math.max(0, position - 10),
          Math.min(text.length, position + casualForm.length + 10)
        );

        let alreadyKeigo = false;
        for (const kf of keigoForms) {
          if (surroundingText.includes(kf.trim())) {
            alreadyKeigo = true;
            break;
          }
        }

        if (!alreadyKeigo) {
          processedPositions.add(posKey);
          issues.push({
            original: casualForm,
            suggestion: rule.keigo_form,
            rule_id: rule.id,
            category: rule.category,
            position,
            explanation: `「${casualForm}」→「${rule.keigo_form}」（${rule.category}）。${rule.common_mistakes[0] || ""}`,
          });
        }
      }

      searchStart = position + casualForm.length;
    }
  }

  // 位置順にソート
  issues.sort((a, b) => a.position - b.position);
  return issues;
}

/**
 * よくあるビジネス敬語の誤りパターンを検出する
 */
function detectCommonMistakes(text: string): KeigoIssue[] {
  const mistakes: KeigoIssue[] = [];

  // 二重敬語の検出パターン
  const doubleHonorificPatterns: Array<{
    pattern: string;
    correct: string;
    explanation: string;
  }> = [
    {
      pattern: "おっしゃられ",
      correct: "おっしゃ",
      explanation: "「おっしゃられる」は二重敬語です。「おっしゃる」が正しい尊敬語です。",
    },
    {
      pattern: "ご覧になられ",
      correct: "ご覧にな",
      explanation: "「ご覧になられる」は二重敬語です。「ご覧になる」が正しい尊敬語です。",
    },
    {
      pattern: "お読みになられ",
      correct: "お読みにな",
      explanation: "「お読みになられる」は二重敬語です。「お読みになる」が正しい尊敬語です。",
    },
    {
      pattern: "お聞きになられ",
      correct: "お聞きにな",
      explanation: "「お聞きになられる」は二重敬語です。「お聞きになる」が正しい尊敬語です。",
    },
    {
      pattern: "拝見させていただ",
      correct: "拝見いたし",
      explanation: "「拝見させていただく」は過剰敬語です。「拝見いたしました」で十分です。",
    },
  ];

  // カジュアルすぎる表現の検出
  const casualPatterns: Array<{
    pattern: string;
    correct: string;
    explanation: string;
  }> = [
    {
      pattern: "了解しました",
      correct: "承知いたしました",
      explanation: "「了解しました」はビジネスメールでは不適切です。「承知いたしました」を使いましょう。",
    },
    {
      pattern: "了解です",
      correct: "承知いたしました",
      explanation: "「了解です」はビジネスでは不適切です。「承知いたしました」が正しい表現です。",
    },
    {
      pattern: "すみません",
      correct: "申し訳ございません",
      explanation: "ビジネス文書では「すみません」より「申し訳ございません」が適切です。",
    },
    {
      pattern: "ごめんなさい",
      correct: "申し訳ございません",
      explanation: "「ごめんなさい」はビジネス文書には不適切です。「申し訳ございません」を使いましょう。",
    },
    {
      pattern: "ちょっと",
      correct: "少々",
      explanation: "「ちょっと」はカジュアルすぎます。ビジネスでは「少々」を使いましょう。",
    },
    {
      pattern: "どうですか",
      correct: "いかがでしょうか",
      explanation: "「どうですか」はビジネスでは「いかがでしょうか」が適切です。",
    },
    {
      pattern: "できません",
      correct: "いたしかねます",
      explanation: "「できません」は直接的すぎます。「いたしかねます」が丁寧な表現です。",
    },
    {
      pattern: "わかりました",
      correct: "承知いたしました",
      explanation: "ビジネスでは「わかりました」より「承知いたしました」が適切です。",
    },
  ];

  // 間違った敬語の使い方を検出
  const wrongUsagePatterns: Array<{
    pattern: string;
    correct: string;
    explanation: string;
  }> = [
    {
      pattern: "ご教授ください",
      correct: "ご教示ください",
      explanation: "ビジネスの一般的な質問には「ご教示」が適切です。「ご教授」は学問的な指導に使います。",
    },
    {
      pattern: "とんでもございません",
      correct: "とんでもないことでございます",
      explanation: "「とんでもございません」は文法的に誤りです。「とんでもないことでございます」が正しい表現です。",
    },
    {
      pattern: "お体ご自愛",
      correct: "ご自愛",
      explanation: "「お体ご自愛ください」は重複表現です。「ご自愛ください」だけで「お体を大切に」の意味があります。",
    },
    {
      pattern: "役不足",
      correct: "力不足",
      explanation: "「役不足」は「自分の実力に対して役目が軽すぎる」意味です。謙遜する場合は「力不足」が正しい。",
    },
  ];

  const allPatterns = [
    ...doubleHonorificPatterns.map((p) => ({ ...p, category: "二重敬語" })),
    ...casualPatterns.map((p) => ({ ...p, category: "カジュアル表現" })),
    ...wrongUsagePatterns.map((p) => ({ ...p, category: "誤用" })),
  ];

  for (const p of allPatterns) {
    let searchStart = 0;
    while (searchStart < text.length) {
      const position = text.indexOf(p.pattern, searchStart);
      if (position === -1) break;

      mistakes.push({
        original: p.pattern,
        suggestion: p.correct,
        rule_id: `mistake-${p.pattern}`,
        category: p.category,
        position,
        explanation: p.explanation,
      });

      searchStart = position + p.pattern.length;
    }
  }

  mistakes.sort((a, b) => a.position - b.position);
  return mistakes;
}

/**
 * テキスト内のカジュアル表現を敬語に変換する
 */
function convertToKeigo(
  text: string,
  contextFilter?: string,
  formalityLevel?: string
): { converted_text: string; conversions: ConversionResult[] } {
  const conversions: ConversionResult[] = [];
  let result = text;

  // ルールを casual_form の長い順にソート（長い表現を先にマッチさせる）
  const sortedRules = [...rules].sort(
    (a, b) => b.casual_form.length - a.casual_form.length
  );

  for (const rule of sortedRules) {
    if (contextFilter && !rule.context.includes(contextFilter)) {
      continue;
    }

    // formalityLevel による難易度フィルタ
    if (formalityLevel === "basic" && rule.difficulty === "advanced") {
      continue;
    }

    const casualForm = rule.casual_form;
    // 複数の敬語形がある場合は最初のものを使用
    const keigoForm = rule.keigo_form.split("／")[0].trim();

    if (result.includes(casualForm)) {
      // 既に敬語形が含まれていない場合のみ変換
      if (!result.includes(keigoForm)) {
        result = result.split(casualForm).join(keigoForm);
        conversions.push({
          original_segment: casualForm,
          converted_segment: keigoForm,
          rule_id: rule.id,
          category: rule.category,
        });
      }
    }
  }

  // 追加のビジネス変換パターン
  const additionalConversions: Array<{
    from: string;
    to: string;
    category: string;
  }> = [
    { from: "了解しました", to: "承知いたしました", category: "ビジネス慣用句" },
    { from: "了解です", to: "承知いたしました", category: "ビジネス慣用句" },
    { from: "ごめんなさい", to: "申し訳ございません", category: "丁寧語" },
    { from: "どうですか", to: "いかがでしょうか", category: "丁寧語" },
    { from: "ちょっと", to: "少々", category: "丁寧語" },
    { from: "できません", to: "いたしかねます", category: "ビジネス慣用句" },
    { from: "わかりました", to: "承知いたしました", category: "謙譲語" },
    { from: "あとで", to: "後ほど", category: "丁寧語" },
    { from: "さっき", to: "先ほど", category: "丁寧語" },
    { from: "今日", to: "本日", category: "丁寧語" },
    { from: "明日", to: "明日（みょうにち）", category: "丁寧語" },
    { from: "昨日", to: "昨日（さくじつ）", category: "丁寧語" },
    { from: "こっち", to: "こちら", category: "丁寧語" },
    { from: "そっち", to: "そちら", category: "丁寧語" },
    { from: "あっち", to: "あちら", category: "丁寧語" },
    { from: "誰", to: "どなた", category: "丁寧語" },
    { from: "どこ", to: "どちら", category: "丁寧語" },
    { from: "いいですか", to: "よろしいでしょうか", category: "丁寧語" },
    { from: "もらえますか", to: "いただけますでしょうか", category: "謙譲語" },
    { from: "してください", to: "していただけますでしょうか", category: "ビジネス慣用句" },
  ];

  for (const ac of additionalConversions) {
    if (result.includes(ac.from)) {
      result = result.split(ac.from).join(ac.to);
      conversions.push({
        original_segment: ac.from,
        converted_segment: ac.to,
        rule_id: `additional-${ac.from}`,
        category: ac.category,
      });
    }
  }

  return { converted_text: result, conversions };
}

/**
 * 敬語レベルのスコアを計算する（0-100）
 */
function calculateKeigoScore(text: string): {
  score: number;
  level: string;
  feedback: string;
} {
  if (!text || text.trim().length === 0) {
    return { score: 0, level: "判定不可", feedback: "テキストが空です。" };
  }

  let score = 100;
  const issues = analyzeKeigoIssues(text);
  const mistakes = detectCommonMistakes(text);

  // カジュアル表現1件につき -10
  score -= issues.length * 10;
  // 敬語ミス1件につき -15
  score -= mistakes.length * 15;

  // 良い敬語表現が使われていれば加点
  const goodPatterns = [
    "いただけますと幸いです",
    "何卒よろしくお願い",
    "お忙しいところ恐れ入りますが",
    "ご確認のほど",
    "申し上げます",
    "ございます",
    "いたします",
    "存じます",
    "承知いたしました",
    "かしこまりました",
  ];

  let goodCount = 0;
  for (const pattern of goodPatterns) {
    if (text.includes(pattern)) {
      goodCount++;
    }
  }
  score += goodCount * 3;

  // スコアを0-100にクランプ
  score = Math.max(0, Math.min(100, score));

  let level: string;
  let feedback: string;

  if (score >= 90) {
    level = "優秀";
    feedback =
      "非常に適切な敬語が使われています。ビジネス文書として問題ありません。";
  } else if (score >= 75) {
    level = "良好";
    feedback =
      "概ね適切な敬語ですが、一部改善の余地があります。";
  } else if (score >= 50) {
    level = "要改善";
    feedback =
      "カジュアルな表現や敬語の誤りがいくつか見られます。重要なビジネス文書の前に修正を推奨します。";
  } else if (score >= 25) {
    level = "不十分";
    feedback =
      "敬語が不十分です。ビジネス文書としては大幅な修正が必要です。";
  } else {
    level = "要全面修正";
    feedback =
      "敬語がほとんど使われていません。ビジネス文書として全面的な書き直しを推奨します。";
  }

  return { score, level, feedback };
}

/**
 * テンプレートを検索する
 */
function searchTemplates(
  query?: string,
  category?: string,
  tone?: string
): EmailTemplate[] {
  return templates.filter((t) => {
    if (category && t.category !== category) return false;
    if (tone && t.tone !== tone) return false;
    if (query) {
      const q = query.toLowerCase();
      const hay = [t.name, t.category, ...t.keywords]
        .join(" ")
        .toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

// ─────────────────────────────────────────────────────────────
// 無料エンドポイント
// ─────────────────────────────────────────────────────────────

app.get("/health", (c) =>
  c.json({
    ok: true,
    service: "jp-keigo-checker-mcp",
    version: "0.1.0",
    time: new Date().toISOString(),
  })
);

app.get("/info", (c) =>
  c.json({
    name: "jp-keigo-checker-mcp",
    version: "0.1.0",
    description_ja:
      "日本語ビジネス敬語のチェック・変換・メールテンプレート生成を行う MCP サーバー。x402 で有料ゲート済み。",
    rules_count: rules.length,
    templates_count: templates.length,
    last_updated: keigoData._meta.last_updated,
    disclaimer: keigoData._meta.disclaimer,
    pricing: {
      "/check": "$0.05 USDC per request",
      "/convert": "$0.08 USDC per request",
      "/template": "$0.03 USDC per request",
      "/mcp": "$0.05 USDC per request",
    },
    endpoints_free: ["/", "/health", "/info", "/free/rule"],
    endpoints_paid: ["/check", "/convert", "/template", "/mcp"],
    categories: {
      keigo: ["尊敬語", "謙譲語", "丁寧語", "ビジネス慣用句"],
      email: ["挨拶", "依頼", "お礼", "お詫び", "報告", "断り"],
    },
  })
);

app.get("/free/rule", (c) => {
  const sample = rules[Math.floor(Math.random() * rules.length)];
  return c.json({
    sample: {
      id: sample.id,
      casual_form: sample.casual_form,
      keigo_form: sample.keigo_form,
      category: sample.category,
      example_sentence_casual: sample.example_sentence_casual,
      example_sentence_keigo: sample.example_sentence_keigo,
    },
    total_rules: rules.length,
    total_templates: templates.length,
    upgrade_message_ja:
      "全ルール検索・敬語チェック・変換には x402 決済が必要です。/check（$0.05）、/convert（$0.08）、/template（$0.03）をご利用ください。",
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
    path === "/free/rule"
  ) {
    return next();
  }

  const middleware = paymentMiddleware(
    c.env.SERVER_ADDRESS as `0x${string}`,
    {
      "/check": {
        price: `$${c.env.X402_PRICE_CHECK}`,
        network: c.env.X402_NETWORK,
        config: { description: "Check Japanese text for keigo issues" },
      },
      "/convert": {
        price: `$${c.env.X402_PRICE_CONVERT}`,
        network: c.env.X402_NETWORK,
        config: { description: "Convert casual Japanese to business keigo" },
      },
      "/template": {
        price: `$${c.env.X402_PRICE_TEMPLATE}`,
        network: c.env.X402_NETWORK,
        config: { description: "Get business email template" },
      },
      "/mcp": {
        price: `$${c.env.X402_PRICE_CHECK}`,
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
// 有料エンドポイント: /check — 敬語チェック
// ─────────────────────────────────────────────────────────────

app.post("/check", async (c) => {
  const body = await c.req.json().catch(() => ({} as any));
  const text: string = (body.text || "").toString();
  const context: string | undefined = body.context;

  if (!text.trim()) {
    return c.json({ error: "text パラメータが必要です。" }, 400);
  }

  const issues = analyzeKeigoIssues(text, context);
  const mistakes = detectCommonMistakes(text);
  const score = calculateKeigoScore(text);

  // 該当するルールの詳細を取得
  const relatedRules = issues
    .map((issue) => rules.find((r) => r.id === issue.rule_id))
    .filter(Boolean)
    .filter(
      (rule, index, self) =>
        self.findIndex((r) => r?.id === rule?.id) === index
    );

  return c.json({
    text,
    context: context || "全般",
    score,
    issues_count: issues.length + mistakes.length,
    keigo_issues: issues,
    common_mistakes: mistakes,
    related_rules: relatedRules.slice(0, 10),
    suggestions_summary:
      issues.length + mistakes.length === 0
        ? "敬語の問題は検出されませんでした。"
        : `${issues.length + mistakes.length}件の改善点が見つかりました。詳細は keigo_issues と common_mistakes を確認してください。`,
  });
});

// ─────────────────────────────────────────────────────────────
// 有料エンドポイント: /convert — 敬語変換
// ─────────────────────────────────────────────────────────────

app.post("/convert", async (c) => {
  const body = await c.req.json().catch(() => ({} as any));
  const text: string = (body.text || "").toString();
  const context: string | undefined = body.context;
  const formality: string = body.formality || "formal";

  if (!text.trim()) {
    return c.json({ error: "text パラメータが必要です。" }, 400);
  }

  const { converted_text, conversions } = convertToKeigo(
    text,
    context,
    formality
  );

  const beforeScore = calculateKeigoScore(text);
  const afterScore = calculateKeigoScore(converted_text);

  return c.json({
    original_text: text,
    converted_text,
    context: context || "全般",
    formality,
    conversions_count: conversions.length,
    conversions,
    score_before: beforeScore,
    score_after: afterScore,
    improvement:
      conversions.length === 0
        ? "変換対象のカジュアル表現は見つかりませんでした。既に適切な敬語が使われている可能性があります。"
        : `${conversions.length}箇所を敬語に変換しました。スコアが ${beforeScore.score} → ${afterScore.score} に改善しました。`,
  });
});

// ─────────────────────────────────────────────────────────────
// 有料エンドポイント: /template — メールテンプレート
// ─────────────────────────────────────────────────────────────

app.post("/template", async (c) => {
  const body = await c.req.json().catch(() => ({} as any));
  const id: string | undefined = body.id;
  const query: string | undefined = body.query;
  const category: string | undefined = body.category;
  const tone: string | undefined = body.tone;

  // ID 指定の場合は1件返す
  if (id) {
    const found = templates.find((t) => t.id === id);
    if (!found) {
      return c.json({ error: "テンプレートが見つかりません。", id }, 404);
    }
    return c.json({
      template: found,
      available_categories: [
        ...new Set(templates.map((t) => t.category)),
      ],
    });
  }

  // 検索
  const results = searchTemplates(query, category, tone);

  return c.json({
    query: query || null,
    category: category || null,
    tone: tone || null,
    count: results.length,
    templates: results,
    available_categories: [...new Set(templates.map((t) => t.category))],
    available_tones: [...new Set(templates.map((t) => t.tone))],
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
        serverInfo: { name: "jp-keigo-checker-mcp", version: "0.1.0" },
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
            name: "check_keigo",
            description:
              "日本語テキストの敬語をチェックする。カジュアル表現の検出、二重敬語の検出、ビジネス敬語のスコアリングを行う。",
            inputSchema: {
              type: "object",
              properties: {
                text: {
                  type: "string",
                  description: "チェック対象のテキスト",
                },
                context: {
                  type: "string",
                  enum: ["メール", "電話", "会議", "文書"],
                  description:
                    "使用コンテキスト。指定すると該当コンテキストのルールのみ適用",
                },
              },
              required: ["text"],
            },
          },
          {
            name: "convert_to_keigo",
            description:
              "カジュアルな日本語テキストをビジネス敬語に変換する。変換前後のスコア比較付き。",
            inputSchema: {
              type: "object",
              properties: {
                text: {
                  type: "string",
                  description: "変換対象のテキスト",
                },
                context: {
                  type: "string",
                  enum: ["メール", "電話", "会議", "文書"],
                  description: "使用コンテキスト",
                },
                formality: {
                  type: "string",
                  enum: ["basic", "formal"],
                  description:
                    "丁寧さのレベル。basic=基本的な丁寧語、formal=完全な敬語",
                },
              },
              required: ["text"],
            },
          },
          {
            name: "get_email_template",
            description:
              "日本語ビジネスメールのテンプレートを取得する。カテゴリ・キーワード検索対応。",
            inputSchema: {
              type: "object",
              properties: {
                id: {
                  type: "string",
                  description: "テンプレートID（直接指定）",
                },
                query: {
                  type: "string",
                  description: "検索キーワード",
                },
                category: {
                  type: "string",
                  enum: [
                    "挨拶",
                    "依頼",
                    "お礼",
                    "お詫び",
                    "報告",
                    "断り",
                  ],
                  description: "テンプレートカテゴリ",
                },
                tone: {
                  type: "string",
                  enum: ["formal", "semi-formal"],
                  description: "メールのトーン",
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

    // check_keigo ツール
    if (toolName === "check_keigo") {
      const text = (args.text || "").toString();
      if (!text.trim()) {
        return c.json({
          jsonrpc: "2.0",
          id,
          error: { code: -32602, message: "text パラメータが必要です。" },
        });
      }

      const issues = analyzeKeigoIssues(text, args.context);
      const mistakes = detectCommonMistakes(text);
      const score = calculateKeigoScore(text);

      const result = {
        text,
        context: args.context || "全般",
        score,
        issues_count: issues.length + mistakes.length,
        keigo_issues: issues,
        common_mistakes: mistakes,
        summary:
          issues.length + mistakes.length === 0
            ? "敬語の問題は検出されませんでした。"
            : `${issues.length + mistakes.length}件の改善点が見つかりました。`,
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

    // convert_to_keigo ツール
    if (toolName === "convert_to_keigo") {
      const text = (args.text || "").toString();
      if (!text.trim()) {
        return c.json({
          jsonrpc: "2.0",
          id,
          error: { code: -32602, message: "text パラメータが必要です。" },
        });
      }

      const { converted_text, conversions } = convertToKeigo(
        text,
        args.context,
        args.formality || "formal"
      );
      const beforeScore = calculateKeigoScore(text);
      const afterScore = calculateKeigoScore(converted_text);

      const result = {
        original_text: text,
        converted_text,
        conversions_count: conversions.length,
        conversions,
        score_before: beforeScore,
        score_after: afterScore,
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

    // get_email_template ツール
    if (toolName === "get_email_template") {
      if (args.id) {
        const found = templates.find((t) => t.id === args.id);
        if (!found) {
          return c.json({
            jsonrpc: "2.0",
            id,
            error: {
              code: -32602,
              message: `テンプレートが見つかりません: ${args.id}`,
            },
          });
        }
        return c.json({
          jsonrpc: "2.0",
          id,
          result: {
            content: [
              { type: "text", text: JSON.stringify(found, null, 2) },
            ],
          },
        });
      }

      const results = searchTemplates(
        args.query,
        args.category,
        args.tone
      );

      return c.json({
        jsonrpc: "2.0",
        id,
        result: {
          content: [
            {
              type: "text",
              text: JSON.stringify(
                { count: results.length, templates: results },
                null,
                2
              ),
            },
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
  return c.html(`<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>jp-keigo-checker-mcp — 日本語ビジネス敬語チェッカー</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", sans-serif; max-width: 720px; margin: 40px auto; padding: 20px; color: #24292f; line-height: 1.7; }
  code { background: #f6f8fa; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }
  pre { background: #0d1117; color: #c9d1d9; padding: 16px; border-radius: 8px; overflow-x: auto; }
  h1 { border-bottom: 1px solid #e1e4e8; padding-bottom: 8px; }
  h2 { color: #0969da; margin-top: 32px; }
  a { color: #0969da; }
  .badge { display: inline-block; background: #1f883d; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; }
  table { border-collapse: collapse; width: 100%; margin: 16px 0; }
  th, td { border: 1px solid #d0d7de; padding: 8px 12px; text-align: left; }
  th { background: #f6f8fa; }
  .example { background: #f0f7ff; border-left: 4px solid #0969da; padding: 12px 16px; margin: 12px 0; border-radius: 0 4px 4px 0; }
  .example-bad { color: #cf222e; }
  .example-good { color: #1a7f37; }
</style>
</head>
<body>
<h1>jp-keigo-checker-mcp</h1>
<p><span class="badge">x402 対応</span> 日本語ビジネス敬語をチェック・変換する MCP サーバー。Claude / OpenAI / その他の AI エージェントから直接呼び出せます。${rules.length}件の敬語ルールと${templates.length}件のメールテンプレートを収録。</p>

<h2>機能</h2>
<table>
  <tr><th>機能</th><th>説明</th></tr>
  <tr><td>敬語チェック</td><td>テキスト内のカジュアル表現・二重敬語・誤用を検出し、100点満点でスコアリング</td></tr>
  <tr><td>敬語変換</td><td>カジュアルな日本語をビジネス敬語に自動変換。変換前後のスコア比較付き</td></tr>
  <tr><td>メールテンプレート</td><td>挨拶・依頼・お礼・お詫び・報告・断りなど、ビジネスメールの雛形を提供</td></tr>
</table>

<h2>使用例</h2>
<div class="example">
  <p class="example-bad">変換前: 「すみません、ちょっと聞きたいことがあるんですが、この件どうですか？わかりました、あとで確認します。」</p>
  <p class="example-good">変換後: 「申し訳ございません、少々お伺いしたいことがあるのですが、この件いかがでしょうか。承知いたしました、後ほど確認いたします。」</p>
</div>

<h2>料金</h2>
<ul>
  <li><code>/check</code> — $0.05 USDC / リクエスト（敬語チェック）</li>
  <li><code>/convert</code> — $0.08 USDC / リクエスト（敬語変換）</li>
  <li><code>/template</code> — $0.03 USDC / リクエスト（メールテンプレート）</li>
  <li>支払いは x402 protocol 経由で自動決済（Base / Solana、2秒・手数料 \\u00A50）</li>
</ul>

<h2>対応カテゴリ</h2>
<table>
  <tr><th>敬語カテゴリ</th><th>メールカテゴリ</th></tr>
  <tr><td>尊敬語・謙譲語・丁寧語・ビジネス慣用句</td><td>挨拶・依頼・お礼・お詫び・報告・断り</td></tr>
</table>

<h2>無料で試す</h2>
<pre>curl ${origin}/info
curl ${origin}/free/rule</pre>

<h2>Claude Desktop 設定例</h2>
<pre>{
  "mcpServers": {
    "jp-keigo": { "url": "${origin}/mcp" }
  }
}</pre>

<h2>API 使用例</h2>
<pre># 敬語チェック
curl -X POST ${origin}/check \\
  -H 'Content-Type: application/json' \\
  -d '{"text":"すみません、ちょっと聞きたいんですが"}'

# 敬語変換
curl -X POST ${origin}/convert \\
  -H 'Content-Type: application/json' \\
  -d '{"text":"了解しました、あとで確認します","context":"メール"}'

# テンプレート取得
curl -X POST ${origin}/template \\
  -H 'Content-Type: application/json' \\
  -d '{"category":"お詫び"}'</pre>

<p><small>この情報は一般的な敬語用法の要約です。業界・組織特有の慣習がある場合は適宜調整してください。</small></p>
<p><small>Built and maintained by an autonomous AI company based in Toyama, Japan.</small></p>
</body>
</html>`);
});

export default app;
