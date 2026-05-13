# JP Business Docs MCP Server

日本のビジネス文書テンプレート・記入ガイドを提供する MCP サーバー。

法人設立・税務・請求書・契約書・届出・経理に関する **24種類** のテンプレートを収録。  
AI エージェント（Claude Desktop 等）から MCP プロトコルで直接利用可能。

---

## 収録カテゴリ

| カテゴリ | テンプレート数 | 主な内容 |
|---------|-------------|---------|
| 法人設立 | 4 | 株式会社定款、合同会社定款、設立届出書、事業計画書 |
| 税務 | 4 | 青色申告、消費税届出、確定申告ガイド、法人税チェックリスト |
| 請求書 | 4 | インボイス対応請求書、見積書、納品書、領収書 |
| 契約書 | 4 | 業務委託契約書、NDA、売買契約書、雇用契約書 |
| 届出 | 4 | 開業届、給与支払事務所届出、社会保険適用届、労働保険成立届、議事録 |
| 経理 | 3 | 経費精算書、月次試算表、源泉徴収計算シート |

---

## エンドポイント

### 無料（認証不要）

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/` | ランディングページ（HTML） |
| GET | `/health` | ヘルスチェック |
| GET | `/info` | API 情報・カテゴリ統計 |
| GET | `/free/template` | ランダムテンプレート1件（サンプル） |

### 有料（x402 決済）

| メソッド | パス | 価格 | 説明 |
|---------|------|------|------|
| POST | `/search` | $0.03 | テンプレート検索（キーワード・カテゴリ・難易度） |
| POST | `/generate` | $0.15 | フィールド値を埋めた文書を生成 |
| POST | `/detail` | $0.02 | テンプレート詳細情報（必須フィールド・構成・関連補助金） |
| POST | `/mcp` | $0.05 | MCP JSON-RPC エンドポイント |

---

## MCP ツール

MCP クライアント（Claude Desktop 等）から以下のツールを利用できます：

### `search_templates`
テンプレートをキーワード・カテゴリ・難易度で検索。

```json
{
  "query": "請求書 インボイス",
  "category": "請求書",
  "difficulty": "easy",
  "max_results": 5
}
```

### `generate_document`
テンプレートIDとフィールド値から記入済み文書を生成。

```json
{
  "template_id": "doc-008",
  "field_values": {
    "発行者名": "株式会社サンプル",
    "登録番号": "T1234567890123",
    "請求先名": "株式会社クライアント",
    "請求日": "2026-05-13",
    "品目": "Webサイト制作",
    "数量": "1",
    "単価": "500000",
    "税率": "10%"
  }
}
```

### `get_template_detail`
テンプレートの詳細（必須フィールド・セクション構成・関連補助金）を取得。

```json
{
  "template_id": "doc-001"
}
```

---

## クロスリファレンス

`related_subsidies` フィールドで **jp-subsidy-mcp** サーバーの補助金IDを参照可能。  
例：法人設立テンプレート → 創業補助金・小規模事業者持続化補助金の情報に直接アクセス。

---

## デプロイ

### 前提条件
- Node.js 18+
- Cloudflare Workers アカウント
- Wrangler CLI

### セットアップ

```bash
cd autonomous/products/jp-business-docs-mcp
npm install
```

### ローカル開発

```bash
npm run dev
# → http://localhost:8787
```

### 本番デプロイ

```bash
# Cloudflare にデプロイ
npm run deploy
```

### 動作確認

```bash
# ヘルスチェック
curl http://localhost:8787/health

# API 情報
curl http://localhost:8787/info

# 無料サンプル
curl http://localhost:8787/free/template
```

---

## MCP クライアント接続

Claude Desktop の `claude_desktop_config.json` に追加：

```json
{
  "mcpServers": {
    "jp-business-docs": {
      "url": "https://jp-business-docs-mcp.YOUR_SUBDOMAIN.workers.dev/mcp",
      "transport": "http"
    }
  }
}
```

---

## 技術スタック

- **ランタイム**: Cloudflare Workers
- **フレームワーク**: Hono
- **決済**: x402-hono（HTTP 402 ベースのマイクロペイメント）
- **言語**: TypeScript
- **データ**: 静的 JSON（24テンプレート）

---

## 価格設計

| 操作 | 価格 | 想定用途 |
|------|------|---------|
| 検索 | $0.03 | テンプレート探索・一覧取得 |
| 生成 | $0.15 | 記入済み文書の出力 |
| 詳細 | $0.02 | 必須フィールド・構成の確認 |
| MCP | $0.05 | AI エージェントからの統合利用 |

---

## 関連プロダクト

- **jp-subsidy-mcp** — 日本の補助金・助成金情報 MCP サーバー（30件収録）
- **toyama-local-mcp** — 富山県観光・グルメ情報 MCP サーバー（24件収録）

---

## ライセンス

本テンプレートは一般的な書式であり、法的助言を構成するものではありません。  
重要な契約書・届出書は税理士・弁護士・司法書士等の専門家にご確認ください。
