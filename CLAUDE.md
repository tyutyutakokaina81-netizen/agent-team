# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

AI 運営の多役職カンパニー雛形。月収 ¥300K の自動化事業を構築する。
5 つの C?O 役職（CDO / CFO / CMO / CPO / CSO）がそれぞれ独立した作業ログ・調査・成果物を保有する。
**すべての文書・運用出力は日本語**で行う（コードのコメントも基本日本語）。

---

## 必読ドキュメント（作業開始前）

1. `company.md` — 会社共通ルール・役職定義・新役職生成ルール（**正典**）
2. `context/` — オーナーの一次情報（diary / ideas / references）。意図と背景を把握する
3. 担当役職の `_index.md` — 過去の成果物・進行中タスクの台帳

CLAUDE.md と `company.md` で記述が衝突した場合は `company.md` を優先する。

---

## Repository Map

```
agent-team/
├── company.md                ← 会社共通ルール（正典）
├── server.mjs                ← agent-gateway: 依存ゼロ JSON API（health/version/echo）
├── pipeline_server.mjs       ← 案件パイプライン操作サーバー（iPhone HTML パネル + Python 起動）
├── team_prompt.txt           ← 4 役マルチエージェント文書作成プロンプト
├── team_copy.sh / team_show.sh
├── CDO/ CFO/ CMO/ CPO/ CSO/  ← 各役職: _index.md / prompt.md / research/ / outputs/
├── context/                  ← diary/ ideas/ references/（gitignore 対象）
└── projects/                 ← 役職横断ワーク
    └── 2026-04-08_月30万自動化/  ← 現行のメインプロジェクト（A〜D の柱）
```

役職配下は共通で `_index.md` + `prompt.md` + `research/` + `outputs/` の 4 点構成。
柱 D の Python パイプラインだけが本リポジトリで唯一のコード資産（後述）。

---

## ファイル管理（運用上の絶対ルール）

- **命名**: `YYYY-MM-DD_ファイル名.md` の日付プレフィックス必須
- **下書き → `research/`、確定版 → `outputs/`**
- **`_index.md` への追記は必須**: ファイルを作成・更新したら必ず該当役職の表に追記する
  - 列: `| 日付 | ファイル名 | 種別 | 概要 | ステータス |`
  - 完了タスクは削除せずステータスのみ更新する
  - 他役職の成果物を参照したらメモ欄に参照元を書く
  - **CFO は `_index.md` に金額を記載しない**（ファイル名のみ）
- **複数役職が関与するタスクは `projects/` に切り出し**、`projects/_index.md` の表に追記
  - サブフォルダは役職別（`CMO/` `CPO/`）かテーマ別（`A_〇〇/` `B_〇〇/`）から自然な方を選ぶ
  - `brief.md` に目的・関与役職・サブフォルダ構成の理由を残す

### Git に乗らないもの（`.gitignore` の重要な部分）

- `CFO/outputs/*`, `CFO/research/*`, `CSO/outputs/*`, `CSO/research/*` — 機密（請求書・契約・PII・商談ログ）
- `projects/*/D_エクセル入力スクレイピング/outputs/*` と `.sessions/*` — 納品前成果物・セッション情報
- `context/diary/*`, `context/ideas/*`, `context/references/*` — オーナー個人情報
- `*_secret*`, `*_confidential*`, `*_機密*`, `*_秘密*`
- フォルダ構造は `.gitkeep` で維持されている

→ ローカルに存在しても `git status` に出ないファイルが多数ある前提で動く。コミットしようとして除外されても異常ではない。

---

## 役職と責務

| 役職 | 担当 | 主な成果物 |
|------|------|-----------|
| CDO | 自動化・プロンプト設計・技術検証・役職管理 | プロンプト集、ツール、ガイド |
| CFO | 数字・契約・経費・事務 | 請求書、契約書、財務サマリ |
| CMO | マーケ・コンテンツ企画・集客 | YouTube 台本、SNS、LP |
| CPO | 教育コンテンツ・プロダクト設計 | スライド、テンプレ、手順書 |
| CSO | 顧客対話・営業・パイプライン | 提案書、対話ログ、FAQ |

**新役職の自動生成は CDO 権限**（承認不要）。条件・手順は `company.md` を参照。生成後は `company.md` のディレクトリ表を更新し、オーナーに事後報告する。

---

## コード資産と起動コマンド

ビルド工程・テストフレームワーク・依存パッケージは **存在しない**。すべて Node 標準モジュールと Python 3 標準ライブラリで動く。`package.json` も無い。

### `server.mjs` — agent-gateway（最小 JSON API）

```bash
node server.mjs            # PORT=3000 でリッスン
PORT=8080 node server.mjs
```

エンドポイント:
- `GET /health` → `{ ok: true, time: ISO }`
- `GET /version` → `{ name: "agent-gateway", version: "0.1.0" }`
- `POST /echo` → 受信 JSON を返す（不正 JSON は 400）
- 他は 404
- ログは `METHOD /path STATUS 処理時間ms` を stdout に出す

### `pipeline_server.mjs` — 案件パイプライン操作サーバー（iPhone 用）

