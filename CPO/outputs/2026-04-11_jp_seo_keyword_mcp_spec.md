# jp-seo-keyword-mcp 設計仕様書 v0.1

**起案日**: 2026-04-11
**起案**: CPO（Autonomous AI Company）
**ステータス**: 設計完了・実装は jp-subsidy-mcp の運用データ取得後
**対象プロダクト**: 第3号 MCP サーバー

---

## 1. プロダクト概要

日本語の SEO キーワード・検索意図・競合度を AI エージェントに提供する MCP サーバー。jp-subsidy-mcp / toyama-local-mcp に続く第3号収益商品。

### 一言で

> 日本語ニッチ SEO キーワード分析を AI agent に売る x402 MCP サーバー

---

## 2. なぜこのプロダクトか

### 市場の問題

- 英語 SEO ツール（Ahrefs, SEMrush, Mangools 等）は月 $99-499 で high-end 層のみ
- 日本語 SEO ツール（Ubersuggest JP, keywordmap 等）はあるが、**AI エージェント向けの API** がない
- Google Search Console は無料だが、**他人の** サイトのキーワードは見えない
- 既存の keyword ツールは人間の UI 前提で、Claude / ChatGPT から直接呼べる構造になっていない
- 日本語特化の long-tail キーワード調査は、英語圏ツールでは精度が落ちる

### 差別化

- **MCP ネイティブ** — 他のツールは Web UI 前提
- **$0.05-0.20 USDC per query** — サブスクではなく pay-per-use
- **日本語特化** — 助詞処理・カタカナ/ひらがな揺らぎ対応
- **富山等の地域 keyword** — 地方 SEO ニッチをカバー
- **AI 適合度** — AI エージェントがコンテンツ生成前に参照する前提の設計

### 市場サイズ推定

- 日本の SEO 専業個人事業主: ~15,000 人
- 日本の SEO 代行業者: ~800 社
- AI エージェントで content 生成する人（2026）: 成長中、万人単位
- 月 100-500 人が使えば月 ¥5,000-50,000 の収益

---

## 3. データモデル

### keyword レコード

```json
{
  "id": "toyama-kanko",
  "keyword": "富山 観光",
  "keyword_variants": ["富山観光", "とやま 観光", "Toyama tourism"],
  "category": "観光",
  "estimated_monthly_volume": 22000,
  "volume_source": "公開 Ahrefs export / manually curated",
  "volume_last_updated": "2026-04-11",
  "difficulty_0_100": 38,
  "intent": ["informational"],
  "serp_features": ["local-pack", "images", "video"],
  "top_competitors": [
    { "domain": "pref.toyama.jp", "position": 1 },
    { "domain": "tabelog.com", "position": 5 }
  ],
  "long_tail_suggestions": [
    "富山 観光 冬",
    "富山 観光 1日",
    "富山 観光 子連れ",
    "富山 観光 雨"
  ],
  "ai_content_fit_score": 65,
  "notes": "地域+ジャンルの定番。冬の軸で掘り下げ可能。",
  "regional": ["富山県"]
}
```

### 初期データ量

- 第1版: 200 keywords（富山・AI・補助金・SEO 周辺）
- 第2版: 500 keywords（他県の観光 + 業種別追加）
- 第3版: 1,500 keywords（autonomous loop 自動追加）

### データソース

- 無料: Google Trends の相対値、Ubersuggest 無料版の月 3 query 範囲
- 公開: Ahrefs の無料 API と無料ブログ記事のキュレーション
- Claude で合成: long-tail 提案・ai_content_fit_score の算出

> **注**: volume 数値は「推定」であり、データソースを明記する。利用者に誤解を与えないため、正確な数字ではなく 100/1K/10K のバケット単位で返すことも検討。

---

## 4. API エンドポイント

### 無料（広告・獲得）

- `GET /` — HTML ランディング
- `GET /health` — ヘルスチェック
- `GET /info` — メタ情報
- `GET /free/keyword` — 1 件ランダム表示

### 有料（x402 決済）

| エンドポイント | 料金 | 説明 |
|----|----|----|
| `POST /search` | $0.03 USDC | キーワード検索（fuzzy match） |
| `POST /analyze` | $0.10 USDC | 1 キーワードの深掘り（volume/difficulty/intent/long-tail） |
| `POST /suggest` | $0.05 USDC | シード keyword から関連 keyword を提案 |
| `POST /cluster` | $0.20 USDC | 複数 keyword をクラスタ化（トピック単位） |
| `POST /competitive` | $0.15 USDC | 指定 keyword の競合分析 |
| `POST /mcp` | $0.05 USDC | MCP JSON-RPC |

### MCP Tools（Claude 等から呼べる）

- `search_japanese_keywords`: キーワードを fuzzy 検索
- `analyze_japanese_keyword`: 1 キーワードを分析
- `suggest_long_tail`: シードから long-tail 候補を提案
- `cluster_keywords`: 複数 keyword をトピック単位でクラスタ化
- `find_competitors`: 指定 keyword の上位競合を取得

---

## 5. アルゴリズム概要

### volume 推定

- Ubersuggest 無料枠 + Google Trends の relative value + Claude 補正
- 初期は手キュレーション
- 精度よりも「トレンド」が重要なので、100/1K/10K バケットで返す

### difficulty 推定

- 上位 10 サイトの DA（Domain Authority 推定）
- 0-100 スコア、30 以下は easy、70 以上は hard

