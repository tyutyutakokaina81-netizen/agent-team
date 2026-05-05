# agent-gateway

依存ゼロ（Node.js 標準モジュールのみ）の JSON API サーバー。

## 起動

```bash
node server.mjs
# => Listening on http://127.0.0.1:3000
```

ポートを変更する場合:

```bash
PORT=8080 node server.mjs
```

## エンドポイント

| メソッド | パス       | 説明                          |
| -------- | ---------- | ----------------------------- |
| GET      | `/health`  | ヘルスチェック                |
| GET      | `/version` | サービス名・バージョン        |
| POST     | `/echo`    | 受け取った JSON をそのまま返す |

## 動作確認（curl 例）

```bash
# ヘルスチェック
curl -s http://127.0.0.1:3000/health | jq
# => { "ok": true, "time": "2026-02-13T..." }

# バージョン
curl -s http://127.0.0.1:3000/version | jq
# => { "name": "agent-gateway", "version": "0.1.0" }

# エコー
curl -s -X POST http://127.0.0.1:3000/echo \
  -H 'Content-Type: application/json' \
  -d '{"hello":"world"}' | jq
# => { "hello": "world" }

# 不正な JSON（400 エラー）
curl -s -X POST http://127.0.0.1:3000/echo \
  -H 'Content-Type: application/json' \
  -d 'not json' | jq
# => { "error": "Invalid JSON" }

# 存在しないパス（404）
curl -s http://127.0.0.1:3000/unknown | jq
# => { "error": "Not Found" }
```

## ログ出力

リクエストごとに `METHOD /path STATUS TIMEms` 形式で標準出力に記録されます。

```
GET /health 200 0.12ms
POST /echo 200 0.45ms
```

<!-- KPI:START -->
## ai-auto 自動運用ステータス（2026-05-05 20:10 時点）

毎朝 07:00 (JST) に GitHub Actions が当日のドラフトを自動生成・自動コミットします。
mac セットアップ不要。iPhone の GitHub アプリで開いて1分以内に公開可能。

| 指標 | 値 |
|------|---|
| 自動生成日数 | **1 日** |
| 最新ドラフト | [`daily/2026-05-05/`](daily/2026-05-05/) |
| ドラフト本日分 | 8 ファイル |

### 最新ドラフト一覧
  - `crowdworks_application_data.txt`
  - `crowdworks_application_writer.txt`
  - `note_draft.md`
  - `paid_note_2980.md`
  - `proposal_sample.md`
  - `reddit_post.md`
  - `seo_article.md`
  - `youtube_short.md`

### 公開フロー（iPhone・1分）
1. GitHub アプリで上の最新ドラフトを開く
2. `note_draft.md` を Raw 表示 → コピー
3. note アプリで貼り付け → 公開ボタン
4. 完了

詳細：
- 全体設計：[`projects/2026-05-05_AI自動収益化引き継ぎ/outputs/claude_code_handover.docx`](projects/2026-05-05_AI自動収益化引き継ぎ/outputs/claude_code_handover.docx)
- iPhone 1分運用ガイド：[`COO/outputs/2026-05-05_iPhone1分運用ガイド.md`](COO/outputs/2026-05-05_iPhone1分運用ガイド.md)
- mac 全自動 Plan B：[`projects/2026-05-05_AI自動収益化引き継ぎ/deploy/SETUP_PROMPT.md`](projects/2026-05-05_AI自動収益化引き継ぎ/deploy/SETUP_PROMPT.md)
<!-- KPI:END -->
