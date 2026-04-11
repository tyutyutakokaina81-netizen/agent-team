# autonomous/

自立型AI "Always-On Company" のコア実装ディレクトリ。

5役職AI（CDO/CFO/CMO/CPO/CSO）が日次ループで自律稼働するための土台。

## 設計ドキュメント

- `CDO/outputs/2026-04-11_autonomous_ai_spec.md` — 全体設計仕様書 v0.1
- `projects/2026-04-08_月30万自動化/brief.md` — 2026-04-11 方針転換版プロジェクトブリーフ

## 構成要素

| ファイル | 役割 | 状態 |
|---------|------|------|
| `budget_guard.mjs` | Claude API 支出の hard limit 管理（第一防衛線） | **Phase 1: 実装済・動作確認済** |
| `officer_runner.mjs` | 1役職ぶんの1ターン実行。context/standing directive / 短期記憶 / task_queue を統合 | **Phase 1+2: 実装済・動作確認済** |
| `orchestrator.mjs` | 5役職のターンを順に回すメインループ。自動 commit/push オプション | **Phase 1: 実装済・動作確認済** |
| `memory.mjs` | 各役職の短期・長期記憶（`state/memory/<officer>.json`） | **Phase 2: 実装済・動作確認済** |
| `dashboard.mjs` | 閲覧専用ダッシュボードサーバー（zero-dep HTTP） | **Phase 3: 実装済・smoke-test 済** |
| `state/` | クロスラン永続ストレージ（予算／記憶／task_queue） | **Phase 1-2: 運用中** |
| `.github/workflows/autonomous_loop.yml` | GitHub Actions ワークフロー（dormant） | **Phase 4: 実装済・未起動** |

## 安全装置（迷惑を起こさない設計）

| 装置 | 効果 |
|------|------|
| 3層 hard limit（¥30/loop, ¥100/day, ¥2K/month） | 暴走で月額予算を超過することが物理的に不可能 |
| `mode=auto` が APIキー無しなら dry-run に fallback | 意図せず live 実行される事故を防ぐ |
| GitHub Actions は `workflow_dispatch` のみ有効（`schedule` は**コメントアウト済**） | オーナーが明示的に有効化しない限り自動実行されない |
| 全ての成果物・状態変更は Git commit 対象 | 任意時点へロールバック可能 |
| 外部プラットフォームへの投稿・応募・契約は一切なし | ToS・法的リスクゼロ |
| task_queue は役職間のメッセージングのみ（外部通信なし） | 情報漏洩リスクなし |

## CLI リファレンス

### 予算確認
```bash
node autonomous/budget_guard.mjs status
node autonomous/budget_guard.mjs check 25
node autonomous/budget_guard.mjs simulate 1200 800 claude-haiku-4-5
```

### 役職記憶の確認
```bash
node autonomous/memory.mjs summary             # 全役職のサマリ
node autonomous/memory.mjs show CDO            # CDO の記憶全文
node autonomous/memory.mjs compress CDO 2026-04  # 月次圧縮
```

### 単一役職のターン実行
```bash
node autonomous/officer_runner.mjs CDO           # auto モード
node autonomous/officer_runner.mjs CDO dry-run   # 強制 dry-run
node autonomous/officer_runner.mjs CDO live      # 強制 live（要 ANTHROPIC_API_KEY）
```

### 全役職1ループ
```bash
node autonomous/orchestrator.mjs --dry-run              # 全役職 dry-run
node autonomous/orchestrator.mjs --dry-run --only CDO   # CDO だけ dry-run
node autonomous/orchestrator.mjs --live --commit        # live 実行＋自動 commit
node autonomous/orchestrator.mjs --live --commit --push # さらにリモートに push
```

### ダッシュボード起動
```bash
node autonomous/dashboard.mjs                  # 3002 番で起動
DASHBOARD_PORT=8080 node autonomous/dashboard.mjs  # ポート変更
```

ブラウザで `http://localhost:3002/` を開くと閲覧専用ダッシュボード：
- 予算サマリ（プログレスバー）
- 各役職の短期記憶（最新の決定）
- task_queue 中身
- 直近のループサマリ（折りたたみ）

## hard limit 一覧

| 階層 | 上限 |
|------|------|
| 1ループあたり | ¥30 |
| 1日あたり | ¥100 |
| 1月あたり | ¥2,000 |

これらは `budget_guard.mjs` の `CONFIG` オブジェクトで集中管理。変更は Git で追跡される。

## クロスラン永続ストレージ `state/`

- `state/budget/daily_spend.json` — 日次支出記録
- `state/budget/monthly_spend.json` — 月次支出記録
- `state/memory/<officer>.json` — 各役職の短期・長期記憶
- `state/task_queue.json` — 役職間メッセージキュー

**注**: `CFO/research/` や `CSO/research/` は `.gitignore` 対象（機密用途）。
**一方**、`autonomous/state/` は git 管理下で、GitHub Actions / ローカル / 他環境の間で状態を共有する。
機密情報は絶対に置かないこと。

## standing directive （context/ideas/*_directive.md）

オーナーからの常駐指示は `context/ideas/` に `*_directive.md` というファイル名で配置する。
これは `.gitignore` の例外ルール（`!context/ideas/*_directive.md`）で git 管理下に置かれ、
officer_runner.mjs が毎ターン最優先で読み込み、全役職の system prompt に注入される。

現在の standing directive:
- `context/ideas/2026-04-11_toyama_challenge_directive.md` — 「事業採算性 × 富山初」の日々調査＆チャレンジ

## GitHub Actions ワークフロー (dormant)

`.github/workflows/autonomous_loop.yml` は **休眠状態** で配置されている：

- `schedule` triggerは全てコメントアウト
- `workflow_dispatch`（手動トリガ）のみ有効
- 定期実行したい場合はオーナーが明示的に schedule 行のコメントを外す必要がある
- `ANTHROPIC_API_KEY` が secret に無ければ dry-run に自動 fallback

手動起動:
```bash
gh workflow run autonomous_loop.yml                # dry-run（デフォルト）
gh workflow run autonomous_loop.yml -f mode=live   # live 実行
```

## 原則

1. **上限超過は失敗ではなく正常終了** — 呼び出し側は exit 0 で終わる
2. **全ての支出は `autonomous/state/budget/` に Git コミット** — 透明性担保
3. **人間の介入は不要** — 暴走しない設計が全責任
4. **オーナーに迷惑をかけない** — 外部アカウント・契約・投稿・顧客接触は一切なし
