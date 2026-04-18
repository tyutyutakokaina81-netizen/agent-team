# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

AI-operated multi-officer company framework that supports the owner's content business.
Five C?O roles (CDO/CFO/CMO/CPO/CSO) each maintain their own work log, research, and outputs.
All documents and operational output are in Japanese.

**現在の事業方針（2026-04-18 更新）：**
従来の「月30万自動化（4本柱：SEOライティング代行 / SNS運用代行 / テンプレ販売 / スクレイピング案件取得）」は
**実績が出なかったため一旦停止**。これからは **note への執筆・投稿に集中** する方針に切り替わった。
旧プロジェクトの資産は `projects/2026-04-08_月30万自動化/` にアーカイブとして残す（削除しない）。

---

## Repository Structure

```
/home/user/agent-team/
├── CLAUDE.md              ← This file (Claude Code guidance)
├── README.md              ← agent-gateway (server.mjs) documentation
├── company.md             ← Core company rules, role definitions, governance (MUST READ)
├── server.mjs             ← Zero-dependency Node.js JSON API server (agent-gateway)
├── pipeline_server.mjs    ← iPhone操作用パイプライン制御サーバー（旧月30万自動化の遺産・現在は停止中）
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
    └── YYYY-MM-DD_プロジェクト名/
        ├── brief.md       ← Goal, timeline, roles involved, subfolder rationale
        └── [サブフォルダ]/ ← 役職別（CMO/ CPO/）またはテーマ別（A_〇〇/ B_〇〇/）
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

## pipeline_server.mjs（旧プロジェクト遺産・現在は停止中）

旧「月30万自動化」プロジェクトの柱D（クラウドソーシング案件の検索・評価・納品自動化）の
iPhone操作用 HTTP コントロールパネル。事業方針の転換により**新規実行は停止**。
ファイル自体は履歴・参考のため残す。

- ポート：`PIPELINE_PORT`（デフォルト 3001）
- 認証：`PIPELINE_TOKEN`（Bearer または `?token=` クエリ）
- 依存パス：`projects/2026-04-08_月30万自動化/D_エクセル入力スクレイピング/{pipeline,outputs}/`
- 主要エンドポイント：`GET /`（HTMLパネル）, `GET /status`, `POST /search`, `POST /deliver`, `GET /results`
- 実行は `python3 run_pipeline.py {search|deliver}` をサブプロセス起動

**新方針下での扱い：** 起動・実行・関連スクリプトの修正は原則行わない。
オーナーから明示の指示があった場合のみ作業すること。

---

## Active Direction: noteへの執筆・投稿（2026-04-18 〜）

**現在の方針：** noteへの執筆・投稿に集中する。  
**背景：** 旧「月30万自動化」（4本柱）は実績が出なかったため一旦停止。
小さく始めて発信を継続することを優先する。

### 主担当の暫定アサイン

| 役職 | この方針における役割 |
|------|--------------------|
| CMO | note記事の企画・タイトル設計・SEO/見出し構成・投稿計画 |
| CPO | 記事本文の構成テンプレ・連載/マガジン設計・読者導線 |
| CSO | 読者反応・コメント・有料記事の問い合わせ対応 |
| CFO | note売上の記録・経費管理（請求書系は引き続き機密扱い） |
| CDO | 執筆ワークフローのプロンプト整備・投稿補助ツール |

### 運用ルール
- note 関連の作業は原則 `projects/` 配下に新規プロジェクトを切って管理する  
  （例：`projects/YYYY-MM-DD_note執筆/`）
- 各役職の `research/`（下書き・構成案）→ `outputs/`（投稿確定版）の流れは従来どおり
- 投稿前に必ずオーナー承認を得る（noteへの実投稿は外部送信に該当）
- 旧プロジェクト（`projects/2026-04-08_月30万自動化/`）は**アーカイブ扱い**で参照可、新規作業は行わない

### 旧プロジェクト（参考保存）

`projects/2026-04-08_月30万自動化/` の内容（Aライティング代行 / B SNS運用代行 / C テンプレ販売 /
D エクセル入力スクレイピング、`brief.md` / `cashflow.md` / `cost_breakdown.md`）は削除せずに残す。
note方針で再利用できるノウハウ（テンプレ販売の知見、SEOライティング知見など）があれば参照してよい。

---

## Notes

- All shell scripts use `#!/bin/zsh` with `set -e`
- Shell scripts reference `$HOME/agent-team/` as the repo path (macOS `pbcopy` assumed)
- All prompts and document output are in Japanese
- Sensitive files (invoices, contracts, customer PII) must not be committed to Git
