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
├── server.mjs             ← Zero-dependency Node.js JSON API server (agent-gateway)
├── pipeline_server.mjs    ← iPhone-operable HTTP+HTML panel for the 柱D pipeline
├── team_prompt.txt        ← 4-role multi-agent document creation prompt
├── team_copy.sh           ← Copy team_prompt.txt to clipboard (zsh/macOS)
├── team_show.sh           ← Print team_prompt.txt to stdout
├── .gitignore             ← Excludes CFO/CSO outputs, 柱D outputs/.sessions, context/* (see below)
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
│   ├── research/          ← Contract/tax research drafts (gitignored)
│   └── outputs/           ← Final: invoices, contracts, expense reports (gitignored)
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
│   ├── research/          ← Customer analysis, market research drafts (gitignored)
│   └── outputs/           ← Final: proposals, dialog logs, FAQs (gitignored)
│
├── context/               ← Owner's primary source of truth (read before any task)
│   ├── diary/             ← Daily reflections and observations (gitignored)
│   ├── ideas/             ← Concepts and strategic thinking (gitignored)
│   └── references/        ← External materials and research (gitignored)
│
└── projects/              ← Cross-functional work (multi-role collaboration)
    ├── _index.md          ← Master project registry
    └── 2026-04-08_月30万自動化/
        ├── brief.md       ← Goal, timeline, roles involved, subfolder rationale
        ├── cashflow.md    ← Cash flow scenarios (realistic / pessimistic / optimistic)
        ├── cost_breakdown.md ← Monthly cost breakdown per tool
        ├── A_ライティング/        ← 柱A: SEO writing service
        ├── B_SNS運用代行/         ← 柱B: SNS management service
        ├── C_テンプレ販売/        ← 柱C: Template digital products (Vol.1〜4)
        └── D_エクセル入力スクレイピング/  ← 柱D: Data-entry/scraping auto-pipeline
            ├── brief.md
            ├── risk_and_feasibility.md   ← TOS/feasibility research (must read before edits)
            ├── pipeline/                  ← Python auto-pipeline (00〜06 + run_pipeline.py)
            ├── templates/                 ← Profile bio, application templates
            ├── outputs/                   ← Generated artifacts (gitignored)
            └── .sessions/                 ← Playwright session cookies (gitignored)
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

## pipeline_server.mjs（柱D 操作パネル）

### 概要
- 柱D「エクセル入力・Webスクレイピング自動受注パイプライン」を iPhone から操作するための
  HTTP+HTML サーバー（標準モジュールのみ・依存ゼロ）
- ホスト: `0.0.0.0`（同一LAN内の iPhone からアクセス可能）
- 認証: `PIPELINE_TOKEN` 環境変数（Bearer ヘッダー or `?token=` クエリ）。未設定なら警告を出して認証スキップ

### エンドポイント
| メソッド | パス       | 説明 |
|----------|-----------|------|
| GET  | `/`        | iOS風 HTML 操作パネル（検索開始 / 納品開始 / 結果表示） |
| GET  | `/status`  | 現在の状態（idle / running / done / error）と直近ログ |
| POST | `/search`  | `run_pipeline.py search` をバックグラウンド起動 |
| POST | `/deliver` | `run_pipeline.py deliver` をバックグラウンド起動 |
| GET  | `/results` | `D_エクセル入力スクレイピング/outputs/` 直近 JSON を返す |

### 起動
```bash
export PIPELINE_TOKEN=your-secret-token        # 本番では必須
PIPELINE_PORT=3001 node pipeline_server.mjs    # デフォルト 3001
```

### 内部動作
- `child_process.spawn('python3', ['run_pipeline.py', ...])` をワーキングディレクトリ
  `projects/2026-04-08_月30万自動化/D_エクセル入力スクレイピング/pipeline` で実行する
- stdout/stderr の各行を `state.log`（最大200行）に追記し、HTML パネルが 5 秒ごとに `/status` をポーリング表示
- 同時実行はブロック（既に running なら 409）

### 運用ルール
- `pipeline_server.mjs` の実行・パイプラインスクリプトの実行は「必ず事前承認」を取る
- `PIPELINE_TOKEN` 未設定時の本番起動は禁止
- 改修は柱D の `risk_and_feasibility.md`（規約調査結果）を踏まえて行う

---

## 柱D パイプライン（Python）

`projects/2026-04-08_月30万自動化/D_エクセル入力スクレイピング/pipeline/`

| スクリプト | 役割 |
|-----------|------|
| `00_session_setup.py` | Playwright でクラウドワークス・ランサーズに初回ログインし、セッションを `.sessions/` に保存 |
| `01_search.py` | 保存セッションで案件を一覧検索・詳細取得 |
| `02_evaluate.py` | 案件文をスコアリングし、`GO / CAUTION / NO-GO` を判定 |
| `03_apply.py` | 応募文を生成し、上位案件のURLをブラウザで自動オープン（**送信は必ず人手**） |
| `04_execute.py` | Excel入力 / スクレイピング作業を実行 |
| `05_review.py` | 念査（品質チェック）。重大issueがあれば中断 |
| `06_deliver.py` | 納品文を生成し、案件URLをブラウザで開く（添付・送信は人手） |
| `run_pipeline.py` | 上記を `search` / `deliver` の2フェーズで統合実行 |

### 人手が必要な操作
1. 初回セッション設定（00_session_setup.py）
2. 応募ボタンのクリック（03_apply.py が URL を自動オープン）
3. 納品ファイル添付と送信ボタンのクリック（06_deliver.py が URL を自動オープン）

### 規約準拠の前提（必読）
- 自動応募・プラットフォーム本体へのスクレイピングは禁止 → 応募・納品の **送信は必ず人手**
- AI使用はクライアントへ開示（プロフィールに「AI補助+人間確認」を明記）
- 詳細は `D_エクセル入力スクレイピング/risk_and_feasibility.md` を参照

---

## Active Project: 月30万自動化（¥300K/Month Automation）

**目標**: 3ヶ月以内に月収¥300K達成（2026-04 〜 2026-06）  
**ランニングコスト**: ¥5,800/月（Claude Pro ¥3K + Canva ¥1.5K + Microsoft 365 ¥1.3K、最小構成では¥0〜¥3K）  
**関与役職**: CMO, CPO, CSO, CDO  
**フォルダ**: `projects/2026-04-08_月30万自動化/`  
**サブフォルダ構成**: テーマ別（A_/B_/C_/D_）

### 4つの収益柱

| 柱 | サービス | 単価 | 目標 | 月収目標 | 担当役職 |
|----|---------|------|------|---------|---------|
| A  | SEOライティング代行 | ¥15K/記事 | 20本/月 | ¥300K | CSO・CMO・CDO |
| B  | SNS運用代行 | ¥50K/社 | 6社 | ¥300K | CMO・CSO・CDO |
| C  | テンプレート販売（note/BOOTH） | ¥500〜¥10K | 自動販売 | ¥30K〜 | CPO・CMO・CDO |
| D  | データ入力・スクレイピング代行 | ¥2K〜¥30K/件 | 10〜20件 | ¥50K〜¥250K | CDO・CSO |

### 売上予測（リアルシナリオ・cashflow.md）
- Month 1: ¥10K（テンプレ初動のみ）
- Month 2: ¥155K（A・B契約開始）— **現時点（2026-05）**
- Month 3: ¥330K（目標達成）
- Month 4以降: ¥525K〜

### テンプレート販売（柱C） — 進捗

| Vol | タイトル | 価格 | ステータス |
|-----|---------|------|----------|
| Vol.1 | フリーランス収支管理スプレッドシート | ¥980 | 販売中（note） |
| Vol.2 | SNSコンテンツカレンダー | 設計済 | 制作中 |
| Vol.3 | 飲食店向けプロンプト集 | 設計済 | 制作中 |
| Vol.4 | バンドルパック | 設計済 | Vol.1-3完成後 |

### 立ち上げ順序の考え方
柱Dは即受注可能で立ち上げ最速 → Month 1〜2 の収益補完。
柱A・Bは契約獲得に時間がかかる → Month 2 以降に貢献。
柱Cは自動販売（一度作れば永久に売れる）→ ロングテール収益。

---

## Notes

- All shell scripts use `#!/bin/zsh` with `set -e`
- Shell scripts reference `$HOME/agent-team/` as the repo path (macOS `pbcopy` assumed)
- All prompts and document output are in Japanese
- Sensitive files (invoices, contracts, customer PII) must not be committed to Git
- Node servers (`server.mjs`, `pipeline_server.mjs`) are dependency-free (Node 標準モジュールのみ)
- 柱D pipeline requires Python3 + `playwright` (`pip install playwright && playwright install chromium`)
- `.gitignore` excludes:
  - `CFO/outputs/*`, `CFO/research/*`, `CSO/outputs/*`, `CSO/research/*`（機密ファイル）
  - `projects/*/D_エクセル入力スクレイピング/outputs/*`（納品前成果物）
  - `projects/*/D_エクセル入力スクレイピング/.sessions/*`（Playwrightセッション）
  - `context/diary/*`, `context/ideas/*`, `context/references/*`（オーナー個人情報）
  - `*_secret*`, `*_confidential*`, `*_機密*`, `*_秘密*`（汎用パターン）
  - `.gitkeep` ファイルは除外対象外（フォルダ構造維持のため）
