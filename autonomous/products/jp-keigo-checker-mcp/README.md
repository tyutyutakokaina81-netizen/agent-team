# jp-keigo-checker-mcp

日本語ビジネス敬語をチェック・変換する MCP サーバー。x402 protocol で USDC による自動決済ゲートを実装。

**位置づけ**: 自立型AI企業（Toyama 発）が提供する、AI エージェント向け日本語敬語アシスタント。

## 何をする？

- 30件の敬語変換ルール（尊敬語・謙譲語・丁寧語・ビジネス慣用句）でテキストをチェック
- 18件のビジネスメールテンプレート（挨拶・依頼・お礼・お詫び・報告・断り）を提供
- カジュアルな日本語をビジネス敬語に自動変換
- 二重敬語・過剰敬語・誤用パターンを検出
- 100点満点の敬語スコアリング付き
- x402 で **$0.03 〜 $0.08 USDC の micro-payment** を自動徴収

## 料金表

| エンドポイント | 料金（USDC） | 説明 |
|----|----|----|
| `GET /` | 無料 | HTML ランディングページ |
| `GET /health` | 無料 | ヘルスチェック |
| `GET /info` | 無料 | サーバーメタ情報 |
| `GET /free/rule` | 無料 | 敬語ルール1件ランダム表示（広告） |
| `POST /check` | **$0.05** | テキストの敬語チェック・スコアリング |
| `POST /convert` | **$0.08** | カジュアル文を敬語に変換 |
| `POST /template` | **$0.03** | ビジネスメールテンプレート取得 |
| `POST /mcp` | **$0.05** | MCP JSON-RPC（Claude Desktop 等） |

## 敬語カテゴリ

| カテゴリ | 説明 | ルール数 |
|---------|------|---------|
| 尊敬語 | 相手の動作を高める表現 | 8件 |
| 謙譲語 | 自分の動作をへりくだる表現 | 11件 |
| 丁寧語 | 文全体を丁寧にする表現 | 3件 |
| ビジネス慣用句 | ビジネス特有の定型表現 | 8件 |

## メールテンプレートカテゴリ

| カテゴリ | テンプレート数 | 例 |
|---------|--------------|-----|
| 挨拶 | 1件 | 初めてのご挨拶メール |
| 依頼 | 4件 | 日程調整、見積もり依頼、催促、契約更新 |
| お礼 | 3件 | 打ち合わせ後、紹介後、お歳暮 |
| お詫び | 3件 | 納期遅延、ミス、クレーム対応 |
| 報告 | 4件 | 進捗報告、完了報告、資料送付、担当変更 |
| 断り | 2件 | 丁重なお断り、値引き交渉お断り |

## 検出パターン

### 二重敬語の検出
- 「おっしゃられる」→「おっしゃる」
- 「ご覧になられる」→「ご覧になる」
- 「拝見させていただく」→「拝見いたしました」

### カジュアル表現の検出
- 「了解しました」→「承知いたしました」
- 「すみません」→「申し訳ございません」
- 「ちょっと」→「少々」
- 「わかりました」→「承知いたしました」

### 誤用の検出
- 「ご教授ください」→「ご教示ください」
- 「とんでもございません」→「とんでもないことでございます」
- 「役不足」→「力不足」

## 収益モデル

- x402 protocol（Coinbase + Cloudflare、2026-02 launch）が支払い処理を自動化
- USDC が **オーナーの Coinbase Wallet address に直接入金**
- 決済は Base ネットワーク（2秒、ガス代 $0.001 以下）
- 中間手数料 **ゼロ**（Stripe 3.6% や銀行振込手数料なし）

## 想定ユースケース

1. Claude Desktop ユーザーが日本語メールを書く → Claude が `jp-keigo-checker-mcp` で敬語チェック → $0.05 USDC 自動支払い → 修正提案を受け取る
2. AI エージェントが日本語のビジネス文書を自動生成 → 敬語変換で品質を担保 → $0.08 USDC
3. 日本語学習者向けチャットボットが敬語の指導に利用 → 月次で数百 req
4. 日本企業のカスタマーサポート AI がメールテンプレートを取得 → $0.03 USDC

## デプロイ

```bash
cd autonomous/products/jp-keigo-checker-mcp/
npm install
npx wrangler secret put SERVER_ADDRESS  # Coinbase Wallet アドレスを登録
npm run deploy                          # Cloudflare Workers にデプロイ
```

## 開発

```bash
cd autonomous/products/jp-keigo-checker-mcp/
npm install
npm run dev      # ローカル開発
npm run deploy   # Cloudflare Workers にデプロイ
```

## 動作確認（curl）

```bash
# 無料エンドポイント
curl -s http://127.0.0.1:8787/health | python3 -m json.tool
curl -s http://127.0.0.1:8787/info | python3 -m json.tool
curl -s http://127.0.0.1:8787/free/rule | python3 -m json.tool

# 有料エンドポイント（x402 決済必要）
curl -s -X POST http://127.0.0.1:8787/check \
  -H 'Content-Type: application/json' \
  -d '{"text":"すみません、ちょっと聞きたいんですが"}' | python3 -m json.tool

curl -s -X POST http://127.0.0.1:8787/convert \
  -H 'Content-Type: application/json' \
  -d '{"text":"了解しました、あとで確認します","context":"メール"}' | python3 -m json.tool

curl -s -X POST http://127.0.0.1:8787/template \
  -H 'Content-Type: application/json' \
  -d '{"category":"お詫び"}' | python3 -m json.tool
```

## Claude Desktop 設定例

```json
{
  "mcpServers": {
    "jp-keigo": { "url": "https://jp-keigo-checker-mcp.<your-subdomain>.workers.dev/mcp" }
  }
}
```

## MCP ツール一覧

| ツール名 | 説明 |
|---------|------|
| `check_keigo` | テキストの敬語をチェック。スコアリング・問題点の指摘 |
| `convert_to_keigo` | カジュアルな日本語を敬語に変換 |
| `get_email_template` | ビジネスメールテンプレートの取得・検索 |

## データ更新

- `data/keigo_rules.json` — 敬語変換ルールを追加・編集
- `data/email_templates.json` — メールテンプレートを追加・編集

## 免責事項

この情報は一般的な敬語用法の要約です。業界・組織特有の慣習がある場合は適宜調整してください。

## ライセンス

MIT。autonomous AI company (Toyama) がメンテナンスしています。

## 参考リンク

- [x402 Protocol](https://x402.org/)
- [Coinbase Agentic Wallets](https://www.coinbase.com/developer-platform/discover/launches/agentic-wallets)
- [Cloudflare x402 Docs](https://developers.cloudflare.com/agents/agentic-payments/x402/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
