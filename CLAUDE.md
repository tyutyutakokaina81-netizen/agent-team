# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

AI-operated multi-officer company framework for building a ¥300K/month automated business.  
Five C?O roles (CDO/CFO/CMO/CPO/CSO) each maintain their own work log, research, and outputs.  
All documents and operational output are in Japanese.

---

## Repository Structure

```
/home/user/agent-team/
├── CLAUDE.md              ← This file (Claude Code guidance)
├── README.md              ← agent-gateway server documentation
├── company.md             ← Core company rules, role definitions, governance (MUST READ)
├── server.mjs             ← Zero-dependency Node.js JSON API server (port 3000)
├── pipeline_server.mjs    ← iPhone control panel for pillar-D pipeline (port 3001)
├── team_prompt.txt        ← 4-role multi-agent document creation prompt
├── team_copy.sh           ← Copy team_prompt.txt to clipboard (zsh/macOS)
├── team_show.sh           ← Print team_prompt.txt to stdout
│
├── CDO/                   ← Chief Digital Officer (systems, automation, tech, role management)
│   ├── _index.md          ← Performance log & active tasks (台帳)
│   ├── prompt.md          ← Role definition, personality, workflow, boundaries
│   ├── research/          ← Drafts, prototypes, investigations
│   └── outputs/           ← Final deliverables: prompts, tools, guides
│
├── CFO/                   ← Chief Financial Officer (finance, contracts, admin)
│   ├── _index.md
│   ├── prompt.md
│   ├── research/          ← Contract/tax research drafts
│   └── outputs/           ← Final: invoices, contracts, expense reports
│
├── CMO/                   ← Chief Marketing Officer (content, SNS, LP, YouTube)
│   ├── _index.md
│   ├── prompt.md
│   ├── research/          ← Content strategy drafts
│   └── outputs/           ← Final: scripts, SNS posts, landing pages
│
├── CPO/                   ← Chief Product Officer (courses, seminars, templates)
│   ├── _index.md
│   ├── prompt.md
│   ├── research/          ← Curriculum/product research drafts
│   └── outputs/           ← Final: slides, templates, step-by-step guides
│
├── CSO/                   ← Chief Sales Officer (customer dialogue, proposals, pipeline)
│   ├── _index.md
│   ├── prompt.md
│   ├── research/          ← Customer analysis, market research drafts
│   └── outputs/           ← Final: proposals, dialog logs, FAQs
│
├── context/               ← Owner's primary source of truth (read before any task)
│   ├── diary/             ← Daily reflections and observations
│   ├── ideas/             ← Concepts and strategic thinking
│   └── references/        ← External materials and research
│
└── projects/              ← Cross-functional work (multi-role collaboration)
    ├── _index.md          ← Master project registry
    └── 2026-04-08_月30万自動化/
        ├── brief.md       ← Goal, timeline, roles involved, subfolder rationale
        ├── cashflow.md    ← Revenue/cost projections
        ├── cost_breakdown.md
        ├── A_ライティング/           ← 柱A: SEO writing service
        ├── B_SNS運用代行/            ← 柱B: SNS operation outsourcing
        ├── C_テンプレ販売/           ← 柱C: Template sales (note/BOOTH)
        └── D_エクセル入力スクレイピング/ ← 柱D: Data-entry scraping pipeline
            ├── brief.md
            ├── risk_and_feasibility.md
            ├── pipeline/             ← Python automation (00-06 scripts + run_pipeline.py)
            ├── templates/            ← profile_bio.md etc
            ├── outputs/              ← Generated results (.gitignore'd)
            └── .sessions/            ← Login sessions (.gitignore'd)
```

---

## 会社運営ルール（必読）

**このリポジトリは会社経営のためのAIチームです。**  
作業開始前に必ず以下を確認してください：

1. `company.md` — 会社共通ルール・ディレクトリ構造・役職定義・新役職生成ルール
2. `context/` — オーナーの日記・アイデア・参考資料（意図や背景の把握に使う）
3. 担当役職の `_index.md` — 過去の成果物・進行中タスクの確認

---

## ファイル管理ルール

### 命名規則
- 日付プレフィックス必須：`YYYY-MM-DD_ファイル名.md`
- 下書き・調査中は `research/` に保存する
- 確定・完成版は `outputs/` に保存する
- センシティブなファイル（請求書・契約書・顧客PII）は Git にコミットしない（`.gitignore` 管理）

### _index.md の運用ルール

