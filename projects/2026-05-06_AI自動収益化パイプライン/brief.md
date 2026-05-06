# プロジェクト：AI自動収益化パイプライン

## 目的
note・YouTube Shorts・Reddit・SNS・CrowdWorks を横断する **コンテンツ生成パイプライン** を構築し、
日次で「公開・応募できる素材」を outputs/ に出し続ける運用基盤を作る。

「仕組みはあるが、公開と応募が不足している」状態を解消することが最優先。

## 期間
2026-05-06 開始（90日 KPI と並走）

## 関与役職
- **CDO**：パイプライン構築・cron／自動化・ログ整備
- **CMO**：note記事・YouTube Shorts台本・SNS導線
- **CPO**：有料note・テンプレ商品との接続
- **CSO**：CrowdWorks応募文生成・受注ファネル

## 既存プロジェクトとの関係
- 兄弟プロジェクト `2026-04-08_月30万自動化/` は **収益柱（A/B/C）の事業設計** を担う。
- 本プロジェクトは **日次の生成・公開オペレーションを支える共通インフラ**。
  両者は重複せず補完関係にある。

## 5つの最優先タスク（引き継ぎ書 第5章 準拠）

| # | タスク | 主担当 | 出力先 |
|---|-------|--------|--------|
| 1 | YouTube Shorts 自動生成パイプライン | CMO・CDO | `outputs/{date}_youtube_short.md` |
| 2 | HeyGen AI女子アナ用スクリプト | CMO・CDO | `outputs/{date}_heygen_script.md` |
| 3 | Kling AI 動画プロンプト | CMO・CDO | `outputs/{date}_kling_prompt.md` |
| 4 | SNS／Reddit 投稿補助 | CMO・CDO | `outputs/{date}_sns_posts.md` |
| 5 | 有料note記事量産 | CPO・CMO | `outputs/{date}_paid_note.md` |

## ディレクトリ構成

```
2026-05-06_AI自動収益化パイプライン/
├── brief.md                       ← 本ファイル
├── README.md                      ← 運用手順
├── pipeline/
│   ├── run.sh                     ← cron から呼ぶメイン
│   ├── generate_daily_outputs.py  ← 5本まとめ生成
│   ├── generate_youtube_short.py
│   ├── generate_heygen_script.py
│   ├── generate_kling_prompt.py
│   ├── generate_sns_posts.py
│   ├── generate_paid_note.py
│   └── generate_crowdworks_application.py
├── prompts/                       ← 各タスクのテンプレート
├── outputs/                       ← 生成物（{YYYY-MM-DD_HHMM}_*.md）
├── logs/                          ← run.log・daily.log
└── docs/
    ├── kpi.md                     ← KPI トラッカ
    └── operation_flow.md          ← 日次フロー
```

## 設計方針

1. **依存ゼロ運用** — Python 標準ライブラリのみで動く。OpenAI／Claude API は環境変数があるときだけ使う（任意）。
2. **テーマ固定** — 高岡・富山・地方暮らし・AI副業・50代の働き方 を回す。
3. **必ず保存** — outputs/ と logs/ は両方書く。`logs/posted_{date}_{slug}.log` 形式。
4. **完全自動投稿はしない** — Reddit・X・noteは投稿文を生成し、人間が公開する半自動運用。
5. **失敗してもパイプラインは止めない** — 個別タスク失敗時は `logs/run.log` に記録し、他のタスクは続行。

## ステータス

- [x] プロジェクト立ち上げ
- [x] パイプライン基盤（run.sh + 個別ジェネレータ）
- [x] プロンプトテンプレート整備
- [ ] cron 連携（オーナー承認後）
- [ ] 7日連続公開達成
- [ ] 30日 KPI（note 30本 / 有料 10本 / Shorts 20本 / 応募 30件）
