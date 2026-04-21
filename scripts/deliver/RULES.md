# 受注→納品パイプライン 運用ルール＆エッジケース対応

このファイルは「イレギュラー発生時の行動規範」と「スクリプトの設計原則」を記録する。
新しいパイプライン作成時や既存改修時、**必ずこのルールに従うこと**。

---

## 🎯 パイプラインの基本原則

### 原則1: 安全第一（Fail-Safe）

- **未検証の入力はそのままファイルシステムに書き込まない**
- **必須項目の空欄は必ず拒否または再入力プロンプト**
- **ファイル操作前に必ず存在確認**
- **破壊的操作（削除・上書き）は連番付与で回避**

### 原則2: 冪等性（Idempotent）

- 同じ操作を何度実行しても結果は同じ
- 中断から再開できる（ステージ検出 → 次のアクション）
- ロックファイルで多重実行を防止
- 既存フォルダは連番付与で衝突回避

### 原則3: 透明性（Transparency）

- 失敗時は原因を明示（「❌ meta.json が不正なJSON: ...」）
- 警告と致命的エラーを区別（⚠️ / ❌）
- 処理内容を逐一ログ出力
- 隠れた副作用を作らない（ステージング追加は許可リスト方式）

### 原則4: 下位互換（Backward Compatibility）

- 古いフォーマットデータを自動マイグレーション
- 欠けたフィールドはデフォルト補完
- 新規フィールド追加時は既存データを壊さない
- バックアップを取ってから破壊的変更

---

## 📋 エッジケース対応チェックリスト

### A. 入力バリデーション

| ケース | 対応 |
|-------|------|
| 空欄入力 | `input_required()` で再入力プロンプト（3回まで） |
| 特殊文字（`<>:"\|?*`等） | `slugify()` / `sanitize_filename()` で除去 |
| 日本語のみの入力 | 長さを40文字で切り詰め・制御文字除去 |
| 非UTF-8エンコーディング | `UnicodeDecodeError` を捕捉し元ファイルをバックアップ |
| 異常に長い入力 | 最大長で切り詰め（client名40字、メモ500字等） |
| 数値に「円」「,」混入 | `safe_int()` で数字以外を除去 |
| 日付の形式揺れ | 複数フォーマット（-/_.）試行→ダメなら空欄 |
| 無効な選択肢 | 3回リトライ→失敗時exit 1 |

### B. ファイルシステム

| ケース | 対応 |
|-------|------|
| フォルダ名重複 | `unique_folder_name()` で連番付与（_2, _3...） |
| ファイル名重複 | `unique_path()` で連番付与 |
| 権限エラー | `PermissionError` を捕捉してエラーメッセージ |
| 読み込み権限なし | 早期return、処理スキップ |
| 書き込み失敗 | ステージングを`git reset HEAD`でクリア |
| 巨大ファイル（>50MB） | スキップ＋警告（`MAX_FILE_SIZE`定数） |
| 空ファイル（0バイト） | スキップ＋警告 |
| 対応外拡張子 | `VALID_EXTENSIONS` で絞り込み |
| 存在しないパス | `os.path.exists()` で事前確認 |

### C. JSON/CSVデータ

| ケース | 対応 |
|-------|------|
| meta.json 不在 | exit 1＋明示的なエラー |
| meta.json 壊れJSON | `JSONDecodeError` を捕捉 |
| 必須フィールド欠落 | `['client', 'job_title', 'job_type']` を検証 |
| CSV 旧フォーマット | `migrate_csv()` で自動変換＋バックアップ |
| CSV 無効ステータス | `VALID_STATUSES` 外は「応募」にフォールバック |
| CSV ロック中（Excel） | `PermissionError` を捕捉＋メッセージ |
| 数値変換失敗 | `safe_int()` で default 0 |

### D. Git操作

| ケース | 対応 |
|-------|------|
| gitリポジトリ外 | `.git` 存在確認＋exit 1 |
| detached HEAD | 検出して「checkout してください」 |
| git lock ファイル存在 | `.git/index.lock` 検出＋exit 1 |
| ネットワーク失敗 | 指数バックオフで3回リトライ（2s→4s→8s） |
| push失敗 | ローカルコミットは保持・手動pushの案内 |
| commit失敗 | `git reset HEAD` でステージング解除 |
| 機密ファイル混入 | 許可リスト方式で事前防止 |
| 非常に大きな変更 | ステージング件数を表示・確認可能に |

### E. 自動実行（launchd/cron）

