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
| 2026-04-08 | `server.mjs` | サーバ | agent-gateway 0.1.0（health/version/echo・依存ゼロ） | 完了 |
| 2026-04-08 | `pipeline_server.mjs` | サーバ | iPhone操作対応の柱Dパイプライン操作API | 完了 |
| 2026-04-08 | `projects/.../D_.../pipeline/00_session_setup.py` | スクリプト | 初回ログイン用セッション保存 | 完了 |
| 2026-04-08 | `projects/.../D_.../pipeline/01_search.py` | スクリプト | 案件検索（Crowdworks/Lancers・全リンクスキャン） | 完了 |
| 2026-04-08 | `projects/.../D_.../pipeline/02_evaluate.py` | スクリプト | 4軸スコアリング評価（APIキー無時はルールベース） | 完了 |
| 2026-04-08 | `projects/.../D_.../pipeline/03_apply.py` | スクリプト | 応募文生成（API/テンプレ二段構え） | 完了 |
| 2026-04-08 | `projects/.../D_.../pipeline/04_execute.py` | スクリプト | 作業実行（Excel/スクレイピング） | 完了 |
| 2026-04-08 | `projects/.../D_.../pipeline/05_review.py` | スクリプト | 念査・品質チェック | 完了 |
| 2026-04-08 | `projects/.../D_.../pipeline/06_deliver.py` | スクリプト | 納品文生成 | 完了 |
| 2026-04-08 | `projects/.../D_.../pipeline/run_pipeline.py` | スクリプト | パイプライン統合実行（search/deliver） | 完了 |
| 2026-04-08 | `projects/.../D_.../risk_and_feasibility.md` | 調査 | 規約・リスク・実現可能性レポート | 完了 |

## 進行中タスク

- 柱D：自動受注パイプラインの本番稼働（初回ログイン後の常時運用検証）

## メモ・引き継ぎ事項

- 柱Dは「初回ログインのみ人手」モデル。応募・納品ボタンの最終クリックは人手（規約配慮）。
- API キー未設定時もテンプレート評価／応募文で動作するフォールバックを実装済（`02_evaluate.py` / `03_apply.py`）。
- 機密ファイル保護は `.gitignore` で完了済（CFO/CSO の outputs・research・context/全体）。
