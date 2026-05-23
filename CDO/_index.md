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
| 2026-05-23 | 2026-05-23_Skills機能設計メモ.md | research | Claude Code Skills（事業評価／カリキュラム設計）のローカル実装方針 | 下書き |
| 2026-05-23 | outputs/skills/business/SKILL.md | スキル（canonical） | CPOメソッド5ステップ実行コマンド。引数で price/sim/compare/score の個別実行も可 | 運用 |
| 2026-05-23 | outputs/skills/curriculum/SKILL.md | スキル（canonical） | カリキュラム・プログラム設計コマンド | 運用 |
| 2026-05-23 | outputs/skills/install.sh | インストーラ | SKILL.md を `.claude/commands/` にコピーする運用スクリプト | 運用 |

## 進行中タスク

- 柱Bの解約防止KPIダッシュボード設計（期日2026-05-30）
- GA4／Search Console MCP導入検証（CMOガイド連動）

## メモ・引き継ぎ事項

- 関連：CPO `CPO/research/2026-05-23_CPOメソッド_ClaudeCode活用ガイド.md`（起点ドキュメント）
- **Skills運用ルール**：canonical版を `CDO/outputs/skills/` で管理し、ローカル実行版は `install.sh` で `.claude/commands/` に展開する（`.claude/` は gitignore 対象のため）
