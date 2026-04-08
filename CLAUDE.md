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
├── server.mjs             ← Zero-dependency Node.js JSON API server
├── team_prompt.txt        ← 4-role multi-agent document creation prompt
├── team_copy.sh           ← Copy team_prompt.txt to clipboard (zsh/macOS)
├── team_show.sh           ← Print team_prompt.txt to stdout
│
├── CDO/                   ← Chief Digital Officer (systems, automation, tech, role management)
│   ├── _index.md          ← Performance log & active tasks
│   ├── prompt.md          ← Role definition, personality, workflow, boundaries
│   ├── research/          ← Prototypes, investigations
│   └── outputs/           ← Prompts, tools, guides
│
├── CFO/                   ← Chief Financial Officer (finance, contracts, admin)
│   ├── _index.md
│   ├── prompt.md
│   ├── research/
│   └── outputs/           ← Invoices, contracts, expense reports
│
├── CMO/                   ← Chief Marketing Officer (content, SNS, LP, YouTube)
│   ├── _index.md
│   ├── prompt.md
│   ├── research/
│   └── outputs/           ← Scripts, SNS posts, landing pages
│
├── CPO/                   ← Chief Product Officer (courses, seminars, educational products)
│   ├── _index.md
│   ├── prompt.md
│   ├── research/
│   └── outputs/           ← Slides, templates, step-by-step guides
│
├── CSO/                   ← Chief Sales Officer (customer dialogue, proposals, pipeline)
│   ├── _index.md
│   ├── prompt.md
│   ├── research/
│   └── outputs/           ← Proposals, dialog logs, FAQs
│
├── context/               ← Owner's primary source of truth (read before any task)
│   ├── diary/             ← Daily reflections and observations
│   ├── ideas/             ← Concepts and strategic thinking
│   └── references/        ← External materials and research
│
└── projects/              ← Cross-functional work (multi-role collaboration)
    ├── _index.md          ← Master project registry
    └── 2026-04-08_月30万自動化/   ← Active: ¥300K/month automation project
        ├── brief.md
        ├── cashflow.md
        ├── cost_breakdown.md
        ├── A_ライティング/        ← SEO writing service (Pillar A)
        ├── B_SNS運用代行/         ← SNS management service (Pillar B)
        └── C_テンプレ販売/        ← Template sales service (Pillar C)
```

---

## 会社運営ルール（必読）

**このリポジトリは会社経営のためのAIチームです。**  
作業開始前に必ず以下を確認してください：

1. `company.md` — 会社共通ルール・ディレクトリ構造・役職定義・新役職生成ルール
2. `context/` — オーナーの日記・アイデア・参考資料（意図や背景の把握に使う）
3. 担当役職の `_index.md` — 過去の成果物・進行中タスクの確認

### ファイル作成・更新時の必須ルール
- 成果物を作成・更新したら **必ず** 該当役職の `_index.md` の成果物ログに追記する
- ファイル名は `YYYY-MM-DD_名前.md` 形式にする
- 役職をまたぐ作業は `projects/` 配下にフォルダを作り `projects/_index.md` に登録する
- センシティブな情報（請求書・契約書・顧客PII）はGitにコミットしない（`.gitignore`管理）

### _index.md の標準形式
```markdown
# [役職] インデックス（[タイトル]）

## 担当業務
- 責任範囲の箇条書き

## 成果物ログ
| 日付 | ファイル名 | 種別 | 概要 | ステータス |

## 進行中タスク
- タスクリスト

## メモ・引き継ぎ事項
- 備考
```

### 役職の判断基準（各役職 prompt.md 参照）

| 役職 | 主な責任 | 得意なアウトプット |
|------|---------|------------------|
| CDO  | 自動化・プロンプト設計・役職管理 | ツール、プロンプト、フォルダ設計 |
| CFO  | 数字の正確性・契約・経費 | 請求書、契約書、財務サマリ |
| CMO  | マーケティング・コンテンツ | YouTubeスクリプト、SNS投稿、LP |
| CPO  | 教育コンテンツ・製品設計 | スライド、テンプレート、手順書 |
| CSO  | 顧客対話・提案・パイプライン | 提案書、対話ログ、FAQ |

### 役職間の情報フロー
```
CSO → CMO（顧客インサイト → マーケティング）
CMO → CPO（市場ニーズ → プロダクト）
CPO → CFO（製品仕様 → 価格・請求）
全役職 ← CDO（ツール・自動化・役職生成）
```

### 新役職が必要と判断した場合
`company.md` の「新役職の自動生成ルール」の条件をすべて満たす場合、**承認不要で自律実行してよい**。  
実行後、作成した内容をオーナーに報告すること（事前確認は不要）。  
条件を満たすか迷う場合は既存役職で対応する（役職は増やさない方向で判断する）。

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

### 出力形式
1. **要点** — 結論・変更サマリを最初に示す
2. **詳細** — 根拠・実装内容・補足説明
3. **次アクション** — ユーザーが取るべき手順や選択肢

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

## Active Project: 月30万自動化（¥300K/Month Automation）

**目標**: 3ヶ月以内に月収¥300K達成（2026-04 〜 2026-06）  
**ランニングコスト**: ¥5,800/月（Claude Pro ¥3K + Canva ¥1.5K + Microsoft 365 ¥1.3K）  
**関与役職**: CMO, CPO, CSO, CDO

### 3つの収益柱

| 柱 | サービス | 単価 | 目標 | 月収 |
|----|---------|------|------|------|
| A  | SEOライティング代行 | ¥15K/記事 | 20本/月 | ¥300K |
| B  | SNS運用代行 | ¥50K/社 | 6社 | ¥300K |
| C  | テンプレート販売 | ¥500〜¥10K | note/BOOTH販売 | ¥30K〜 |

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
- Git development branch: `claude/add-claude-documentation-6K1Pe`
