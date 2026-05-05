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
| 2026-05-05 | `~/ai-auto/`（リポジトリ外） | L2/L3対応 | cw_apply に writer/ai_support/consultant の3カテゴリ追加・generate_seo_article.py / generate_proposal.py 新規・有料note既定¥2,980化・kpi.py に Level別売上分解・prompts/polish_prompts.md（無料Web AI 7プロンプト集）・SEOキーワード辞書追加 | 完了 |
| 2026-05-05 | `~/ai-auto/`（リポジトリ外） | Plan B 全自動 | _scheduler.py / _browser.py / auto_schedule.py / dispatcher.py / publish_note.py / post_x.py / post_reddit.py / apply_crowdworks.py / _note.py を新規。時間分散ランダム化＋人間挙動エミュレーション＋ DRY_RUN 既定。BANリスクは残るためPlanBは段階的有効化必須 | 完了 |
| 2026-05-05 | `~/ai-auto/` | リファクタ | publish_note._parse バグ修正（H1ベース）/ apply_crowdworks 提案数バグ修正（数値抽出）/ post_x 見出しスキップ＋CSV末尾読み / dead code削除 / _browser USER_DATA_DIR統一 / DRY_RUNでRuntimeError化 / docstring圧縮 | 完了 |
| 2026-05-05 | `projects/2026-05-05_AI自動収益化引き継ぎ/deploy/` | デプロイ | mac再現用パッケージ（28ファイル＋install.sh＋SETUP_PROMPT.md） | 完了 |
| 2026-05-05 | `~/ai-auto/ban_detector.py` `~/ai-auto/sunday_polish.py` | A案実装 | 朝9時にBAN検知（403/404/410/451）・日曜18時に高単価候補3本（有料note/SEO記事/提案書）を自動生成。SETUP_PROMPT.md にA案運用プロトコルとcron 4行を追記 | 完了 |

## 進行中タスク

- AI自動収益化引き継ぎ：cron常時稼働化（zsh環境前提・ローカル設定）
- AI自動収益化引き継ぎ：M2 開始時に L1 → L2 案件応募シフト（cw_apply --kind writer）
- AI自動収益化引き継ぎ：Plan B の段階的有効化（Reddit → X → note → CW の順、DRY_RUN試運転7日経てから本番化）

## メモ・引き継ぎ事項

- `~/ai-auto/` はローカル実行環境（リポジトリ外）。docxとビルダのみGit管理。
- 機微情報（.env / .cost_log.json / published.csv / outputs / logs）は `.gitignore` 済み。
- 完全自動投稿は規約リスクのため不採用。「生成→人間が公開→published.py で記録」運用を堅持。
- LLM日次予算は環境変数 `AI_DAILY_BUDGET_JPY`（既定 ¥100）。**推奨運用は API無効・無料Web AI 併用**で月額¥0。
- KPIは `python3 ~/ai-auto/kpi.py` で 7/30/90日の達成状況と Level別売上分解を確認可能。
- 原単位戦略：L1（実績作り3週間）→ L2（SEO記事・¥2,980note）→ L3（継続契約）の階段移行。
