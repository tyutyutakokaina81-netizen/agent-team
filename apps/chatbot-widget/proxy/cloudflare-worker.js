/**
 * Cloudflare Worker — チャットボット用 最小プロキシ（APIキーをサーバ側に隠す）
 * 無料枠で動く（1日10万リクエストまで無料）。ゼロ予算で本番運用可。
 *
 * 役割: ブラウザのチャットウィジェットから来る {messages, model} を受け、
 *       サーバ側に隠したAPIキーで OpenAI互換APIを叩いて {reply} を返す。
 *       → ブラウザにAPIキーを置かなくてよい＝不特定多数に公開しても安全。
 *
 * デプロイ手順（クライアントのCloudflareアカウントで・無料）:
 *  1. dash.cloudflare.com → Workers & Pages → Create → Worker
 *  2. このコードを貼り付けてデプロイ
 *  3. Settings → Variables and Secrets → Secret を追加:
 *       OPENAI_API_KEY = sk-...           (必須)
 *       ALLOW_ORIGIN   = https://your-site.com   (任意・推奨。未設定なら * )
 *  4. 発行されたURL（https://xxx.workers.dev）を、ウィジェットの proxyUrl に設定:
 *       window.CHATBOT_CONFIG = { proxyUrl: "https://xxx.workers.dev", model:"gpt-4o-mini", ... }
 *
 * これでブラウザ側にキー不要。OpenAI以外のOpenAI互換API（Azure/own-host等）にも ENDPOINT で対応。
 */
export default {
  async fetch(request, env) {
    const origin = env.ALLOW_ORIGIN || "*";
    const cors = {
      "Access-Control-Allow-Origin": origin,
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    };

    if (request.method === "OPTIONS") return new Response(null, { headers: cors });
    if (request.method !== "POST") {
      return new Response(JSON.stringify({ error: "POST only" }), { status: 405, headers: { ...cors, "Content-Type": "application/json" } });
    }

    if (!env.OPENAI_API_KEY) {
      return new Response(JSON.stringify({ error: "Server not configured (missing OPENAI_API_KEY secret)" }), { status: 500, headers: { ...cors, "Content-Type": "application/json" } });
    }

    let payload;
    try { payload = await request.json(); } catch {
      return new Response(JSON.stringify({ error: "invalid JSON" }), { status: 400, headers: { ...cors, "Content-Type": "application/json" } });
    }

    // --- 簡易ガード（濫用・コスト暴走を抑える） ---
    const messages = Array.isArray(payload.messages) ? payload.messages.slice(-16) : [];
    if (!messages.length) {
      return new Response(JSON.stringify({ error: "messages required" }), { status: 400, headers: { ...cors, "Content-Type": "application/json" } });
    }
    const totalChars = messages.reduce((n, m) => n + (m && typeof m.content === "string" ? m.content.length : 0), 0);
    if (totalChars > 8000) {
      return new Response(JSON.stringify({ error: "input too long" }), { status: 413, headers: { ...cors, "Content-Type": "application/json" } });
    }

    const endpoint = env.ENDPOINT || "https://api.openai.com/v1/chat/completions";
    const model = (payload.model || env.MODEL || "gpt-4o-mini");

    try {
      const r = await fetch(endpoint, {
        method: "POST",
        headers: { "Authorization": "Bearer " + env.OPENAI_API_KEY, "Content-Type": "application/json" },
        body: JSON.stringify({ model, messages, temperature: 0.4, max_tokens: 500 }),
      });
      const data = await r.json();
      if (!r.ok) {
        return new Response(JSON.stringify({ error: (data.error && data.error.message) || ("upstream " + r.status) }), { status: 502, headers: { ...cors, "Content-Type": "application/json" } });
      }
      const reply = (data.choices && data.choices[0] && data.choices[0].message && data.choices[0].message.content) || "";
      return new Response(JSON.stringify({ reply }), { headers: { ...cors, "Content-Type": "application/json" } });
    } catch (e) {
      return new Response(JSON.stringify({ error: "proxy error: " + e.message }), { status: 502, headers: { ...cors, "Content-Type": "application/json" } });
    }
  }
};
