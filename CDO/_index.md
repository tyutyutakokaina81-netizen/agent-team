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
| 2026-04-11 | `CDO/outputs/2026-04-11_autonomous_ai_spec.md` | 設計仕様書 | 自立型AI "Always-On Company" v0.1 設計仕様書。5役職AI日次ループ・budget_guard・orchestrator・Review Dashboard の段階的立ち上げ計画 | 策定済 |
| 2026-04-11 | `autonomous/budget_guard.mjs` | Node.js モジュール | Claude API 支出 hard limit 管理（1ループ¥30/1日¥100/1月¥2000）。canProceed/record/estimateYen/summary API | 実装済・未稼働試験 |
| 2026-04-11 | `autonomous/officer_runner.mjs` | Node.js モジュール | 1役職ぶんの1ターン実行。context/ideas を standing directive として毎ターン読込み、Claude API または dry-run モックで応答、成果物書き出し＋_index.md 追記＋task_queue 追加 | 実装済・未稼働試験 |
| 2026-04-11 | `autonomous/orchestrator.mjs` | Node.js モジュール | 5役職の日次ループ実行。事前予算チェック→各役職実行→日次サマリ→optional git commit/push。CLI: --commit/--push/--dry-run/--only | 実装済・未稼働試験 |
| 2026-04-11 | `autonomous/README.md` | ドキュメント | autonomous/ ディレクトリの構成表と各コンポーネントの使い方 | 策定済 |
| 2026-04-11 | `CDO/research/2026-04-11_dryrun_cdo.md` | dry-run 成果物 | officer_runner end-to-end 動作確認。モック応答をパース→ファイル書き出し→_index.md 追記→予算カウンタ更新まで正常動作 | パス |
| 2026-04-11 | `autonomous/state/budget/{daily,monthly}_spend.json` | 予算台帳 | budget_guard.mjs のクロスラン永続ストレージ（autonomous/state/ に配置、CFO/research/ は gitignore 対象のため移動済） | 初期化済 |
| 2026-04-11 | `context/ideas/2026-04-11_toyama_challenge_directive.md` | standing directive | オーナー指示「事業採算性 × 富山初」を自律ループの最優先 directive として捕捉。.gitignore 例外（`!*_directive.md`）で git 管理下 | 反映済 |
| 2026-04-11 | 2026-04-11_dryrun_cdo.md | dry-run | officer_runner 動作確認 | モック |

## 進行中タスク

- **Phase 1 コード実装は完了**。次は **稼働試験**（オーナー承認待ち）：
  - `node autonomous/budget_guard.mjs status` で状態確認
  - `node autonomous/orchestrator.mjs --dry-run --only CDO` で CDO 単独モック実行
  - `node autonomous/orchestrator.mjs --live --only CDO`（要 ANTHROPIC_API_KEY）で CDO 単独実 API 実行
  - `node autonomous/orchestrator.mjs --live --commit --push` で全役職 1 ループ完走＋自動コミット
- Phase 2 着手予定: `context_loader.mjs` の本格化／`memory.json` の短期記憶／ `task_queue.json` 運用確認
- Phase 3 着手予定: Review Dashboard（pipeline_server.mjs 拡張）
- Phase 4 着手予定: GitHub Actions ワークフロー（定期実行化）

## メモ・引き継ぎ事項

- **2026-04-11 方針転換**：「今月¥30K回収」を放棄、「自立型AI基盤構築月」に切替。収益 ¥0 前提。Claude API 追加支出は ¥2,000/月 hard limit
- **2026-04-11 オーナー standing directive**：「事業採算性」と「富山初」のキーワードで日々調査＆チャレンジ。`context/ideas/2026-04-11_toyama_challenge_directive.md` として捕捉済み。各役職はこれを毎ターン最優先で参照する
- 旧柱（A/B/C/D/E）は削除せず archival 保存。将来「接続点」を開く決断時に再活用
- **Phase 1 のハイライト**：zero-dep 実装（`fetch` / `node:fs` / `node:child_process` のみ）、dry-run モードで API キー不要の構造検証、3層 hard limit で暴走封じ込め
