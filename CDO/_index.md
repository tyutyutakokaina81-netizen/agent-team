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
| 2026-06-07 | docs/role-division.md | 役職管理 | 役割分担の正本。Claude Code=主(執筆含む全実務)／cowork=副(ネット/ブラウザ実行の代行)。ops/inbox連携・配信二段構え | 確定 |
| 2026-06-07 | ops/（inbox/processed/README） | 連携基盤 | code↔cowork の機械向け指示チャネル。疎通テスト001投函済 | 運用開始（疎通確認中） |
| 2026-06-06 | outputs/2026-06-06_役割分担_cowork×ClaudeCode.md | 役職管理 | 旧案（生成=cowork/検品=code）。docs/role-division.md に統合・上書き | 統合済（残置） |
| 2026-05-28 | outputs/note_publisher/ | 自動化ツール | note自動公開ヘルパー(Playwright・柱Dと同じ初回ログインのみ手動モデル)。オーナーのMacで実行 | MVP完成 |

## 進行中タスク

- note_publisher: 初回運用後にUIセレクタ調整が必要な可能性（noteのDOM変更追従）

## メモ・引き継ぎ事項

- note_publisherはCMO/outputs/の最新記事を自動選択。写真は ~/Pictures/note/YYYY-MM-DD/photo_NN.jpg 命名規則。