| ケース | 対応 |
|-------|------|
| 同時実行 | PIDロックファイル（`.auto_morning.pid`） |
| 1日複数回実行 | 日付ロック（`.last_run_date`） |
| 実行途中で中断 | `trap 'rm -f "$PID_LOCK"' EXIT` で自動クリーンアップ |
| ログファイル肥大化 | 5000行超で末尾1000行に自動切り詰め |
| ステップ内で1つ失敗 | `|| echo "⚠️ 失敗"` で続行 |
| PC寝てた | launchd の `StartCalendarInterval` が次回起動時にキャッチアップ |

### F. 品質チェック（記事）

| ケース | 対応 |
|-------|------|
| drafts フォルダなし | `critical` エラー追加 |
| 複数下書き | 最大サイズのものをメインに（全ファイル処理） |
| キーワードが分割形 | 「副業 始め方」→「副業の始め方」もOK判定 |
| Markdown記号の繰り返し | `---` `###` 等を除外してチェック |
| 特殊なキーワード | タイトル検出で分割語マッチ |
| 短すぎる原稿 | 文字数チェックで`critical`警告 |
| 誇大表現 | 「絶対」「100%」等をパターンマッチ |

---

## 🚨 人間が判断すべきケース

以下はスクリプトで自動判定せず、必ず人間が判断する：

1. **納品前の最終品質確認** — AI補助でも最終判断は人間
2. **クライアントとのコミュニケーション** — 定型文以外
3. **単価交渉の可否** — クライアントの反応見て判断
4. **著作権・知財の譲渡範囲** — 契約時に確認
5. **怪しい案件の見極め** — 最終判断は人間
6. **応募辞退の判断** — 規約違反疑いなど
7. **修正依頼の範囲判定** — 追加料金発生するか

---

## 🔄 中断/再開ルール

### ケース1: 途中で中断

```bash
# 入力途中でCtrl+Cを押した
# → フォルダは作成されない（try/except KeyboardInterrupt）
```

### ケース2: プロンプト生成後に中断

```bash
# meta.jsonとprompts/は残っている
# 再開：
python3 scripts/deliver/run.py
# → 進行中案件として自動検出
```

### ケース3: Claudeが途中で失敗

```bash
# drafts/に部分的な原稿が残る
# → quality_check.py が文字数不足を検出
# → 該当部分だけ再生成してマージ
```

### ケース4: 納品後にクライアントから修正依頼

```bash
# meta.json の status を "revising" に変更
# drafts/ に修正版を保存
# package.py を再実行 → final/ に新バージョン
```

---

## 🧹 クリーンアップルール

### 日次クリーンアップ

- ログファイル5000行超→末尾1000行に
- PIDロック→完了時に削除（trap）
- `.last_run_date` → 翌日更新

### 月次クリーンアップ（手動）

```bash
# 1ヶ月以上前の納品済み案件をアーカイブ
# deliveries/YYYY-MM-DD_xxx → deliveries/_archive/YYYY-MM/

# CSVマイグレーションバックアップ削除（30日以上前）
find scripts/*.migration_backup -mtime +30 -delete
```

### 年次クリーンアップ（手動）

- 年度切替時に `deliveries/_archive/YYYY/` にまとめる
- 会計ソフトと照合して決算データ作成
- クライアントプロファイルを最新化

---

## 📐 新機能追加時のルール

### スクリプト作成チェックリスト

新規Pythonスクリプトを追加する際は以下を満たすこと：

