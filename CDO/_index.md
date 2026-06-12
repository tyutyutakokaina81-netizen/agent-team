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
| 2026-05-28 | outputs/note_publisher/ | 自動化ツール | note自動公開ヘルパー(Playwright・柱Dと同じ初回ログインのみ手動モデル)。オーナーのMacで実行 | MVP完成 |
| 2026-06-12 | outputs/note_publisher/ ほか | バグ修正 | プログラム監査で検出した綻びを一括修正：publish_all.sh(消滅ブランチ直書き→main・pipefail)／publish_to_note.py(同日5本順次公開・公開済みログで二重投稿防止・バッチ時input待ち解消・終了コード)／prepare_photos.py(--by-date引き継ぎ)／pipeline_server.mjs(トークン必須化・全ルート認証・XSS対策)／server.mjs(ボディ上限・二重レスポンス防止)／inject_js/34本削除 | 完了 |

## 進行中タスク

- note_publisher: 初回運用後にUIセレクタ調整が必要な可能性（noteのDOM変更追従）

## メモ・引き継ぎ事項

- note_publisherのデフォルトは「ファイル名日付=本日（無ければ次の未来日付）の全記事を順次公開」。公開済みは .published.log でスキップ。写真は ~/Pictures/note/YYYY-MM-DD/photo_NN.jpg 命名規則（prepare_photos.py が --by-date を自動で引き継ぐ）。
- publish_all.sh の pull 先ブランチは main（環境変数 PUBLISH_BRANCH で変更可）。
- pipeline_server.mjs は PIPELINE_TOKEN 未設定だと起動しない（全ルート認証必須）。
