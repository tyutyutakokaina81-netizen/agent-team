# agent-gateway

依存ゼロ（Node.js 標準モジュールのみ）の JSON API サーバー。

## 起動

```bash
node gateway/server.mjs
# => Listening on http://127.0.0.1:3000
```

ポートを変更する場合:

```bash
PORT=8080 node gateway/server.mjs
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
