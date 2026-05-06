# CDO インデックス（技術責任者）

## 担当業務
- プロンプト作成・管理・改善
- Claude Code活用・自動化
- 技術検証・PoC
- ツール整備・ワークフロー改善
- 新役職フォルダの自動生成

> **ルール：** ファイルを作成・更新するたびに必ず下の成果物ログに追記すること。

## 成果物ログ

| 日付 | ファイル名 | 種別 | 概要 | ステータス |
|------|-----------|------|------|-----------|
| 2026-05-06 | outputs/note_article_generator_prompt.md | プロンプト | note 集客記事の量産用プロンプト（Claude Pro 貼り付け運用） | 完了 |
| 2026-05-06 | outputs/note_article_scaffold.mjs | ツール | トピック JSON からスキャフォルド .md を自動生成（ゼロ依存） | 完了 |
| 2026-05-06 | outputs/topics/vol1_freelance_cashflow.json | 設定 | Vol.1 用トピック設定 | 完了 |
| 2026-05-06 | outputs/topics/vol2_sns_calendar.json | 設定 | Vol.2 用トピック設定 | 完了 |
| 2026-05-06 | outputs/topics/vol3_restaurant_prompts.json | 設定 | Vol.3 用トピック設定 | 完了 |

## 進行中タスク

- （なし）

## メモ・引き継ぎ事項

- **費用ゼロ運用ポリシー**：外部API・新規SaaS契約なし。Claude Pro チャット（既存契約 ¥3K/月）への貼り付け運用のみ。
- スクリプト実行例：`node CDO/outputs/note_article_scaffold.mjs --list`
- トピック追加時は `CDO/outputs/topics/<slug>.json` を作成すれば自動で利用可能
- 関連プロジェクト：`projects/2026-04-08_月30万自動化/C_テンプレ販売/`
