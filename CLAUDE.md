# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

AI-operated multi-officer company framework. Originally framed as a ¥300K/month automated business;
the **active North Star is now: get overseas readers to read articles about 高岡・氷見・富山 (Takaoka / Himi / Toyama)** — see `AGENTS.md` §0.

Six C?O roles (CDO / CFO / CMO / CPO / CSO / CAO) each maintain their own work log, research, and outputs.
All documents and operational output are in Japanese.

> **Read order at the start of EVERY session (mandatory):**
> 1. `context/STATE.md` — current state, absolute constraints (A1–A7), decision log. **Auto-loaded by the SessionStart hook.**
> 2. `company.md` — company-wide rules, directory structure, role definitions, governance.
> 3. The relevant role's `_index.md` — past deliverables and in-progress tasks (台帳/ledger).

---

## Repository Structure

```
/home/user/agent-team/
├── CLAUDE.md              ← This file (Claude Code guidance)
├── AGENTS.md              ← Onboarding for any repo-capable AI worker (file-based collab, no API cost)
├── company.md            ← Core company rules, role definitions, governance (MUST READ)
├── README.md             ← agent-gateway (server.mjs) documentation
│
├── .claude/
│   ├── settings.json      ← SessionStart hook + permissions (Bash, Skill allowed)
│   └── hooks/
│       └── session-start.sh   ← Loads context/STATE.md into session context at startup
│
├── .github/workflows/
│   ├── pages.yml          ← Deploy tavern.html to GitHub Pages (on push to main)
│   └── note-thumbnails.yml← Generate note thumbnails via Gemini/Pexels (cloud has net access)
│
├── server.mjs             ← Zero-dependency Node.js JSON API server (agent-gateway)
├── pipeline_server.mjs    ← iPhone-operable pipeline server (柱D 案件検索/納品, token-auth)
├── tavern.html            ← Single-page dashboard/UI (deployed to GitHub Pages)
├── inject_js/             ← Per-note browser inject scripts (n<id>.js) for cowork publishing
├── thumbnails/ thumbs/ thumbs_preview/  ← Generated/AI thumbnail assets
│
├── team_prompt.txt        ← 4-role multi-agent document creation prompt
├── team_copy.sh / team_show.sh   ← Copy / print team_prompt.txt (zsh/macOS)
│
├── CDO/  CFO/  CMO/  CPO/  CSO/  CAO/   ← Officer roles (each: _index.md, prompt.md, research/, outputs/)
│   └── CDO/outputs/                     ← note_publisher/, note_footer/, cross_post/, skills/
│       └── skills/chinakorea-magazine-monthly/SKILL.md   ← Monthly CN/KR magazine skill
│
├── EN/                    ← English / cross-post material (research/, outputs/reddit/, outputs/x_tweets/)
├── CMO/outputs/EN/        ← English versions of note articles
│
├── ops/                   ← File-based async task queue between code (Claude Code) and cowork
│   ├── README.md          ← Queue protocol + process_inbox.py CLI usage
│   ├── process_inbox.py   ← Zero-dep CLI: list / show / take / done / post
│   ├── inbox/             ← code → cowork instructions
│   ├── outbox/            ← cowork → code reports
│   ├── processed/         ← completed tasks (moved here, never deleted)
│   └── logs/              ← batch execution logs
│
├── docs/                  ← Governance & operations docs (read before contributing)
│   ├── agent-governance.md    ← Safety: least-privilege, no main-push, no secrets (MUST READ)
│   ├── role-division.md / org.md  ← code = primary/brain, cowork = sub/executor
│   ├── auto-ops.md / automation.md / full-automation-setup.md
│   ├── cowork-handoff.md / workers-connect.md / site-setup.md
│   └── article_footer_overseas.md
│
├── context/               ← Owner's primary source of truth (read before any task)
│   ├── STATE.md           ← Persistent memory (auto-loaded). NOT gitignored.
│   └── diary/ ideas/ references/   ← Owner private info (gitignored except .gitkeep)
│
└── projects/              ← Cross-functional work (multi-role collaboration)
    ├── _index.md          ← Master project registry
    └── 2026-04-08_月30万自動化/
        ├── A_ライティング/  B_SNS運用代行/  C_テンプレ販売/
        └── D_エクセル入力スクレイピング/   ← pipeline/ + templates/ (pipeline_server.mjs target)
```

