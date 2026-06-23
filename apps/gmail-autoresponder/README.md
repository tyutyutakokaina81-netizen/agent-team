# Gmail 自動返信ドラフト（Apps Script・無料・PC不要）
受信した問い合わせにAIが「返信の下書き」を自動作成→人が確認して送るだけ。送信は必ず人。
## 設置（5分）
1. script.google.com → 新規 → `Code.gs` を貼る
2. プロジェクト設定 → スクリプトプロパティ：`OPENAI_API_KEY`（必須）、`SYSTEM_PROMPT`（任意・業種別。system-prompts.md参照）、`WATCH_LABEL`（任意）
3. `setupTrigger` を1回実行（承認許可）→15分毎に自動で下書き作成
4. `draftReplies` を手動実行して動作確認
## 安全
下書きのみ・自動送信なし。二重作成は ai-drafted ラベルで防止。断定しない指示を内蔵。
## 役割
AI自動化代行の納品物にもなる（Gmailユーザー向け「問い合わせ返信の自動化」）。
