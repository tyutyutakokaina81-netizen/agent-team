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
| 2026-05-05 | `projects/2026-05-05_AI自動収益化引き継ぎ/outputs/claude_code_handover.docx` | 引き継ぎ書 | Claude Code向け15章構成の完全版引き継ぎ書（A4・実務提出レベル） | 完了 |
| 2026-05-05 | `projects/2026-05-05_AI自動収益化引き継ぎ/build_handover_docx.py` | スクリプト | 上記docxを再生成するためのpython-docxビルダ | 完了 |
| 2026-05-05 | `~/ai-auto/`（リポジトリ外） | 実行基盤 | run.sh / generate_daily_outputs.py / generate_note.py / generate_reddit.py / generate_youtube_short.py / generate_paid_note.py / cw_apply.py / auto_post.py / prompts/ / .env.example を新規配置 | 完了 |
| 2026-05-05 | `projects/2026-05-05_AI自動収益化引き継ぎ/build_handover_docx.py` | リファクタ | style_run ヘルパ・定数化・コメント整理で 647 → 604 行 | 完了 |
| 2026-05-05 | `~/ai-auto/`（リポジトリ外） | 機能拡張 | テーマローテ（prompts/themes.json）・published.csv記録・kpi集計・LLMラッパ（_ai.py、コストガード）・cw_apply --from-json 対応・run.sh拡張 | 完了 |

## 進行中タスク

- AI自動収益化引き継ぎ：cron常時稼働化（zsh環境前提・ローカル設定）
- AI自動収益化引き継ぎ：実運用での API 利用開始（.env に ANTHROPIC_API_KEY 設定）

## メモ・引き継ぎ事項

- `~/ai-auto/` はローカル実行環境（リポジトリ外）。docxとビルダのみGit管理。
- 機微情報（.env / .cost_log.json / published.csv / outputs / logs）は `.gitignore` 済み。
- 完全自動投稿は規約リスクのため不採用。「生成→人間が公開→published.py で記録」運用を堅持。
- LLM日次予算は環境変数 `AI_DAILY_BUDGET_JPY`（既定 ¥100）。超過時は自動でテンプレフォールバック。
- KPIは `python3 ~/ai-auto/kpi.py` で 7/30/90日の達成状況を確認可能。
