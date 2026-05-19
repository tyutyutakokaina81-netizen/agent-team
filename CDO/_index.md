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
| 2026-05-19 | `projects/2026-04-08_月30万自動化/A_ライティング/order_workflow.md` | 運用設計 | A：SEOライティング受注運用ワークフロー（7ステップ・Claudeプロンプト・品質チェック含む） | 完了 |
| 2026-05-19 | `projects/2026-04-08_月30万自動化/A_ライティング/order_tracker_template.csv` | テンプレ | 受注管理シート（Googleスプレッドシート用CSV） | 完了 |
| 2026-05-19 | `CDO/outputs/scripts/monthly_report.mjs` | スクリプト | A受注／B営業／経費の3CSVを集計して月次サマリmdを生成（依存ゼロ・Node 18+） | 完了 |
| 2026-05-19 | `CDO/outputs/docs/2026-05-19_月次レポート生成ツール.md` | ドキュメント | 月次レポート生成ツールの使い方・CSV仕様・拡張案 | 完了 |
| 2026-05-19 | `projects/2026-04-08_月30万自動化/A_ライティング/prompt_outline_v2.md` | プロンプト設計 | A：SEO構成案プロンプト v2（実例付き・自己チェック5項目組込） | 完了 |
| 2026-05-19 | `CDO/outputs/scripts/monthly_report.mjs` v2 | スクリプト | C テンプレ販売CSV対応・Slack Webhook通知・cron運用例を追加 | 完了 |
| 2026-05-19 | `CDO/outputs/scripts/sample_c_sales.csv` | サンプル | C テンプレ販売の集計用CSVサンプル | 完了 |

## 進行中タスク

- （なし）

## メモ・引き継ぎ事項

- CSOへ：`order_workflow.md` の Step1（応募基準・応募文）と Step2（キックオフ）を実運用で使用してください。改善点はワークフロー末尾の `改善ログ` 表に追記します。
- CMOへ：Step3〜5は v2 構成案プロンプト（`prompt_outline_v2.md`）を使用してください。v1からの改善点は同ファイル末尾参照。
- CFOへ：請求書・契約書・経費管理テンプレは整備済（`CFO/templates/`）。月次レポートは `monthly_report.mjs` で自動生成可能。
- 月次レポート使用法：毎月初に `node CDO/outputs/scripts/monthly_report.mjs YYYY-MM --out=CFO/outputs/YYYY-MM_月次サマリ.md` を実行。