ファイルを作成・更新するたびに **必ず** 該当役職の `_index.md` 成果物ログに追記する。

```markdown
| 日付 | ファイル名 | 種別 | 概要 | ステータス |
```

- 進行中タスクは完了後に削除しない → ステータスを「完了」に変更する
- 他役職の成果物を参照した場合、自分の `_index.md` のメモ欄に参照元を記載する
- CFO は `_index.md` に金額を記載しない（ファイル名のみ記録する）

### projects/ の使い方

複数役職が関与するタスクは必ず `projects/` に切り出す。

```
projects/YYYY-MM-DD_プロジェクト名/
├── brief.md       ← 目的・ゴール・関与役職・サブフォルダ構成の理由
└── [サブフォルダ]/ ← 役職別 or テーマ別（どちらでも可）
```

**サブフォルダの選び方：**
- 役職別（CMO/ CPO/ 等）：担当が役職で明確に分かれる場合
- テーマ別（A_〇〇/ B_〇〇/ 等）：事業柱・機能単位で整理した方が自然な場合

1. 開始時に `projects/_index.md` のテーブルに追記する
2. 完了後も削除せずアーカイブとして残す

```markdown
# projects/_index.md テーブル形式
| 開始日 | プロジェクト名 | 関与役職 | 状態 | フォルダ |
```

### context/ の使い方

| サブフォルダ | 格納するもの |
|------------|------------|
| `context/diary/` | 日記・日常の気づき・感情メモ |
| `context/ideas/` | アイデア・考え事・将来構想 |
| `context/references/` | 参考資料・書籍メモ・外部情報 |

- タスク実行前に必ず参照し、オーナーの意図・背景を把握してから作業を開始する
- 古くなった情報にはファイル冒頭に `[アーカイブ]` を付ける

---

## 役職ルール

### 役職一覧と担当領域

| 役職 | 役割 | 主な成果物 |
|------|------|----------|
| CDO | 自動化・プロンプト設計・技術検証・役職管理 | プロンプト集、ツール、ガイド |
| CFO | 数字の正確性・契約・経費・事務 | 請求書、契約書、財務サマリ |
| CMO | マーケティング・コンテンツ企画・集客 | YouTube台本、SNS投稿、LP |
| CPO | 教育コンテンツ・プロダクト設計 | スライド、テンプレート、手順書 |
| CSO | 顧客対話・営業・パイプライン管理 | 提案書、対話ログ、FAQ |

### 役職間の情報フロー

```
オーナー（context/）
    ├─→ CSO：顧客ニーズ・商談情報を収集
    │       ├─→ CMO：マーケ施策・コンテンツに反映
    │       └─→ CPO：プロダクト改善に反映
    ├─→ CMO：コンテンツ企画・集客
    │       └─→ CPO：教材・セミナーと連携
    ├─→ CPO：プロダクト設計・教材
    │       └─→ CFO：価格・契約条件と整合
    ├─→ CFO：財務・事務管理
    │       └─→ CSO：見積・契約書を提供
    └─→ CDO：全役職のツール・プロンプト整備
            └─→ 全役職：効率化・自動化を支援
```

### 新役職の自動生成ルール（CDO 権限）

以下の条件をすべて満たす場合、**CDO は承認不要で即実行してよい**：

1. 既存の役職のどれにも明確に当てはまらないタスクが発生した
2. 同種のタスクが今後も繰り返し発生すると予測できる
3. 役割名と担当業務を明確に定義できる
4. 迷う場合は既存役職で対応する（役職は増やさない方向で判断する）

**生成手順：**
1. 条件を満たすと判断したら即実行（承認不要）
2. 以下の構造でフォルダを作成する：
   ```
   新役職名/
   ├── _index.md     ← 担当業務・成果物ログを記載
   ├── research/
   └── outputs/
   ```
3. `company.md` のディレクトリ構造と成果物保存先テーブルを更新する
4. 実行後にオーナーへ報告する（「新役職を追加しました」）

**役職名の命名規則：**
- C?O 形式を基本とする（例：CHO=人事、CLO=法務、CXO=顧客体験）
- 略称が既存役職と重複する場合は別名を検討する

---

## 報告ルール

### 事実と意見を分ける

報告時は事実と推測・意見を必ず区別して記載する。

```
【事実】先月のYouTube登録者数は1,200人増加した。
【考察】コンテンツ投稿頻度を週2回に増やした影響と考えられる。
【提案】来月も同頻度を維持し、効果を検証することを推奨する。
```