```bash
PIPELINE_TOKEN=xxxxx node pipeline_server.mjs    # 認証必須（未設定だと警告のみで起動するが本番不可）
PIPELINE_PORT=3001 node pipeline_server.mjs       # デフォルト 3001
```

`HOST=0.0.0.0` でリッスンし、iPhone 等の外部端末から HTML 操作パネル (`GET /`) を開ける。トークンは `Authorization: Bearer <TOKEN>` または `?token=<TOKEN>` クエリで渡す。

エンドポイント:
- `GET /` → iPhone 用 HTML 操作パネル（status / 検索開始 / 納品開始 / 結果表示 / ログ）
- `GET /status` → 稼働状況（認証不要）
- `POST /search` → `python3 run_pipeline.py search` をバックグラウンド起動
- `POST /deliver` → `python3 run_pipeline.py deliver` をバックグラウンド起動
- `GET /results` → `outputs/` 内で最新の `*_evaluated.json` または `*_applications.json` を返す

`state.status` は `idle | running | done | error`。同時実行は 409 で弾く。サーバー単体では何もせず、配下の Python スクリプトに処理を委譲する。

### 柱 D の Python パイプライン

`projects/2026-04-08_月30万自動化/D_エクセル入力スクレイピング/pipeline/`:

```
run_pipeline.py         ← search / deliver サブコマンドのディスパッチャ
00_session_setup.py     ← セッション・出力先準備
01_search.py            ← クラウドソーシング案件検索
02_evaluate.py          ← GO / CAUTION / NO-GO の自動評価
03_apply.py             ← 応募文生成
04_execute.py           ← 受注後の作業
05_review.py            ← 念査
06_deliver.py           ← 納品文生成
```

Python 単体実行は **必ず事前承認**（後述「行動方針」）。`pipeline_server.mjs` を経由した場合のみ自動的に `cwd=PIPELINE_DIR` で実行される。

### Shell scripts

- `team_copy.sh` — `team_prompt.txt` を `pbcopy` でクリップボードへ（macOS 前提）
- `team_show.sh` — `team_prompt.txt` を stdout へ
- いずれも `#!/bin/zsh` + `set -e`、リポジトリパスを `$HOME/agent-team/` で参照

`team_prompt.txt` 自体は 4 役（企画 → 本文 → 要約 → チェック）のマルチエージェント文書作成プロンプト。

---

## 報告ルール

### 出力フォーマット（必須）

1. **要点** — 結論・変更サマリを最初に
2. **詳細** — 根拠・実装内容・補足
3. **次アクション** — オーナーが取るべき手順や選択肢

### 事実と意見の分離

```
【事実】先月の YouTube 登録者は 1,200 人増。
【考察】週 2 回投稿の影響と推定。
【提案】同頻度を維持し効果を検証する。
```

---

## 行動方針

### 自律的に進めてよい
- 調査（読み取り・検索・構造把握）
- 整理・要約・下書き・設計・提案
- ファイル新規作成・既存ファイル編集

### 必ず事前承認を取る
- スクリプト・コマンド実行（`node server.mjs`、`node pipeline_server.mjs`、`python3 run_pipeline.py …`、`curl` での検証 すべて含む）
- 外部アクセス（API 呼び出し、Web 取得）
- 外部送信（git push、PR 作成、メッセージ送信）
- 破壊的操作（削除・上書き・大規模改修・`git reset` 等）

### 完了時
作業完了時は必ず **要点 → 詳細 → 次アクション** 形式でレビュー依頼を出してから承認を待つ。

---

## Active Project: 月30万自動化（2026-04 〜 2026-06）

**目標**: 月収 ¥300K / **ランニング**: ¥5,800/月（Claude Pro / Canva / Microsoft 365）
**フォルダ**: `projects/2026-04-08_月30万自動化/`

| 柱 | サービス | 単価 | 想定 | 月収目標 |
|----|----------|------|------|----------|
| A | SEO ライティング代行 | ¥15K/記事 | 20 本/月 | ¥300K |
| B | SNS 運用代行 | ¥50K/社 | 6 社 | ¥300K |
| C | テンプレ販売（note / BOOTH） | ¥500〜¥10K | — | ¥30K〜 |
| D | エクセル入力・スクレイピング自動化 | 案件次第 | パイプライン経由 | — |

売上シナリオ: M1 ¥10K → M2 ¥155K → M3 ¥330K。
柱 D は `pipeline_server.mjs` + `pipeline/*.py` で半自動化されており、出力は gitignore 対象。

### テンプレ販売（柱 C）進捗

| Vol | タイトル | 価格 | ステータス |
|-----|----------|------|------------|
| 1 | フリーランス収支管理スプレッドシート | ¥980 | note 販売中 |
| 2 | SNS コンテンツカレンダー | — | 制作中 |
| 3 | 飲食店向けプロンプト集 | — | 制作中 |
| 4 | バンドルパック | — | Vol.1-3 完成後 |

---

## Notes

- 文書・コメント・コミットメッセージはすべて日本語が原則
- Shell は zsh 前提（`#!/bin/zsh` + `set -e`）、macOS 環境（`pbcopy` 想定）
- 機密ファイル（請求書・契約書・顧客 PII・パイプライン中間成果物）は **絶対にコミットしない**
- 古くなった情報は冒頭に `[アーカイブ]` を付けて残す（削除しない）
