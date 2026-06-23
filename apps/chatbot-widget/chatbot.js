/*!
 * chatbot.js — ドロップイン型 LLMチャットボット ウィジェット（依存ゼロ・単一ファイル）
 * AI自動化代行の納品物／デモ用。どのWebページにも <script src="chatbot.js"> で組み込める。
 *
 * 特徴:
 *  - 実際に会話するLLMチャット（OpenAI互換の chat/completions API を呼ぶ）。
 *  - APIキーは「利用者(クライアント)の自前キー」をブラウザのlocalStorageに保存して使う
 *    ＝当社/サイト運営側にAPIコストが発生しない。キーはそのブラウザ内のみ（外部送信しない）。
 *  - キー未設定でも動く「台本フォールバック」つき（FAQに答え、設定を促す）。
 *  - system プロンプト・初期メッセージ・色・モデルを window.CHATBOT_CONFIG で差し替え可能。
 *
 * ⚠️ セキュリティの正直な注意:
 *   ブラウザにAPIキーを置く方式は「自分用／社内用／小規模」向け。
 *   不特定多数に公開する本番では、キーは必ずサーバ側(プロキシ)に置くこと（キー露出防止）。
 *   本ウィジェットは config.proxyUrl を指定すれば、キーなしで自社プロキシ経由にも切替可能。
 *
 * 使い方（最小）:
 *   <script>
 *     window.CHATBOT_CONFIG = {
 *       title: "AI自動化サポート",
 *       system: "あなたは○○の問い合わせ対応アシスタント。丁寧に、断定せず、最終確認は人が行う前提で答える。",
 *       greeting: "こんにちは！ご質問どうぞ🤖",
 *       model: "gpt-4o-mini",            // OpenAI互換モデル名
 *       endpoint: "https://api.openai.com/v1/chat/completions", // or 互換API
 *       // proxyUrl: "https://your-server/chat"  // ← これを使えばブラウザにキー不要
 *     };
 *   </script>
 *   <script src="chatbot.js"></script>
 */