---

## 会社運営ルール（必読）

**このリポジトリは会社経営のためのAIチームです。** 作業開始前に必ず以下を確認してください：

1. `context/STATE.md` — 最新状態・絶対制約(A1〜A7)・決定ログ（**SessionStartフックが自動ロード**）
2. `company.md` — 会社共通ルール・ディレクトリ構造・役職定義・新役職生成ルール
3. `context/` — オーナーの日記・アイデア・参考資料（意図や背景の把握に使う）
4. 担当役職の `_index.md` — 過去の成果物・進行中タスクの確認

---

## 永続メモリ（記憶）システム

コンテナは使い捨て。**コミット済みファイルだけが永続する。**

- `context/STATE.md` が唯一の「記憶」。`.claude/hooks/session-start.sh` がセッション開始時に
  この内容を stdout に出し、SessionStart の追加コンテキストとして自動ロードする。
- タスク完了時は **必ず** `context/STATE.md`（最新状態・次にやること・決定ログ）と
  該当役職の `_index.md` を更新し、**commit & push する**（push しないと消える）。
- フックは依存インストールをしない（このリポジトリの主作業＝note記事作成にビルド/テストは不要）。

---

## ファイル管理ルール

### 命名規則
- 日付プレフィックス必須：`YYYY-MM-DD_ファイル名.md`
- 下書き・調査中は `research/`、確定・完成版は `outputs/`
- センシティブなファイルは Git にコミットしない（下記「.gitignore」参照）

### .gitignore（機密の取り扱い）
- `CFO/`・`CSO/` の outputs/research は**丸ごと除外**（請求書・契約書・顧客PII）。`.gitkeep` のみ追跡。
- `context/diary/`・`context/ideas/`・`context/references/` は除外（オーナー個人情報）。`.gitkeep` のみ追跡。
- `*_secret* / *_confidential* / *_機密* / *_秘密*`、`.env`、柱Dの納品前成果物・セッション情報も除外。
- ⚠️ **`context/STATE.md` は除外されない**（記憶として追跡・push 必須）。

### _index.md の運用ルール

ファイルを作成・更新するたびに **必ず** 該当役職の `_index.md` 成果物ログに追記する。

```markdown
| 日付 | ファイル名 | 種別 | 概要 | ステータス |
```

- 進行中タスクは完了後に削除しない → ステータスを「完了」に変更する
- 他役職の成果物を参照した場合、自分の `_index.md` のメモ欄に参照元を記載する
- CFO は `_index.md` に金額を記載しない（ファイル名のみ記録する）
- **`CMO/_index.md` と `context/STATE.md` の正本管理は code（Claude Code）専任**。外部ワーカーは編集しない。

### projects/ の使い方

複数役職が関与するタスクは必ず `projects/` に切り出す。サブフォルダは役職別（CMO/ CPO/）か
テーマ別（A_〇〇/ B_〇〇/）のどちらでも可。`brief.md` に採用理由を一言記載する。
開始時に `projects/_index.md` に追記し、完了後も削除せずアーカイブとして残す。

### context/ の使い方

| サブフォルダ | 格納するもの |
|------------|------------|
| `context/STATE.md` | 永続メモリ（最新状態・絶対制約・決定ログ） |
| `context/diary/` | 日記・日常の気づき・感情メモ（gitignored） |
| `context/ideas/` | アイデア・考え事・将来構想（gitignored） |
| `context/references/` | 参考資料・書籍メモ・外部情報（gitignored） |

タスク実行前に必ず参照し、オーナーの意図・背景を把握してから作業を開始する。

---

## 役職ルール

### 役職一覧と担当領域

| 役職 | 役割 | 主な成果物 |
|------|------|----------|
| CDO | 自動化・プロンプト設計・技術検証・役職管理・スキル整備 | プロンプト集、ツール、publisher、ガイド |
| CFO | 数字の正確性・契約・経費・事務 | 請求書、契約書、財務サマリ（gitignored） |
| CMO | マーケティング・コンテンツ企画・集客・note記事執筆 | note記事、SNS投稿、LP、英語版 |
| CPO | 教育コンテンツ・プロダクト設計 | スライド、テンプレート、手順書 |
| CSO | 顧客対話・営業・パイプライン管理 | 提案書、対話ログ、FAQ（gitignored） |
| CAO | 反響分析・トレンド調査・仮説構築・A/Bテスト設計（2026-05-30 新設） | 分析レポート、インサイト、監査結果 |

