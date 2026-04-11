# toyama-local-mcp

富山県の観光・グルメ・伝統工芸・祭り情報を AI エージェントに提供する MCP サーバー。

**位置づけ**: autonomous AI 会社の**第2号収益商品**。jp-subsidy-mcp と同じ wallet アドレスで運用可。

## 何をする？

- 24 件の富山県内観光スポット・グルメ・伝統工芸・祭り情報を収録
- カテゴリ／エリア／季節／予算／子連れ可でフィルタ
- 行動コンテキストから旅行行程をレコメンド
- Claude / ChatGPT / その他 AI エージェントから直接呼び出せる
- x402 protocol で自動決済（$0.02 〜 $0.08 USDC）

## 料金表

| エンドポイント | 料金 | 説明 |
|----|----|----|
| `GET /` | 無料 | HTML ランディング |
| `GET /health` | 無料 | ヘルスチェック |
| `GET /info` | 無料 | メタ情報 |
| `GET /free/spot` | 無料 | 1件ランダム表示（広告）|
| `POST /search` | **$0.03** USDC | フィルタ検索 |
| `POST /recommend` | **$0.08** USDC | 行程レコメンド |
| `POST /detail` | **$0.02** USDC | 詳細取得 |
| `POST /mcp` | **$0.03** USDC | MCP JSON-RPC |

## ターゲットユーザー

- 日本語で富山旅行を調べたい海外観光客（インバウンド）
- 旅行ブログ作成者（AI で行程を組ませたい）
- 観光業の自動化（旅館のコンシェルジュ bot 等）
- 地方創生系の AI エージェント

## デプロイ

jp-subsidy-mcp と同じ手順：

```bash
cd autonomous/products/toyama-local-mcp/
npm install
npx wrangler secret put SERVER_ADDRESS  # 同じ Coinbase Wallet address
npx wrangler deploy
```

deploy 後の URL: `https://toyama-local-mcp.<your-subdomain>.workers.dev`

## 収録カテゴリ

- 自然・絶景（立山黒部・黒部ダム・雨晴海岸 他）
- 世界遺産（五箇山）
- 温泉（宇奈月温泉）
- グルメ（富山ブラック・白えび・氷見ぶり・ます寿司）
- 伝統工芸（高岡銅器・井波彫刻・越中和紙）
- 祭り（越中おわら風の盆）
- 歴史（富山城・瑞龍寺・高岡大仏）
- 公園（環水公園・海王丸パーク）

## ライセンス

MIT。autonomous AI company (Toyama) がメンテナンス。
