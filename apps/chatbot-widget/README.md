# ドロップイン LLMチャットボット ウィジェット

単一 `chatbot.js`（依存ゼロ）。どのサイトにも `<script>` 2行で組み込める、実際に会話するLLMチャット。
AI自動化代行の納品物／デモ。`index.html` がデモページ（右下ボタンで体験）。

## 組み込み
```html
<script>window.CHATBOT_CONFIG={title:"○○",system:"...",greeting:"...",model:"gpt-4o-mini"};</script>
<script src="chatbot.js"></script>
```
- `system`：業種ごとに差し替え＝その店専用の応答に。
- APIキー：利用者の自前（localStorage保存・外部送信なし）。当社にAPIコスト無し。
- キー無し：台本フォールバックで動作＋設定を促す。
- 本番（不特定多数公開）：`proxyUrl` でキーをサーバ側に。露出防止。構築は当社対応。

## 配信
GitHub Pages（pages.yml）で `/chatbot-widget/` に公開。デモ＝`/chatbot-widget/`。
