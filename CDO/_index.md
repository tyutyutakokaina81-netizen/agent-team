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
| 2026-06-23 | apps/invoice-generator/index.html, README.md | Webツール | 依存ゼロ単一HTMLの請求書ジェネレーター(localStorage保存・印刷PDF・インボイス注記・商品リンク/ad slot)。GitHub Pages公開可。検索流入×テンプレ商品の相互送客フック付き | 完成 |
| 2026-07-23 | projects/2026-04-08_月30万自動化/D_エクセル入力スクレイピング/templates/2026-07-23_claudecode指示書_python自動収集.md | プロンプト/テンプレ | 柱D案件用「Claude Codeにコピペで渡せるPythonデータ収集指示書」。静的(requests+bs4)/動的(Selenium)の使い分け・[ ]穴埋め式・規約/robots.txt/PII禁止のコンプラ節・Excel転記のみ版・設計レビュー別AI連携の任意節つき | 完成 |

## 進行中タスク

- note_publisher: 初回運用後にUIセレクタ調整が必要な可能性（noteのDOM変更追従）

## メモ・引き継ぎ事項

- note_publisherはCMO/outputs/の最新記事を自動選択。写真は ~/Pictures/note/YYYY-MM-DD/photo_NN.jpg 命名規則。
