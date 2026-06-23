/**
 * Gmail 自動返信ドラフト — Google Apps Script（無料・Googleのサーバで動く・PC不要）
 *
 * 役割: 受信した問い合わせメールに対し、AIが「返信の下書き」を自動作成してGmailに保存。
 *       あなたは下書きを確認して送るだけ。★送信は必ず人★（AIは下書きまで）。
 *       → 「来た客への返信」という最後の人手を、ほぼ"確認して送るだけ"に軽くする。
 *
 * これは AI自動化代行の納品物にもなる（Gmailユーザー向け「問い合わせ返信の自動化」）。
 *
 * セットアップ（5分・無料）:
 *  1. script.google.com → 新しいプロジェクト → このコードを貼る
 *  2. 左の「プロジェクトの設定」→ スクリプト プロパティ に追加:
 *       OPENAI_API_KEY = sk-...                （必須）
 *       SYSTEM_PROMPT  = （任意・業種別の指示。未設定なら汎用）
 *       WATCH_LABEL    = （任意。例 "要返信"。未設定なら受信トレイの未読を対象）
 *  3. 関数 setupTrigger を1回実行（承認を求められたら許可）→ 15分ごとに自動実行されます
 *  4. 関数 draftReplies を手動実行して動作確認（下書きがGmailにできればOK）
 *
 * 安全:
 *  - 作るのは「下書き」だけ。勝手に送信しません。最終確認・送信は人。
 *  - 一度下書きしたスレッドは "ai-drafted" ラベルを付け、二重作成を防止。
 *  - 機密判断や断定はしない指示を内蔵（誤情報・炎上の抑制）。
 */

function DEFAULT_SYSTEM() {
  return [
    "あなたは事業者の問い合わせ対応アシスタントです。届いた問い合わせメールへの『返信の下書き』を日本語で作成します。",
    "ルール: 丁寧・簡潔・安心感。件名は変えず本文のみ。挨拶→要件の受け止め→次のアクション（面談/見積/必要情報の質問）→結び。",
    "禁止: 料金・可否・成果の断定。わからないことは推測で補わず丁寧に質問する。重要判断は『担当が確認します』に留める。",
    "末尾に『※この下書きは担当者が確認のうえ送信します』と入れる。"
  ].join("\n");
}

function draftReplies() {
  var props = PropertiesService.getScriptProperties();
  var key = props.getProperty("OPENAI_API_KEY");
  if (!key) { Logger.log("OPENAI_API_KEY 未設定"); return; }
  var system = props.getProperty("SYSTEM_PROMPT") || DEFAULT_SYSTEM();
  var watch = props.getProperty("WATCH_LABEL");

  var done = GmailApp.getUserLabelByName("ai-drafted") || GmailApp.createLabel("ai-drafted");
  var query = watch
    ? 'label:"' + watch + '" -label:ai-drafted'
    : 'is:unread in:inbox -label:ai-drafted newer_than:3d';

  var threads = GmailApp.search(query, 0, 10);
  var made = 0;
  for (var i = 0; i < threads.length; i++) {
    var thread = threads[i];
    if (thread.isInChats()) continue;
    var msgs = thread.getMessages();
    var last = msgs[msgs.length - 1];
    var body = (last.getPlainBody() || "").slice(0, 4000);
    if (!body.trim()) { thread.addLabel(done); continue; }

    var reply = callOpenAI(key, system, body);
    if (reply) {
      last.createDraftReply(reply);
      thread.addLabel(done);
      made++;
    }
  }
  Logger.log("作成した下書き: " + made + " 件");
}

function callOpenAI(key, system, userText) {
  try {
    var res = UrlFetchApp.fetch("https://api.openai.com/v1/chat/completions", {
      method: "post",
      contentType: "application/json",
      headers: { Authorization: "Bearer " + key },
      payload: JSON.stringify({
        model: "gpt-4o-mini",
        temperature: 0.4,
        max_tokens: 600,
        messages: [
          { role: "system", content: system },
          { role: "user", content: "次の問い合わせメールへの返信の下書きを作成してください。\n\n----\n" + userText + "\n----" }
        ]
      }),
      muteHttpExceptions: true
    });
    var data = JSON.parse(res.getContentText());
    if (data.error) { Logger.log("API error: " + data.error.message); return null; }
    return data.choices && data.choices[0] && data.choices[0].message && data.choices[0].message.content;
  } catch (e) {
    Logger.log("fetch error: " + e); return null;
  }
}

/** 15分ごとの自動実行トリガーを設置（1回だけ実行） */
function setupTrigger() {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === "draftReplies") ScriptApp.deleteTrigger(triggers[i]);
  }
  ScriptApp.newTrigger("draftReplies").timeBased().everyMinutes(15).create();
  Logger.log("トリガー設置完了（15分ごとに draftReplies を実行）");
}