(function () {
  var C = Object.assign({
    title: "AIアシスタント",
    system: "あなたは丁寧なカスタマーサポートのアシスタントです。簡潔に、わかりやすく答えます。断定を避け、専門的な判断は人が確認する前提で答えてください。",
    greeting: "こんにちは！ご質問をどうぞ。",
    model: "gpt-4o-mini",
    endpoint: "https://api.openai.com/v1/chat/completions",
    proxyUrl: null,
    accent: "#2f6df0",
    maxTurns: 12
  }, window.CHATBOT_CONFIG || {});

  var LSKEY = "chatbot_api_key";
  var history = [{ role: "system", content: C.system }];

  // ---- スタイル ----
  var css = `
  .lcb-btn{position:fixed;right:18px;bottom:18px;z-index:2147483000;background:${C.accent};color:#fff;border:none;border-radius:50px;padding:14px 20px;font:600 15px/1 -apple-system,sans-serif;box-shadow:0 8px 24px rgba(0,0,0,.25);cursor:pointer}
  .lcb-panel{position:fixed;right:18px;bottom:78px;z-index:2147483000;width:350px;max-width:calc(100vw - 36px);height:500px;max-height:calc(100vh - 110px);background:#fff;border-radius:16px;box-shadow:0 16px 48px rgba(0,0,0,.22);display:none;flex-direction:column;overflow:hidden;font-family:-apple-system,sans-serif}
  .lcb-panel.open{display:flex}
  .lcb-head{background:${C.accent};color:#fff;padding:13px 16px;font-weight:700;display:flex;justify-content:space-between;align-items:center;font-size:15px}
  .lcb-head button{background:none;border:none;color:#fff;font-size:20px;cursor:pointer}
  .lcb-body{flex:1;overflow-y:auto;padding:14px;background:#f5f7fa}
  .lcb-m{margin:8px 0;display:flex}.lcb-m .b{max-width:84%;padding:9px 13px;border-radius:13px;font-size:14px;line-height:1.6;white-space:pre-wrap}
  .lcb-bot .b{background:#fff;border:1px solid #e4e8ee;border-bottom-left-radius:4px}
  .lcb-me{justify-content:flex-end}.lcb-me .b{background:${C.accent};color:#fff;border-bottom-right-radius:4px}
  .lcb-in{display:flex;border-top:1px solid #e4e8ee}
  .lcb-in input{flex:1;border:none;padding:12px 14px;font-size:14px;outline:none}
  .lcb-in button{background:${C.accent};color:#fff;border:none;padding:0 16px;font-weight:700;cursor:pointer}
  .lcb-cfg{font-size:12px;color:#5b6470;padding:8px 14px;background:#fffbe6;border-top:1px solid #f0e6b0}
  .lcb-cfg a{color:${C.accent};cursor:pointer;text-decoration:underline}
  `;
  var st = document.createElement("style"); st.textContent = css; document.head.appendChild(st);

  // ---- DOM ----
  var btn = document.createElement("button"); btn.className = "lcb-btn"; btn.textContent = "💬 " + (C.buttonLabel || "AIに質問");
  var panel = document.createElement("div"); panel.className = "lcb-panel";
  panel.innerHTML =
    '<div class="lcb-head"><span>' + esc(C.title) + '</span><button aria-label="close">×</button></div>' +
    '<div class="lcb-body"></div>' +
    '<div class="lcb-cfg" style="display:none"></div>' +
    '<div class="lcb-in"><input placeholder="メッセージを入力…"><button>送信</button></div>';
  document.body.appendChild(btn); document.body.appendChild(panel);

  var body = panel.querySelector(".lcb-body");
  var input = panel.querySelector(".lcb-in input");
  var sendBtn = panel.querySelector(".lcb-in button");
  var cfgBar = panel.querySelector(".lcb-cfg");

  function esc(s){var d=document.createElement("div");d.textContent=s;return d.innerHTML;}
  function add(role, text){
    var d = document.createElement("div"); d.className = "lcb-m " + (role === "user" ? "lcb-me" : "lcb-bot");
    var b = document.createElement("div"); b.className = "b"; b.textContent = text; d.appendChild(b);
    body.appendChild(d); body.scrollTop = body.scrollHeight; return b;
  }
  function hasKey(){ return C.proxyUrl || localStorage.getItem(LSKEY); }

  function showKeyPrompt(){
    cfgBar.style.display = "block";
    cfgBar.innerHTML = 'LLM未接続です。<a>APIキーを設定</a>すると実際の会話になります（キーはこの端末内のみ保存）。';
    cfgBar.querySelector("a").onclick = function(){
      var k = prompt("OpenAI互換のAPIキーを貼り付け（この端末のブラウザにのみ保存されます）:");
      if (k) { localStorage.setItem(LSKEY, k.trim()); cfgBar.style.display = "none"; add("bot", "接続しました。どうぞお話しください。"); }
    };
  }

  // ---- 台本フォールバック（キーなしでも最低限会話） ----
  function scripted(t){
    var s = t.toLowerCase();
    if (/(料金|価格|いくら|cost|price)/.test(s)) return "料金は内容により異なります。詳しくは担当よりご案内します。";
    if (/(サンプル|無料|試|demo|sample)/.test(s)) return "無料サンプルをご用意できます。お問い合わせください。";
    return "ご質問ありがとうございます。担当が確認のうえお答えします（※AIキー設定で、その場で会話できます）。";
  }

  async function ask(text){
    history.push({ role: "user", content: text });
    if (history.length > C.maxTurns * 2) history = [history[0]].concat(history.slice(-C.maxTurns * 2 + 1));
    var thinking = add("bot", "…");
    try {
      var res, data;
      if (C.proxyUrl) {
        res = await fetch(C.proxyUrl, { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({ messages: history, model: C.model }) });
        data = await res.json();
      } else {
        var key = localStorage.getItem(LSKEY);
        if (!key) { thinking.textContent = scripted(text); showKeyPrompt(); return; }
        res = await fetch(C.endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": "Bearer " + key },
          body: JSON.stringify({ model: C.model, messages: history, temperature: 0.4 })
        });
        data = await res.json();
      }
      if (!res.ok) throw new Error((data && data.error && data.error.message) || ("HTTP " + res.status));
      var reply = (data.choices && data.choices[0] && (data.choices[0].message ? data.choices[0].message.content : data.choices[0].text)) || (data.reply) || "(応答なし)";
      thinking.textContent = reply.trim();
      history.push({ role: "assistant", content: reply.trim() });
    } catch (e) {
      thinking.textContent = "⚠️ 応答に失敗しました（" + e.message + "）。キーやネット接続をご確認ください。";
    }
  }

  function send(){
    var v = input.value.trim(); if (!v) return;
    add("user", v); input.value = ""; ask(v);
  }
  sendBtn.onclick = send;
  input.addEventListener("keydown", function(e){ if (e.key === "Enter") send(); });
  panel.querySelector(".lcb-head button").onclick = function(){ panel.classList.remove("open"); };
  btn.onclick = function(){
    panel.classList.toggle("open");
    if (panel.classList.contains("open") && !body.hasChildNodes()){
      add("bot", C.greeting);
      if (!hasKey()) showKeyPrompt();
    }
  };
})();
