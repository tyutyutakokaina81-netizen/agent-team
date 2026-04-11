# jp-subsidy-mcp

日本の補助金・助成金を検索する MCP サーバー。x402 protocol で USDC による自動決済ゲートを実装。

**位置づけ**: 自立型AI企業（Toyama 発）が初めて世に出す**収益性を持つ商品**。

## 何をする？

- 14 件（初期）の日本の公開補助金情報を AI エージェント（Claude / OpenAI / その他）に提供
- AI 適合度・地域・金額でフィルタ
- 事業コンテキストからレコメンド
- x402 で **$0.02 〜 $0.10 USDC の micro-payment** を自動徴収

## 料金表

| エンドポイント | 料金（USDC） | 説明 |
|----|----|----|
| `GET /` | 無料 | HTML ランディングページ |
| `GET /health` | 無料 | ヘルスチェック |
| `GET /info` | 無料 | サーバーメタ情報 |
| `GET /free/list` | 無料 | 1件だけランダム表示（広告）|
| `POST /search` | **$0.05** | キーワード検索 |
| `POST /recommend` | **$0.10** | 事業コンテキストからレコメンド |
| `POST /detail` | **$0.02** | 1件の詳細取得 |
| `POST /mcp` | **$0.05** | MCP JSON-RPC（Claude Desktop 等） |

## 収益モデル

- x402 protocol（Coinbase + Cloudflare、2026-02 launch）が支払い処理を自動化
- USDC が **オーナーの Coinbase Wallet address に直接入金**
- 決済は Base ネットワーク（2 秒、ガス代 $0.001 以下）
- 中間手数料 **ゼロ**（Stripe 3.6% や銀行振込手数料なし）

## 想定ユースケース

1. Claude Desktop ユーザーが "IT 導入補助金の対象になりたい" と質問 → Claude が `jp-subsidy-mcp` を呼ぶ → $0.05 USDC 自動支払い → 該当補助金を返す
2. 他社の AI エージェントが日本の SMB 向け運営タスク中に補助金情報が必要になった → x402 で支払い → データ取得
3. ChatGPT/Claude API を使う日本語チャットボットが UX 強化 → 月次で数百 req

## デプロイ

**まず [DEPLOY_11MIN.md](./DEPLOY_11MIN.md) を見てください**。オーナーが 11 分で live にできる手順を書いています。

## 開発

```bash
cd autonomous/products/jp-subsidy-mcp/
npm install
npm run dev      # ローカル開発
npm run deploy   # Cloudflare Workers にデプロイ
```

## データ更新

`data/subsidies.json` に補助金情報を追加。自律型AIが週次で自動更新予定（今後の拡張）。

## 免責事項

この情報は公開情報の要約です。正式な申請前に必ず各制度の公式サイトで最新の要件・金額・期限を確認してください。

## ライセンス

MIT。autonomous AI company (Toyama) がメンテナンスしています。

## 参考リンク

- [x402 Protocol](https://x402.org/)
- [Coinbase Agentic Wallets](https://www.coinbase.com/developer-platform/discover/launches/agentic-wallets)
- [Cloudflare x402 Docs](https://developers.cloudflare.com/agents/agentic-payments/x402/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
