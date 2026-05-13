# jp-startup-legal-mcp

日本のスタートアップ・フリーランス向け法務FAQ・手続きガイドを提供する MCP サーバー。x402 protocol で USDC による自動決済ゲートを実装。

**位置づけ**: 自立型AI企業（Toyama 発）の MCP プロダクト。起業・フリーランスに関する法務知識を AI エージェント経由で提供。

## 免責事項

**この情報は一般的な法務知識の提供を目的としており、法的助言ではありません。** 具体的な法的問題については、必ず弁護士・司法書士・税理士等の専門家にご相談ください。法令は改正される場合がありますので、最新の法令を確認してください。

## 何をする？

- 32 件の法務FAQ（会社設立・契約・知的財産・税務・労務・許認可・個人情報・フリーランス）
- 22 件の手続きガイド（必要書類・ステップ・費用・所要日数・よくあるミス付き）
- AI エージェント（Claude / OpenAI / その他）から直接呼び出し可能
- x402 で **$0.03 〜 $0.10 USDC の micro-payment** を自動徴収

## カバーするカテゴリ

| カテゴリ | FAQ 例 |
|---------|--------|
| 会社設立 | 個人事業主 vs 法人、株式会社 vs 合同会社、資本金、設立届出 |
| 契約 | 業務委託契約、NDA、請負 vs 準委任、電子契約、収入印紙 |
| 知的財産 | 著作権、商標登録、AI と知的財産、ドメイン名 |
| 税務 | 確定申告、インボイス制度、源泉徴収、経費、決算期 |
| 労務 | 従業員雇用、社会保険、36協定、テレワーク |
| 許認可 | 特定商取引法、飲食店営業許可、在留資格 |
| 個人情報 | 個人情報保護法、プライバシーポリシー |
| フリーランス | フリーランス保護法、副業、法的支援サービス |

## 料金表

| エンドポイント | 料金（USDC） | 説明 |
|----|----|----|
| `GET /` | 無料 | HTML ランディングページ |
| `GET /health` | 無料 | ヘルスチェック |
| `GET /info` | 無料 | サーバーメタ情報 |
| `GET /free/faq` | 無料 | FAQ 1件ランダム表示（広告） |
| `POST /search` | **$0.05** | キーワード・カテゴリ検索 |
| `POST /detail` | **$0.03** | FAQ・手続きの詳細取得 |
| `POST /checklist` | **$0.10** | 手続きチェックリスト（全ステップ・書類付き） |
| `POST /mcp` | **$0.05** | MCP JSON-RPC（Claude Desktop 等） |

## 収益モデル

- x402 protocol（Coinbase + Cloudflare、2026-02 launch）が支払い処理を自動化
- USDC が **オーナーの Coinbase Wallet address に直接入金**
- 決済は Base ネットワーク（2 秒、ガス代 $0.001 以下）
- 中間手数料 **ゼロ**（Stripe 3.6% や銀行振込手数料なし）

## MCP ツール

| ツール名 | 説明 |
|---------|------|
| `search_legal_faq` | 法務FAQの検索（キーワード、カテゴリ、対象者、難易度でフィルタ可能） |
| `get_faq_detail` | FAQ・手続きの詳細取得（関連する手続き・FAQ も返す） |
| `get_procedure_checklist` | 手続きの完全チェックリスト（必要書類、手順、費用、注意点） |

## 想定ユースケース

1. フリーランスが Claude に「開業届の出し方を教えて」と質問 → Claude が `jp-startup-legal-mcp` を呼ぶ → $0.05 USDC 自動支払い → FAQ + 手続きチェックリストを返す
2. スタートアップ創業者が「株式会社と合同会社どっちがいい？」→ 法務FAQ で比較情報を取得
3. AI エージェントが日本での起業支援タスク中に法務情報が必要 → x402 で支払い → データ取得

## デプロイ

jp-subsidy-mcp の [DEPLOY_11MIN.md](../jp-subsidy-mcp/DEPLOY_11MIN.md) と同じ手順でデプロイ可能です。

```bash
cd autonomous/products/jp-startup-legal-mcp/
npm install
npx wrangler secret put SERVER_ADDRESS    # ウォレットアドレスを登録
npm run deploy                             # Cloudflare Workers にデプロイ
```

## 開発

```bash
cd autonomous/products/jp-startup-legal-mcp/
npm install
npm run dev      # ローカル開発（http://localhost:8787）
npm run deploy   # Cloudflare Workers にデプロイ
```

## 動作確認（curl）

```bash
# 無料エンドポイント
curl -s http://localhost:8787/health | python3 -m json.tool
curl -s http://localhost:8787/info | python3 -m json.tool
curl -s http://localhost:8787/free/faq | python3 -m json.tool

# 有料エンドポイント（ローカル開発時は x402 なしで動作）
curl -s -X POST http://localhost:8787/search \
  -H 'Content-Type: application/json' \
  -d '{"query": "開業届"}' | python3 -m json.tool

curl -s -X POST http://localhost:8787/detail \
  -H 'Content-Type: application/json' \
  -d '{"id": "faq-001"}' | python3 -m json.tool

curl -s -X POST http://localhost:8787/checklist \
  -H 'Content-Type: application/json' \
  -d '{"id": "proc-001", "format": "markdown"}' | python3 -m json.tool
```

## データ更新

- `data/legal_faq.json` に法務FAQ を追加・更新
- `data/procedures.json` に手続きガイドを追加・更新
- 法改正時は速やかにデータを更新してください

## ライセンス

MIT。autonomous AI company (Toyama) がメンテナンスしています。

## 参考リンク

- [x402 Protocol](https://x402.org/)
- [Coinbase Agentic Wallets](https://www.coinbase.com/developer-platform/discover/launches/agentic-wallets)
- [Cloudflare x402 Docs](https://developers.cloudflare.com/agents/agentic-payments/x402/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [国税庁](https://www.nta.go.jp/)
- [法務局](https://houmukyoku.moj.go.jp/)
- [特許庁](https://www.jpo.go.jp/)
- [個人情報保護委員会](https://www.ppc.go.jp/)
- [フリーランス保護法](https://www.jftc.go.jp/freelance/)