### 役職間の情報フロー

```
オーナー（context/）
    ├─→ CAO：反響・市場・読者を分析 → CMO/CPO/CSO へインサイト供給
    ├─→ CSO：顧客ニーズ・商談情報 → CMO（マーケ）/ CPO（プロダクト）へ反映
    ├─→ CMO：コンテンツ企画・集客 → CPO（教材・セミナー）と連携
    ├─→ CPO：プロダクト設計・教材 → CFO（価格・契約条件）と整合
    ├─→ CFO：財務・事務管理 → CSO（見積・契約書）を提供
    └─→ CDO：全役職のツール・プロンプト・スキル整備 → 全役職を自動化支援
```

### 新役職の自動生成ルール（CDO 権限）

既存役職に当てはまらず、反復が見込まれ、役割を明確に定義できるタスクが発生した場合、
**CDO は承認不要で即実行してよい**（迷う場合は既存役職で対応＝増やさない方向）。
手順：`新役職名/{_index.md, research/, outputs/}` を作成 → `company.md` の構造/保存先テーブルを更新 →
オーナーへ報告。命名は C?O 形式（重複時は別名）。CAO はこのルールで新設された実例。

---

## code（主）× cowork（副）× 外部ワーカーの役割分担

`docs/role-division.md` / `docs/org.md` / `AGENTS.md` 参照。オーナー確定方針（2026-06-06/07）：

- **Claude Code（code）= 主担当・頭脳**：企画・執筆・整理・分析・台帳/STATE 正本管理・git/PR・
  公開パイプラインの設計と判断まで全部。`main` が canonical。
- **cowork = 副・ミラー環境**：code が物理的にできない「外部ネット／ブラウザ／セッション認証／
  定期実行／並列バッチ」の**実行だけ**を代行。独自に企画・執筆・判断・新規ブランチ作成はしない。
- **外部ワーカー（ChatGPT/Gemini等）**：`AGENTS.md` の作法で参加。最小権限、main直push禁止、
  自分の `worker/<name>-*` ブランチで作業し code がレビューして main へ収束。

### ops/ — エージェント間の非同期キュー

code ↔ cowork の構造化された指示・報告は `ops/` のファイルキューで行う（git に乗る）。

```bash
python3 ops/process_inbox.py list --to code      # 自分宛の未処理を一覧
python3 ops/process_inbox.py show 2026-06-07_001  # 詳細
python3 ops/process_inbox.py take 2026-06-07_001  # 着手（open→in-progress）
python3 ops/process_inbox.py done 2026-06-07_001 --result "5本揃えてcommit済み"  # 完了→processed/へ
python3 ops/process_inbox.py post --from code --to cowork --type instruction \
  --title "..." --body "..."                       # 新規投函
```

ファイル名 `YYYY-MM-DD_NNN_<from>_<to>.yaml`。inbox=code→cowork、outbox=cowork→code、
完了は processed/ へ move（削除しない）。1ファイル=1タスク、結果サマリ必須。

---

## 報告ルール

### 事実と意見を分ける

```
【事実】先月のYouTube登録者数は1,200人増加した。
【考察】コンテンツ投稿頻度を週2回に増やした影響と考えられる。
【提案】来月も同頻度を維持し、効果を検証することを推奨する。
```

### 出力形式
1. **要点** — 結論・変更サマリを最初に示す
2. **詳細** — 根拠・実装内容・補足説明
3. **次アクション** — ユーザーが取るべき手順や選択肢

> ただし「実行して」プロトコル実行時は **B11：報告は要点のみ**（結果1行＋必要な命令1ブロック）。

---

## 行動方針

### 自律的に進めてよい操作
調査（読み取り・検索）／整理・要約・構造化／下書き・設計・提案／コード作成・編集。

### 必ず事前に確認する操作
スクリプト・コマンドの実行（ビルド/テスト/`server.mjs`/`pipeline_server.mjs` 起動・curl 検証含む）／
外部アクセス・外部送信（API・Web取得・git push・PR作成）／破壊的操作（削除・上書き・大規模改修・git reset 等）。

> **例外**：下記「実行して」プロトコルに伴う commit & push は無確認で自動実行してよい（オーナー承認済み）。
> ただし削除・上書き・git reset 等の破壊的操作は例外に含めない。

