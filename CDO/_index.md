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
| 2026-06-22 | ops/auto_company/guard_checks.py | 監視ツール | 無人ガーディアン。重複/未来日付/テスト/台帳整合/センシティブを決定論検出(API課金ゼロ)。初回稼働で未来日付1・重複11・台帳未記載74を即検出 | 完成・稼働 |
| 2026-06-22 | ops/auto_company/revenue_ledger.py | 採算ツール | sales.csvから採算表自動生成(売上−手数料＝純利益・Phaseゲート)。CFO工程⑥ | 完成 |
| 2026-06-22 | ops/auto_company/build_gumroad_pack.py | 出品ツール | 商品mdから制作ノート除去の配布用クリーン版を生成(流出防止) | 完成 |
| 2026-06-22 | .github/workflows/auto-company-guardian.yml | 無人監視 | push時＋毎朝7時にguard_checksを自動実行(Actions無料枠・API課金ゼロ) | 完成・稼働 |

## 進行中タスク

- note_publisher: 初回運用後にUIセレクタ調整が必要な可能性（noteのDOM変更追従）
- 【監視体制・常設】guardが検出した赤(未来日付1/重複11/台帳未記載74)の棚卸し。削除/統合は人間ゲート(要オーナー確認)

## メモ・引き継ぎ事項

- note_publisherはCMO/outputs/の最新記事を自動選択。写真は ~/Pictures/note/YYYY-MM-DD/photo_NN.jpg 命名規則。