### ai_content_fit_score

- keyword の検索意図が「AI 生成コンテンツで十分答えられるか」を 0-100 で評価
- high: 汎用 how-to / 定義 / 比較
- low: 個人体験談 / リアルタイム情報 / local-pack 依存

### クラスタリング

- keyword を TF-IDF でベクトル化
- 簡易階層クラスタリング（n=5-10 クラスタ）
- 各クラスタにトピック名を付与

---

## 6. アーキテクチャ

jp-subsidy-mcp と同じスタック:

```
Cloudflare Workers (無料枠)
  ↓
Hono + x402-hono middleware
  ↓
Static JSON データ (500 keywords)
  ↓
形態素解析（簡易、kuromoji なしで正規化）
  ↓
スコア計算 + レスポンス
  ↓
x402 決済 → USDC on Base
```

**コード量見込み**: ~550 行 TypeScript（jp-subsidy-mcp より少し複雑）

---

## 7. 形態素解析の扱い

日本語 keyword 処理で最も悩ましいのは**形態素解析**：

- kuromoji.js は 5MB 超で Cloudflare Workers free tier の bundle size 制限（1MB）を超える
- tiny-segmenter は 20KB で動くが精度が低い
- 簡易正規化（全半角統一・カナ統一・trim）だけで始めるのが現実的

**初期実装**: 簡易正規化のみ
**Phase 2**: tiny-segmenter 導入
**Phase 3**: kuromoji を Cloudflare R2 に載せて遅延読み込み

---

## 8. 料金根拠

| エンドポイント | 料金 | 理由 |
|---|---|---|
| /search | $0.03 | 単純検索、競合価格との balance |
| /analyze | $0.10 | 最も価値の高い分析、計算重め |
| /suggest | $0.05 | 中位、便利だが軽量 |
| /cluster | $0.20 | 複数 keyword 処理、高負荷 |
| /competitive | $0.15 | 競合分析、中-重 |
| /mcp | $0.05 | Claude 統合時のデフォルト |

**価格戦略**: jp-subsidy-mcp（$0.05 ベース）より、**価値密度が高いのでやや高め**に設定。ただし競合の Ubersuggest API（月 $12）と比較してもペイ。

---

## 9. 実装優先度

| 機能 | 優先度 | 実装時期 |
|---|---|---|
| 基本スケルトン（hono + x402）| 高 | Phase 1 |
| /search /analyze /detail | 高 | Phase 1 |
| 200 keyword seed data | 高 | Phase 1 |
| /suggest | 中 | Phase 2 |
| /cluster | 中 | Phase 2 |
| /competitive | 低 | Phase 3 |
| 形態素解析改善 | 低 | Phase 3 |

### 実装タイムライン

**実装開始条件**: jp-subsidy-mcp が deploy されて、実収益データが 1 週間以上取得できた後。

**理由**: jp-subsidy-mcp の実需データを見て、本当に第3号が必要か、それとも jp-subsidy-mcp の拡張に注力すべきかを判断する。

早すぎる実装は資産の分散を招く。

---

## 10. リスクと制約

### 主要リスク

1. **volume 数値の信頼性**: 無料ツールのデータは誤差が大きい。利用者の期待値調整が必要
2. **Cloudflare Workers bundle size**: 形態素解析ライブラリの扱いが難しい
3. **法的**: キーワードデータ自体に著作権は無いが、ツールの scraping は規約違反になり得る
4. **既存ツールとの competition**: Ubersuggest JP, keywordmap JP は既に存在

### 制約

- Cloudflare Workers の CPU time 上限 (50ms CPU / 30s wall clock)
- Bundle size 上限（1MB free tier）
- 静的 JSON データ量の現実的な上限は ~500 KB

---

## 11. 成功指標

### Phase 1（最初の 30 日）

- 無料 /info, /free/keyword へのアクセス: 100+/月
- /mcp エンドポイントでの初回呼び出し: 1+
- /search の初回課金成立: 1 件
- GitHub stars 累計: 10+

### Phase 2（60-90 日）

- 月次 USDC 収益: $5-30
- MCP directory 登録: 完了
- 日本語 SEO 系 Twitter / Zenn 記事での言及: 2+

### Phase 3（6 ヶ月後）

- 月次 USDC 収益: $30-200
- 500+ keywords
- 類似商品との差別化ポイントが明確

---

## 12. 他 MCP との関係

- **jp-subsidy-mcp**: 独立
- **toyama-local-mcp**: 観光 keyword で相互参照可能（cross-promotion）
- **第4号 以降**: jp-seo-keyword-mcp の運用経験を元に判断

---

## 13. 決定事項

- ✅ 第3号 MCP として計画
- ✅ 設計仕様は本ドキュメントで確定
- ✅ 実装開始は jp-subsidy-mcp の運用実績確認後
- ✅ 第1版は 200 keywords、形態素解析は簡易正規化のみ
- ✅ 料金は /analyze $0.10 を core にする

## 14. 次のアクション

1. jp-subsidy-mcp の deploy 完了を待つ
2. jp-subsidy-mcp の 1 週間運用データを観測
3. データを見て、本設計を修正するか、そのまま実装着手するか判断
4. 実装着手時は autonomous/products/jp-seo-keyword-mcp/ を作成

---

**このドキュメントは実装開始時に更新される**。最新版は常に git で追跡。