```
□ シェバン `#!/usr/bin/env python3`
□ docstring（使い方・エッジケース対応）
□ 必須入力の検証（空欄拒否・型チェック）
□ ファイルパスの存在確認
□ try/except での例外捕捉
□ KeyboardInterrupt / EOFError の処理
□ 非0 exit コードでエラー通知
□ stderr と stdout の使い分け
□ 絶対パスで他スクリプトを参照（ディレクトリ非依存）
□ テストケースで動作確認
```

### シェルスクリプト作成チェックリスト

```
□ シェバン `#!/bin/bash`（zsh依存禁止）
□ `set -e` で即座エラー終了
□ 絶対パス解決 `$(cd "$(dirname "$0")/.." && pwd)`
□ gitリポジトリ検証
□ ロック機構（多重実行防止）
□ trap でクリーンアップ
□ リトライロジック（ネットワーク依存時）
□ 権限エラー・ファイル不在のハンドリング
```

---

## 🔐 セキュリティルール（絶対遵守）

### バックアップ時の許可リスト

`backup.sh` は明示的な許可リスト方式。以下のみコミット可能：

- `*.md`, `CLAUDE.md`, `company.md`, `README.md`
- `{CDO,CFO,CMO,CPO,CSO}/_index.md` `{CDO,CFO,CMO,CPO,CSO}/prompt.md`
- `CDO/outputs/*.md`, `CMO/outputs/*.md`, `CPO/outputs/*.md`
- `projects/**/*.md`, `projects/**/*.py`
- `scripts/*.{py,sh,md}`, `scripts/deliver/*.{py,sh,md}`
- `*.{mjs,js,plist,template,txt}`

### 絶対コミット禁止

- `**/auth-state.json`（認証セッション）
- `**/*_session.json`（あらゆるセッションファイル）
- `logs/*.png` `logs/*.json` `logs/*.log`
- `**/__pycache__/`, `*.pyc`
- `**/node_modules/`, `package-lock.json`
- `scripts/applications.csv`（個人データ）
- `scripts/dashboard.html`（個人データ含む）
- `deliveries/*`（クライアント情報含む）

### 機密ファイル発見時の手順

1. `.gitignore` に追加
2. `git rm --cached <ファイル>`
3. 必要なら `git filter-branch` で履歴から削除
4. force push で上書き
5. 該当サービスのセッション無効化（note.com等）

---

## 🧪 テストルール

### 新機能追加後の確認

```
1. 正常系（典型的な入力）
2. 境界値（最小・最大・0）
3. 異常系（空欄・特殊文字）
4. 中断（Ctrl+C）
5. 再実行（冪等性確認）
```

### デモ実行で確認

```bash
./scripts/deliver/demo_full_pipeline.sh
# → 全工程がエラーなく完走すること
```

---

## 📝 運用フロー定義

### 受注したら

```
1. python3 scripts/deliver/new_job.py  # 受注情報入力
2. python3 scripts/deliver/generate.py "<folder>"  # プロンプト生成
3. python3 scripts/deliver/timer.py start "<folder>"  # 時間計測開始（任意）
4. Claudeでプロンプト実行 → drafts/ に保存
5. python3 scripts/deliver/quality_check.py "<folder>"  # 品質チェック
6. python3 scripts/deliver/timer.py stop "<folder>"  # 時間計測終了
7. python3 scripts/deliver/package.py "<folder>"  # 納品パッケージ
8. delivery_email.txt を編集して送信
9. 検収後、請求書発行・入金確認
10. python3 scripts/application_tracker.py で受注登録
```

### 毎朝（PC開いたとき）

```
dashboard.html が自動で開く
→ 昨夜の自動実行結果を確認
→ 今日の優先タスクを決定
```

### 毎晩（20:00 or PC起動時）

```
auto_morning.sh が自動実行
→ pull → daily_report → dashboard生成 → backup
→ dashboard.html が自動で開く
```

---

## 🎯 イレギュラー対応マニュアル

### 「応募トラッカーが動かない」

```
1. CSV が Excel で開かれていないか確認
2. python3 scripts/application_tracker.py → 自動マイグレーション
3. .migration_backup ファイルが作成されていれば移行成功
```

### 「auto_morning が走らない」

```
1. launchctl list | grep agent-team で登録確認
2. tail -50 ~/agent-team/logs/cron.log でログ確認
3. rm ~/agent-team/logs/.last_run_date で日付ロック解除
4. launchctl start com.user.agent-team.morning で手動実行
```

### 「backup が push できない」

```
1. git status でローカル状態確認
2. 3回リトライしても失敗 → ネットワーク確認
3. ローカルコミットは保持されているので、後で手動 git push
```

### 「deliver パイプラインが中断した」

```
1. python3 scripts/deliver/run.py
2. 進行中案件を選択 → 次のアクションが自動提示される
3. 再開：指示通りに次のステップを実行
```

### 「誤って機密ファイルをコミット」

```
1. git rm --cached <ファイル>
2. .gitignore に追加
3. git commit -m "security: 機密ファイル追跡解除"
4. 重大な場合：git filter-branch で履歴から削除
5. force push で上書き
6. 該当サービスのセッション無効化
```

---

## 🔄 定期レビュー

このRULESは以下のタイミングでレビュー：

- **月1回**：実運用で発見したエッジケースを追加
- **新機能追加時**：影響範囲を検証
- **重大バグ発生時**：即座に対応ルール化

---

## 📚 関連ドキュメント

- `scripts/deliver/README.md` - パイプライン使い方
- `CLAUDE.md` - プロジェクト全体の運用ルール
- `projects/2026-04-08_月30万自動化/PLAYBOOK.md` - 収益化の全体戦略
- `company.md` - 会社共通ルール

---

*Last updated: 2026-04-21*
*イレギュラーケース追加時はこのファイルを必ず更新*