### 出力形式
1. **要点** — 結論・変更サマリを最初に示す
2. **詳細** — 根拠・実装内容・補足説明
3. **次アクション** — ユーザーが取るべき手順や選択肢

---

## 行動方針

### 自律的に進めてよい操作
- 調査（ファイル読み取り、コード検索、構造把握）
- 整理（情報の分類・要約・構造化）
- 下書き（ドキュメント・コードの草案作成）
- 設計（アーキテクチャ検討、方式提案）
- 提案（改善案・代替案の提示）
- コード作成（新規ファイル作成、既存ファイル編集）

### 必ず事前に確認する操作
- スクリプト・コマンドの実行（ビルド、テスト含む）
- 外部アクセス（API呼び出し、Web取得）
- 外部送信（git push、PR作成、メッセージ送信）
- 破壊的操作（ファイル削除、上書き、大規模改修、git reset等）

### 完了時のルール
- 作業完了時は必ず **レビュー依頼（承認）** を出す
- 変更内容の要約と確認ポイントを提示してからユーザー承認を得る

---

## Prompt Variants

### team_prompt.txt — 4-role document creation team
- Roles: 企画（Planning）→ 本文（Body）→ 要約（Summary）→ チェック（Review）
- Use case: General internal document creation
- Shared rules: preserve content, explain jargon, infer intent, output single final version

```bash
./team_copy.sh    # Copy to clipboard (macOS/pbcopy)
./team_show.sh    # Print to stdout
```

---

## agent-gateway（server.mjs）

### 概要
- `server.mjs` は依存ゼロ（Node標準 `node:http` のみ）の JSON API サーバー
- エンドポイント:
  - `GET /health` → `{ ok: true, time: ISO文字列 }`
  - `GET /version` → `{ name: "agent-gateway", version: "0.1.0" }`
  - `POST /echo` → 受け取ったJSONをそのまま返す（不正JSONは 400）
  - その他は 404 → `{ error: "Not Found" }`
- ログ: `METHOD /path STATUS 処理時間ms` を stdout に出力
- ステータスコード: 200 / 400（不正JSON）/ 404（未定義パス）/ 500（サーバーエラー）

### 起動
```bash
node server.mjs           # デフォルト PORT=3000
PORT=8080 node server.mjs # ポート変更
```

### 動作確認（curl）
```bash
curl -s http://127.0.0.1:${PORT:-3000}/health | python3 -m json.tool
curl -s http://127.0.0.1:${PORT:-3000}/version | python3 -m json.tool
curl -s -X POST http://127.0.0.1:${PORT:-3000}/echo \
  -H 'Content-Type: application/json' -d '{"hello":"world"}' | python3 -m json.tool
curl -s -X POST http://127.0.0.1:${PORT:-3000}/echo \
  -H 'Content-Type: application/json' -d 'not json' | python3 -m json.tool
curl -s http://127.0.0.1:${PORT:-3000}/unknown | python3 -m json.tool
```

### 運用ルール
- `server.mjs` の実行・curl での検証は「必ず事前承認」を取る
- 変更が完了したら「要点 → 詳細 → 次アクション」形式でレビュー依頼（承認）を出す

---

## pipeline_server.mjs（iPhone操作パネル）

### 概要
- 柱D（エクセル入力スクレイピング）のパイプラインを iPhone から操作するための Node.js サーバー
- `HOST='0.0.0.0'` でバインドし、同一LAN内の iPhone からアクセス可能
- 画面は `/` の HTML パネル（検索／納品／結果確認ボタン）
- バックエンドは Python スクリプト（`projects/.../D_.../pipeline/run_pipeline.py`）を `spawn` で実行

### エンドポイント
- `GET /` → iPhone 用 HTML 操作パネル
- `GET /status` → `{ status, phase, startedAt, finishedAt, log[] }`（認証不要）
- `POST /search` → 案件検索フェーズ開始（バックグラウンド実行）
- `POST /deliver` → 納品フェーズ開始（バックグラウンド実行）
- `GET /results` → 最新の評価結果 JSON（`outputs/*_evaluated.json` or `*_applications.json`）

### 認証・環境変数
- `PIPELINE_PORT`（デフォルト 3001）
- `PIPELINE_TOKEN`（**必須**）— 未設定時は `exit 1` で起動を中止する
- 認証は `Authorization: Bearer <TOKEN>` または `?token=<TOKEN>`

