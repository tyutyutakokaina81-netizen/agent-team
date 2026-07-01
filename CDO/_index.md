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
| 2026-07-01 | outputs/note_publisher/check_thumbnail_coverage.py, 2026-07-01_サムネ監視_運用手順.md | 監視/運用 | サムネ取りこぼし監視の定例化。記事×thumbnails/*.jpg×_provenance.json(GOOD_BACKENDS)を突合し未取得一覧と充足率を出す読み取り専用スクリプト(依存ゼロ・ネット不要)＋週1/記事追加後にnote-thumbnails.ymlをworkflow_dispatch再実行で自己修復する手順。初回集計=144本中104本(72.2%) | 完了 |
| 2026-06-29 | 2026-06-29_note記事_検索最適化チェックリスト.md | 書式/ガイド | 今後のnote記事を最初から検索最適化で作る恒久標準（タイトル/冒頭/見出し/タグ/回遊/英語/事実検証）。過去記事手編集に頼らず新規が放置で流入を取る。L1標準化版 | 完了 |
| 2026-05-28 | outputs/note_publisher/ | 自動化ツール | note自動公開ヘルパー(Playwright・柱Dと同じ初回ログインのみ手動モデル)。オーナーのMacで実行 | MVP完成 |
| 2026-06-23 | apps/invoice-generator/index.html, README.md | Webツール | 依存ゼロ単一HTMLの請求書ジェネレーター(localStorage保存・印刷PDF・インボイス注記・商品リンク/ad slot)。GitHub Pages公開可。検索流入×テンプレ商品の相互送客フック付き | 完成 |

## 進行中タスク

- note_publisher: 初回運用後にUIセレクタ調整が必要な可能性（noteのDOM変更追従）

## メモ・引き継ぎ事項

- note_publisherはCMO/outputs/の最新記事を自動選択。写真は ~/Pictures/note/YYYY-MM-DD/photo_NN.jpg 命名規則。
