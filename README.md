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

| メソッド | パス             | 説明                                              |
| -------- | ---------------- | ------------------------------------------------- |
| GET      | `/`              | 「かいちのAI大学」デスクトップUI（HTML）          |
| GET      | `/desktop/*`     | デスクトップUIの静的ファイル（CSS/JS）            |
| GET      | `/health`        | ヘルスチェック                                    |
| GET      | `/version`       | サービス名・バージョン                            |
| POST     | `/echo`          | 受け取った JSON をそのまま返す                    |

## かいちのAI大学 デスクトップUI

ブラウザで `http://127.0.0.1:3000/` を開くと、Windows 98 風の
デスクトップ画面が表示されます。

- 左：SVG＋CSSアニメの「かいち教官」キャラ（呼吸・瞬き・口パク）
- 右：対話入力エリア（Enter で送信、Shift+Enter で改行）
- 下：タスクバー＋クリック可能なデスクトップアイコン

依存ゼロ（外部ライブラリなし）。`desktop/` 配下のファイルを編集すれば
ロジック・スタイル・キャラを差し替えられます。

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