### 完了時のルール
作業完了時は変更サマリと確認ポイントを提示し、**レビュー依頼（承認）** を出す（「実行して」時を除く）。

### Claude Code 運用の鉄則（かいちのAI大学「Claude Code」動画の学び・2026-07-08反映）
出典と詳細：`CAO/research/2026-07-08_かいちClaude Code動画_学びと設定反映.md`（動画全文＝`CAO/research/kaichi_youtube/`）。

- **3つの黄金律**：①**フォルダーを分ける**（プロジェクト/粒度でコンテキスト管理＝`projects/`・役職・`apps/`）②**まずプランから**（大規模/破壊的は出力前に設計・確認。Plan mode=shift+tab×2）③**検証ループを回す**（作る→テスト→修正。＝「実機検証なき"修正済み"宣言禁止」）。
- **課金の安全（¥0原則の補強）**：有料API/従量課金の発生源を持たない（サムネのGemini撤去は正解）。ツール作成時のAPI従量課金に注意。コストは意識して監視（`/cost`）。
- **機密の安全（4系統は必ず`.gitignore`）**：`.env`/`credentials.*`/SSH秘密鍵`id_*`/AWS鍵・`.pem`・`.key`。「全部コミットして」でも漏れない構造にする（設定済）。
- **破壊的コマンド禁止**：`rm -rf`等の不可逆操作は事前確認必須（governanceと一致）。
- **CLAUDE.md＝憲法/長期記憶**、**役員はサブエージェント化**（`.claude/agents/`）＝かいちの経営役員シリーズと同思想。当社差別化＝「教える」でなく「AIで無人運営している実例(done-by-AI)」。

---

## 絶対制約（A1〜A7・毎セッション確認・`context/STATE.md` 由来）

| # | 制約 | 補足 |
|---|---|---|
| A1 | **外部ネット全面ブロック** | note.com・Google 等すべて HTTP 403。code からの直接投稿/取得/閲覧は不可 |
| A2 | **画像生成不可（code 側）** | 画像生成AIなし。code はサムネを作らない |
| A3 | **サムネはオーナー/cloudが取得（写真風で統一）** | フリー素材/画像AI/Canva 等。形式は全部「写真風」。code は記事に `[写真X]` placeholder を置くだけ |
| A4 | **PII禁止** | 具体的な地区名・町名・住所はファイル・記事・メモに一切書かない（市レベルまでOK） |
| A5 | **テンプレ・適当・誇張NG** | 「Xには、Yがある」連発／同日内重複／「世界唯一」断定 すべて禁止 |
| A6 | **同パターンの英語要約2連続NG** | "If you make things..." 型反復禁止 |
| A7 | **コンテナは使い捨て** | commit & push しない限り消える。STATE.md への記録＋push 必須 |

---

## 「実行して」プロトコル v2（自動実行・オーナー承認済み）

オーナーが **「実行して」**（または「実行」「今日の分」「今日の記事書いて」など）と言ったら、
以下を **承認不要で自動実行** する。

1. **記憶を読む**：`context/STATE.md` と `CMO/_index.md` を最初に確認（STATE.md はフックが自動ロード済み）
2. **対象日の特定**：`CMO/outputs/` で 5本揃っていない最も近い日付を対象に
   - 5本未満 → 不足分を作成して 5本に揃える／5本揃っている → 次の未完成日へ
3. **デフォルト動作 = 対象日分の note 記事を 5 本作成**（CMO主導・CAOが事前選定）
   - **本数：5本厳守**（少なくも多くもない）／**5本中2本は食**（オーナー指示）
   - **同一カテゴリ2日連続を回避**／一次観察（高岡住人視点）を優先
   - 本文はそのまま貼れる完成稿。**英語要約を併記**（記事ごとに別パターン）
   - 記事末尾に **「事実検証ノート」**（✅確実/⚠️要確認/諸説あり）を必ず付ける
   - サムネ：実写は生成不可 →「実写生成プロンプト」or オーナー写真使用前提（`[写真X]` placeholder）
   - クロスポスト素材（Reddit/X/EN）を生成（`gen_all.py` 等）
4. **保存**：`CMO/outputs/YYYY-MM-DD_note記事_*.md`（＋英語版は `CMO/outputs/EN/`、素材は `EN/outputs/`）
5. **記憶を更新**：`CMO/_index.md` の成果物ログと `context/STATE.md`（最新状態・次にやること・決定ログ）
6. **無確認で自動 commit & push**
7. 完了報告（要点のみ＝結果1行＋必要な命令1ブロック）

