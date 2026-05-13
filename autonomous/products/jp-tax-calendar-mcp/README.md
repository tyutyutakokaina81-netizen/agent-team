# jp-tax-calendar-mcp

日本の税務・届出・補助金・経理・季節行事の期限カレンダーを提供する MCP サーバー。x402 protocol で USDC による自動決済ゲートを実装。

**位置づけ**: 自立型AI企業（Toyama 発）が提供する、日本のビジネス期限管理に特化した MCP サーバー。

## 何をする？

- 35 件（初期）の日本の税務・届出・経理期限を AI エージェント（Claude / OpenAI / その他）に提供
- カテゴリ（税務/届出/補助金/季節行事/経理）、対象者（個人事業主/法人/both）、地域でフィルタ
- 指定日から N 日以内に到来する期限を緊急度付きで一覧表示
- 各期限の詳細情報（ペナルティ、関連期限、次回の日程）を提供
- x402 で **$0.02 〜 $0.05 USDC の micro-payment** を自動徴収

## 料金表

| エンドポイント | 料金（USDC） | 説明 |
|----|----|----|
| `GET /` | 無料 | HTML ランディングページ |
| `GET /health` | 無料 | ヘルスチェック |
| `GET /info` | 無料 | サーバーメタ情報 |
| `GET /free/next` | 無料 | 直近の期限1件だけ表示（広告）|
| `POST /search` | **$0.03** | キーワード検索 |
| `POST /upcoming` | **$0.05** | N日以内の期限一覧（緊急度付き） |
| `POST /detail` | **$0.02** | 1件の詳細取得 |
| `POST /mcp` | **$0.03** | MCP JSON-RPC（Claude Desktop 等） |

## カテゴリ

| カテゴリ | 内容 | 例 |
|----|----|----|
| 税務 | 所得税・法人税・消費税・住民税等の申告・納付 | 確定申告、予定納税、源泉徴収 |
| 届出 | 各種届出・申請手続き | 開業届、青色申告承認、インボイス登録 |
| 補助金 | 公募期間のある補助金・助成金 | IT導入補助金、持続化補助金 |
| 経理 | 日常の経理・決算業務 | 月次決算、年末調整、棚卸し |
| 季節行事 | ビジネス上の季節イベント | 新年会、お中元、お歳暮 |

## 収益モデル

- x402 protocol（Coinbase + Cloudflare、2026-02 launch）が支払い処理を自動化
- USDC が **オーナーの Coinbase Wallet address に直接入金**
- 決済は Base ネットワーク（2 秒、ガス代 $0.001 以下）
- 中間手数料 **ゼロ**（Stripe 3.6% や銀行振込手数料なし）

## 想定ユースケース

1. フリーランスが Claude Desktop で「今月中にやるべき税務手続きは？」と質問 → Claude が `jp-tax-calendar-mcp` を呼ぶ → $0.05 USDC 自動支払い → 期限一覧を返す
2. 経理担当者が「源泉徴収の納付期限はいつ？遅れたらどうなる？」→ 詳細情報を取得 → $0.02 USDC
3. AI エージェントが毎月の経理タスクリマインダーを自動生成 → 月次で $0.05 × 12 = $0.60/年
4. 補助金の公募期間を自動チェック → 申請タイミングを逃さない

## MCP ツール

Claude Desktop や MCP 対応クライアントから利用可能な3つのツール:

| ツール名 | 説明 |
|---------|------|
| `search_deadlines` | キーワード・カテゴリ・対象者・地域で期限を検索 |
| `get_upcoming` | N日以内に到来する期限を緊急度付きで一覧表示 |
| `get_deadline_detail` | 1件の期限の詳細（ペナルティ、関連期限、今後の日程） |

## デプロイ

```bash
cd autonomous/products/jp-tax-calendar-mcp/
npm install
npx wrangler secret put SERVER_ADDRESS   # Coinbase Wallet アドレスを設定
npm run deploy                            # Cloudflare Workers にデプロイ
```

## 開発

```bash
cd autonomous/products/jp-tax-calendar-mcp/
npm install
npm run dev      # ローカル開発（http://localhost:8787）
```

## 動作確認（curl）

```bash
# 無料エンドポイント
curl -s http://localhost:8787/health | python3 -m json.tool
curl -s http://localhost:8787/info | python3 -m json.tool
curl -s http://localhost:8787/free/next | python3 -m json.tool

# 有料エンドポイント（ローカル開発時は x402 チェックなし）
curl -s -X POST http://localhost:8787/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"確定申告","target":"個人事業主"}' | python3 -m json.tool

curl -s -X POST http://localhost:8787/upcoming \
  -H 'Content-Type: application/json' \
  -d '{"days":30,"target":"個人事業主"}' | python3 -m json.tool

curl -s -X POST http://localhost:8787/detail \
  -H 'Content-Type: application/json' \
  -d '{"id":"kakutei-shinkoku"}' | python3 -m json.tool
```

## Claude Desktop 設定例

```json
{
  "mcpServers": {
    "jp-tax-calendar": {
      "url": "https://jp-tax-calendar-mcp.<your-subdomain>.workers.dev/mcp"
    }
  }
}
```

## データ更新

`data/calendar.json` に期限情報を追加・更新。自律型AIが定期的に最新の公募情報を反映予定。

## 免責事項

この情報は公開情報の要約です。正式な届出・申告前に必ず税理士または各制度の公式サイトで最新の要件・期限を確認してください。

## ライセンス

MIT。autonomous AI company (Toyama) がメンテナンスしています。

## 参考リンク

- [x402 Protocol](https://x402.org/)
- [Coinbase Agentic Wallets](https://www.coinbase.com/developer-platform/discover/launches/agentic-wallets)
- [Cloudflare x402 Docs](https://developers.cloudflare.com/agents/agentic-payments/x402/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [国税庁](https://www.nta.go.jp/)
- [e-Tax](https://www.e-tax.nta.go.jp/)