### 起動
```bash
export PIPELINE_TOKEN=your-secret-token  # 未設定だと起動しない
node pipeline_server.mjs                 # 3001 で起動
PIPELINE_PORT=4000 node pipeline_server.mjs # ポート変更
```

### 運用ルール
- サーバー起動・`POST /search` `POST /deliver` の実行は「必ず事前承認」を取る
- パイプライン配下（`D_エクセル入力スクレイピング/outputs/`、`.sessions/`）は `.gitignore` 済みなのでコミットしない
- 納品前成果物・ログイン情報を含むため、`PIPELINE_TOKEN` なしで公開ネットワークに晒さない

---

## Active Project: 月30万自動化（¥300K/Month Automation）

**目標**: 3ヶ月以内に月収¥300K達成（2026-04 〜 2026-06）  
**ランニングコスト**: ¥5,800/月（Claude Pro ¥3K + Canva ¥1.5K + Microsoft 365 ¥1.3K）  
**関与役職**: CMO, CPO, CSO, CDO  
**フォルダ**: `projects/2026-04-08_月30万自動化/`

### 収益柱（A/B/C/D の4本）

| 柱 | サービス | 単価 | 目標 | 担当役職 |
|----|---------|------|------|---------|
| A  | SEOライティング代行 | ¥15K/記事 | 20本/月 → ¥300K | CSO・CMO・CDO |
| B  | SNS運用代行 | ¥50K/社 | 6社 → ¥300K | CMO・CSO・CDO |
| C  | テンプレート販売 | ¥500〜¥10K | note/BOOTH | CPO・CMO・CDO |
| D  | エクセル入力スクレイピング | 案件単価 | パイプライン自動化 | CDO |

### 柱Dパイプライン（`D_エクセル入力スクレイピング/pipeline/`）

案件検索から納品までを Python + Playwright で自動化。**人手が必要なのは初回ログインと応募／納品ボタンの押下のみ**。

| 番号 | スクリプト | 役割 |
|------|-----------|------|
| 00 | `00_session_setup.py` | クラウドワークス／ランサーズの初回ログイン・セッション保存 |
| 01 | `01_search.py` | 案件一覧の検索・詳細取得 |
| 02 | `02_evaluate.py` | 4軸スコアリング（GO / CAUTION / NO-GO）— APIキー未設定時はルールベースにフォールバック |
| 03 | `03_apply.py` | 応募文生成（APIキー不要のテンプレ版あり）・上位URLをブラウザで自動オープン |
| 04 | `04_execute.py` | 受注後の作業実行 |
| 05 | `05_review.py` | 念査（品質チェック） |
| 06 | `06_deliver.py` | 納品文生成・納品ページを自動オープン |

```bash
# セッション状態確認
python run_pipeline.py setup

# 検索 → 評価 → 応募文生成（ブラウザで上位3件を自動オープン）
python run_pipeline.py search

# 受注後：作業実行 → 念査 → 納品準備
python run_pipeline.py deliver
```

iPhone から操作する場合は `pipeline_server.mjs` を経由する（上記セクション参照）。

### 売上予測（リアルシナリオ）
- Month 1: ¥10K（テンプレ初動のみ）
- Month 2: ¥155K（A・B契約開始）
- Month 3: ¥330K（目標達成）

### テンプレート販売 — 進捗

| Vol | タイトル | 価格 | ステータス |
|-----|---------|------|----------|
| Vol.1 | フリーランス収支管理スプレッドシート | ¥980 | 販売中（note） |
| Vol.2 | SNSコンテンツカレンダー | 設計済 | 制作中 |
| Vol.3 | 飲食店向けプロンプト集 | 設計済 | 制作中 |
| Vol.4 | バンドルパック | 設計済 | Vol.1-3完成後 |

---

## Notes

- All shell scripts use `#!/bin/zsh` with `set -e`
- Shell scripts reference `$HOME/agent-team/` as the repo path (macOS `pbcopy` assumed)
- All prompts and document output are in Japanese
- Sensitive files (invoices, contracts, customer PII) must not be committed to Git
- `.gitignore` で保護されているもの: `CFO/outputs/`, `CFO/research/`, `CSO/outputs/`, `CSO/research/`, `context/diary/`, `context/ideas/`, `context/references/`, `projects/*/D_エクセル入力スクレイピング/outputs/`, `projects/*/D_エクセル入力スクレイピング/.sessions/`
- フォルダ構造維持用の `.gitkeep` のみ上記保護対象でも例外的にコミットされる
