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

## 完成の定義（DoD: Definition of Done）

過去に「設計書 = 完成」と誤認する事故が発生したため、以下を厳守する。

### 設計 ≠ 完成

**「設計書」「仕様書」「サービス設計」を作成しただけでは完了ではない。**

各成果物タイプごとに「完成」の条件を以下に定義する：

| 成果物タイプ | 「完成」の条件 |
|------------|---------------|
| テンプレ販売（C 柱） | (1) 仕様書 md / (2) 実体ファイル（CSV/Excel/md/Notion/PDF）/ (3) note 販売ページ原稿 — の **3点全て** が存在 |
| プロンプト集 | プロンプト本数の **100%** が記述されている（「（〜は同様）」「（〜個）」等の省略禁止） |
| サービス設計（A/B 柱） | (1) 設計書 / (2) 価格表 / (3) 営業文面 / (4) 受注後ワークフロー — の **4点全て** が存在 |
| パイプライン・ツール（D 柱・CDO） | (1) 動作するコード / (2) 実行手順書 / (3) エラー時のフォールバック — の **3点全て** が存在 |
| サーバー（server.mjs 等） | (1) 動作するコード / (2) curl 等での動作確認手順 / (3) 想定外入力への応答 — の **3点全て** が存在 |

### 「販売可能」と言ってよい条件

「販売可能」「リリース可能」「即売れる」と表現してよいのは **以下の全てを満たすときのみ**：

1. 購入者が **そのまま** 使える形式でファイルが存在する（CSV→Sheets インポート1クリック等の最小手数を除く）
2. 価格・販売チャネル・公開URLが確定している
3. オーナーの追加作業が「アップロード操作」のみで済む

それ以外は **「販売準備完了」「仕様完了」「設計完了」など状態を正確に表す語** を使う。

---

## 完了報告フォーマット（必須）

完了報告は以下のフォーマットを **必ず** 使用する。誇張・楽観報告を防ぐため、項目を省略しない。

```markdown
## 完了報告

### ✅ 実装した実体ファイル（git管理されているもの）
- パス1（行数・概要）
- パス2（行数・概要）

### ⚠️ 仕様のみ・実体なし
- 該当なし / または 具体的に列挙

### ❌ オーナーの追加作業が必要
- 作業1（推定所要時間）
- 作業2（推定所要時間）

### 「ほんとか？」セルフチェック（後述プロトコル参照）
- Q1: 主張した完了項目は本当に DoD を満たすか？ → 検証コマンド・結果
- Q2: 「販売可能」「完成」「動く」と書いた箇所は本当か？ → 検証コマンド・結果
- Q3: 仕様書だけで実体ファイルが無い項目を見落としていないか？ → 検証コマンド・結果

### 誇張なし宣言
- 「販売可能」と書いた箇所：（具体的に / なし）
- 「完成」と書いた箇所：（具体的に / なし）
- 上記は全て上の DoD を満たすことを確認した：はい / いいえ
```

---

## 「ほんとか？」プロトコル（必須）

過去セッションで「自己申告で完了と言ったが実態は半分しか実装されていない」という事故が
複数回発生した。これを防ぐため、**完了報告の前に必ず以下のセルフチェックを実行する**。

### 基本ルール

完了報告を書く前に、自分で **3回「ほんとか？」と問いかける**。  
各問いには **コマンド実行結果（git status / ls / wc -l / grep 等の客観証拠）** で答える。  
証拠なしの「はい」「完了済」「動くはず」は **禁止**。

### 必須3問

```
Q1：「ほんとか？仕様書だけで実体ファイルがないものはないか？」
  検証：find と grep で実体ファイル（.csv/.py/.md 中の実コード）を確認
  例：ls projects/.../*.csv | wc -l → 期待数と一致するか

Q2：「ほんとか？『（〜は同様）』『（〜個）』『TODO』が本文に残っていないか？」
  検証：grep -rn -E "（.*同様.*続く）|（.*個）$|TODO|FIXME|未実装" --include="*.md"
  期待：0件

Q3：「ほんとか？brief.md の DoD 表で ❌ の行を『完成』と報告していないか？」
  検証：brief.md の完成度チェック表を実際に確認
  期待：報告内容と表が一致
```

