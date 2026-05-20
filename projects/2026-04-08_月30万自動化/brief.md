# プロジェクト：月30万自動化

## 目標
AIを活用した合法的な収益自動化で月30万円を達成する

## 期間
3ヶ月（2026-04〜2026-06）

## 3本柱（並列実行）

| モデル | 目標単価 | 目標件数 | 月収 | 担当役職 |
|--------|---------|---------|------|---------|
| A：SEOライティング | 1.5万円/記事 | 20記事 | 30万 | CSO・CMO・CDO |
| B：SNS運用代行 | 5万円/社 | 6社 | 30万 | CMO・CSO・CDO |
| C：テンプレ販売 | 5,000円/本 | 60本 | 30万 | CPO・CMO・CDO |

## ステータス
- [x] A：サービス設計完了（`A_ライティング/service_design.md`）
- [x] A：受注ワークフロー構築（`A_ライティング/order_workflow.md` 2026-05-19）
- [x] B：サービス設計完了（`B_SNS運用代行/service_design.md`）
- [x] B：提案文作成（`B_SNS運用代行/proposal_templates.md`）
- [x] C：テンプレ第1弾リリース（Vol.1 noteで販売中）
- [x] C：販売ページ公開（Vol.1 `C_テンプレ販売/vol1_note_listing.md`）

## 次の重点アクション（2026-05-19 時点）
- [ ] A：クラウドワークス／ランサーズで日次応募開始（Month 2 で12本受注）／`A_ライティング/order_workflow.md`
- [ ] B：1社目契約獲得（Month 2 目標：1社×¥50K）／`B_SNS運用代行/sales_playbook.md`
- [x] C：Vol.2 SNSカレンダー 制作完了（note公開待ち）／`C_テンプレ販売/vol2_sns_calendar.md`
- [ ] C：Vol.2 note公開（owner作業：スプレッドシート実物作成・PDF化）
- [x] C：Vol.3 飲食店向けプロンプト集 制作完了（PDF化＆公開待ち）／`C_テンプレ販売/vol3_prompt_collection_restaurant.md`
- [ ] C：Vol.3 note公開（owner作業：PDF化）
- [x] C：Vol.4 バンドルパック 設計完了（特典3点・販売ページ・スケジュール）／`C_テンプレ販売/vol4_bundle_pack.md`
- [ ] C：Vol.4 note公開（owner作業：特典PDF制作・スプレッドシート制作）
- [x] C：Vol.5 士業向けプロンプト集 制作完了（20プロンプト＋コンプラチェックリスト）／`vol5_prompt_collection_shigyo.md`
- [x] C：Vol.6 美容院・ネイル・サロン向けプロンプト集 制作完了（20プロンプト＋撮影ガイド）／`vol6_prompt_collection_beauty.md`
- [ ] C：Vol.5・Vol.6 note公開（owner作業：PDF化）
- [x] CMO：Vol.1〜4 リリース告知SNS投稿セット（4波×3媒体）／`launch_sns_posts.md`
- [x] CSO：業種別商談ヒアリングシート5業種版／`hearing_sheets_by_industry.md`
- [x] CDO：月次レポート拡張（C連携・Slack通知・cron運用）／`CDO/outputs/scripts/monthly_report.mjs`
- [x] CDO：入金督促・契約更新アラートスクリプト／`CDO/outputs/scripts/payment_alerts.mjs`
- [x] CFO：取引先管理マスターテンプレ／`CFO/templates/2026-05-19_取引先管理マスター_テンプレ.md`
- [x] CMO：Vol.4 バンドル LP構成（独自LP用）／`C_テンプレ販売/vol4_landing_page.md`
- [x] CSO：失注分析テンプレ＋月次集計フロー／`B_SNS運用代行/loss_analysis_template.md`

## CDOツール整備
- [x] 月次レポート自動生成スクリプト（`CDO/outputs/scripts/monthly_report.mjs`）
- [x] A受注／B営業／経費 の3CSVを集計して月次サマリを生成

## A 受注体制
- [x] 受注運用ワークフロー v1（`A_ライティング/order_workflow.md`）
- [x] 構成案プロンプト v2 実例付き（`A_ライティング/prompt_outline_v2.md`）
- [ ] クラウドワークス／ランサーズで応募開始

## B 営業体制
- [x] 営業プレイブック（`B_SNS運用代行/sales_playbook.md`）
- [x] 業種別ターゲットリスト50件作成ガイド（`B_SNS運用代行/target_list_50.md`）
- [ ] CSO：50件の実データ収集（CSO/outputs/）