### 公開（オーナー/cowork 側の作業・code はできない）

| 種類 | コマンド |
|---|---|
| 写真あり公開 | `python3 prepare_photos.py --then-publish --count N --date YYYY-MM-DD` |
| 写真なし公開 | `python3 publish_to_note.py --text-only` |
| 指定記事 | `python3 publish_to_note.py --article <path>` |

> ⚠️ 自動公開には安全ガードあり（未来日付ブロック・テスト記事フィルタ・重複チェック・1日最大5本・
> 並列実行防止）。2026-06-12 の重複/テスト記事インシデント以降、棚卸し完了まで自動公開は慎重運用。

---

## Prompt Variants

### team_prompt.txt — 4-role document creation team
- Roles: 企画（Planning）→ 本文（Body）→ 要約（Summary）→ チェック（Review）
- Shared rules: preserve content, explain jargon, infer intent, output single final version

```bash
./team_copy.sh    # Copy to clipboard (macOS/pbcopy)
./team_show.sh    # Print to stdout
```

### CDO スキル — chinakorea-magazine-monthly
毎月1日（または「マガジン作って」）に中国語6記事＋韓国語6記事の月刊マガジンを Word 出力。
定義：`CDO/outputs/skills/chinakorea-magazine-monthly/SKILL.md`。

---

## Node サーバー

### server.mjs（agent-gateway）
依存ゼロ（`node:http` のみ）の JSON API。`GET /health`・`GET /version`・`POST /echo`（不正JSONは400）・
その他404。ログ `METHOD /path STATUS msms`。起動 `node server.mjs`（`PORT` で変更）。詳細は `README.md`。

### pipeline_server.mjs
iPhone 操作対応パイプラインサーバー（柱D＝案件検索/納品）。`PIPELINE_PORT`（既定3001）、
`PIPELINE_TOKEN`（必須）で認証。`GET /`（操作HTML）・`/status`・`POST /search`・`POST /deliver`・
`/results`・`/log`。対象は `projects/2026-04-08_月30万自動化/D_エクセル入力スクレイピング/`。

> いずれも実行・curl 検証は「必ず事前承認」を取る。

---

## CI / GitHub Actions

| ワークフロー | トリガー | 内容 |
|---|---|---|
| `pages.yml` | push to `main` / 手動 | `tavern.html` を GitHub Pages（`_site/index.html`）にデプロイ |
| `note-thumbnails.yml` | `CMO/outputs/**` 変更時 / 手動 | クラウド（ネット可）で note サムネを Gemini(Imagen3)→Pexels の順に生成し `thumbnails/` にコミット。キーは Repo Secrets（`GEMINI_API_KEY`/`PEXELS_API_KEY`）。bot は `thumbnails/` のみ触るため push ループにならない |

---

## Active Project: 月30万自動化（¥300K/Month Automation）

**目標**: 月収¥300K（2026-04〜06）／**ランニングコスト**: ¥5,800/月
**関与役職**: CMO, CPO, CSO, CDO, CAO ／**フォルダ**: `projects/2026-04-08_月30万自動化/`

### 4つの柱

| 柱 | サービス | 単価 | 備考 |
|----|---------|------|------|
| A  | SEOライティング代行 | ¥15K/記事 | 20本/月目標 |
| B  | SNS運用代行 | ¥50K/社 | 6社目標 |
| C  | テンプレート販売 | ¥500〜¥10K | note/BOOTH（Vol.1販売中） |
| D  | エクセル入力/スクレイピング | — | `pipeline_server.mjs` で iPhone 操作 |

> なお現在の運用上の最優先は **note 記事による高岡・氷見・富山の海外発信**（`AGENTS.md` North Star）。

---

## Notes

- All shell scripts use `#!/bin/zsh` or `#!/bin/bash` with `set -e`; macOS パス前提のものあり（`pbcopy` 等）。
- All prompts and document output are in Japanese.
- Sensitive files (invoices, contracts, customer PII, owner diary/ideas) must not be committed to Git（.gitignore 管理）。
- `inject_js/n<id>.js` は各 note 記事用のブラウザ inject スクリプト（cowork 公開で使用）。
</content>