### 任意の追加問（タスク種別による）

- コード変更時：「ほんとか？シンタックスエラーなく動くか？」→ `python -c "import ..."` 等
- git push時：「ほんとか？origin と local が一致しているか？」→ `git log -1 origin/branch` で比較
- API/サーバー変更時：「ほんとか？想定外入力（不正JSON・空文字）に応答するか？」→ curl で実証
- テンプレ作成時：「ほんとか？プロンプト本数や項目数が宣言通りか？」→ `grep -c "^### "` で実数確認

### 自己問答が NG だったとき

セルフチェックで違反が見つかった場合は、**完了報告を書く前に修正する**。  
「ほぼ完了」「あと少し」での報告は禁止。実装まで戻る。

### 二重申告禁止

「販売可能」と書きながら同じ報告内に「ただしオーナー作業が必要」と書くのは
矛盾なので禁止。「販売準備完了」「仕様完了」など状態を正確に表す語を使う。

---

## 自動施行フック（.claude/hooks/）

`.claude/settings.json` に以下のフックが登録されており、上記ルールを **機械的に施行** する：

### SessionStart hook（`session_start_dod.sh`）
- セッション開始時に `brief.md` の DoD 表を強制表示
- 各セッション開始時、AI は未達項目の現状を必ず認識する

### Stop hook（`stop_hontoka.sh`）
- 直前のアシスタント出力に「完了」「販売可能」「完成」等の主張が含まれ、
  かつ直近で検証コマンド（ls/find/wc/grep/git log 等）を実行していない場合、
  `decision: "block"` でブロックして「ほんとか？」プロトコル実行を強制する
- 検証実行済 or 完了主張なしの場合は素通り（誤爆回避）

### PreToolUse(Bash) hook（`pre_commit_check.sh`）
- `git commit` のメッセージに「販売可能」「リリース可能」等の禁止語が含まれ、
  かつ `brief.md` の DoD 表に ❌（未達）が残っている場合、
  `permissionDecision: "deny"` でコミットを拒否する
- 禁止語あり ＋ DoD 全達成 → `permissionDecision: "ask"` で人間確認

### verify.sh（任意呼び出し）
- DoD 全項目を機械的に検査するスタンドアロンスクリプト
- 完了報告の前に `bash .claude/hooks/verify.sh` を呼び、exit 0 を確認すること
- 検査内容：
  1. プレースホルダ残留（「（〜は同様）」「TODO」等）
  2. brief.md の ❌ 一覧
  3. 仕様書（Vol.X.md）と実体（vol{X}*.csv）の対応
  4. origin と local の同期
  5. 未コミットの変更

---

## 積み残しチェックリスト

各プロジェクトの `brief.md` には **必ず** 以下のチェックリストを保持する：

```markdown
### 完成度チェック（DoD準拠）

| 成果物 | 仕様書 | 実体ファイル | 販売ページ | 状態 |
|-------|-------|------------|-----------|------|
| Vol.X | ✅ | ✅ | ❌ | 販売準備完了 |
| Vol.Y | ✅ | ❌ | ❌ | 仕様のみ |
```

- 仕様書・実体・販売ページの3列全てが ✅ になって初めて「完成」
- セッション開始時にこの表を確認し、未 ✅ の項目から着手する
- 新規成果物を追加するときも必ずこの表に行を追加する

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
**フォルダ**: `projects/2026-04-08_月30万自動化/`

### 3つの収益柱

| 柱 | サービス | 単価 | 目標 | 月収目標 |
|----|---------|------|------|---------|
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
