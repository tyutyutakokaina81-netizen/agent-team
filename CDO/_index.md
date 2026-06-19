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
| 2026-06-19 | ops/cowork_run.sh, ops/install_publish_schedule.sh | 自動化設定 | 日次自動公開を「安全ゲート付き」で設定。①本番公開ゲート（ops/PUBLISH_ENABLED無ければ--draft）②未来日付スキップ③冪等化。既定は本番公開OFF。launchd毎朝08:00。導入はオーナーがMacで実行 | 完了 |
| 2026-06-19 | outputs/note_publisher/publish_to_note.py | ツール強化 | 閲覧数回復策の一環。未来日付ガード（未来日付記事の自動公開を既定で禁止・--allow-futureで解除）＋冪等化（published_log.tsvで二重公開防止・--forceで解除）を実装。6/12インシデント再発防止＝再開条件②を充足 | 完了 |
| 2026-05-28 | outputs/note_publisher/ | 自動化ツール | note自動公開ヘルパー(Playwright・柱Dと同じ初回ログインのみ手動モデル)。オーナーのMacで実行 | MVP完成 |

## 進行中タスク

- note_publisher: 初回運用後にUIセレクタ調整が必要な可能性（noteのDOM変更追従）

## メモ・引き継ぎ事項

- note_publisherはCMO/outputs/の最新記事を自動選択。写真は ~/Pictures/note/YYYY-MM-DD/photo_NN.jpg 命名規則。
