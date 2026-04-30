# CLAUDE.md

このファイルは、Claude Code（claude.ai/code）がこのリポジトリで作業する際のガイダンスを提供します。

---

## AI従業員運用規約（最優先・全行動の絶対基準）

### 1. セキュリティ・情報保護 (Security First)
- **認証情報の完全保護**: `.env`, `*.pem`, `credentials.json`, `config.*` など認証に関わるファイルへのアクセス・外部送信・上書きを厳禁。
- **個人情報の保護**: 顧客データ・PII を含むファイルを扱う際は必ず匿名化確認を人間に求め、生データを外部コンテキストに含めない。
- **情報の非公開**: 指示範囲外のディレクトリへのアクセス、または不明な外部API・ドメインへのデータ送信前に必ず許可を得る。

### 2. 破壊的操作の制限 (Damage Control)
**「影響予測の提示」→「バックアップ確認」→「人間の明示的承認」**の3ステップを必ず踏む。

破壊的操作の定義：
- ファイル・ディレクトリの一括削除（`rm -rf` 等）
- git履歴の改変（`.git` 操作・`push -f` 等）
- DB構造変更・データ削除（`DROP`, `TRUNCATE`, `DELETE` 等）
- インフラ設定の初期化（Terraform, Docker等）

### 3. 運用費用の制御 (Cost Guardrail)
- **ループの自己停止**: 同一エラーに3回連続失敗した場合、即座に中断して人間に報告する。
- **高額消費の警告**: 1タスクで100,000トークン超が予想される場合、事前に報告して承認を得る。

### 4. AI従業員マインドセット
- **迷ったら止まる**: 指示が曖昧、またはシステムを不安定にする懸念がある場合は独断で進めず質問する。
- **透明性**: 変更理由・実行内容は人間が監査できる形で残す。
- **目的の完遂**: 月収¥300K達成という会社利益を念頭に、システム化されたAI活用を目指す。

---

## 目的

月収¥300K達成を目指すAI自動経営フレームワーク。  
5つのC?O役職（CDO/CFO/CMO/CPO/CSO）がそれぞれ作業ログ・調査・成果物を管理する。  
すべてのドキュメントと成果物は日本語で出力する。

---

## リポジトリ構造

```
/home/user/agent-team/
├── CLAUDE.md                  ← このファイル（Claude Code ガイダンス）
├── README.md                  ← agent-gateway サーバードキュメント
├── company.md                 ← 会社共通ルール・役職定義・ガバナンス（必読）
├── server.mjs                 ← 依存ゼロの Node.js JSON API サーバー（ポート 3000）
├── pipeline_server.mjs        ← iPhone 対応パイプライン制御サーバー（ポート 3001）
├── team_prompt.txt            ← 4役割・多エージェント文書作成プロンプト
├── team_copy.sh               ← team_prompt.txt をクリップボードにコピー（zsh/macOS）
├── team_show.sh               ← team_prompt.txt を stdout に出力
│
├── now                        ← Mac用ワンコマンド公開（note/X/YouTube/案件応募）
├── setup                      ← Mac初回セットアップ（ライブラリ・LaunchAgent登録）
├── cron_run.sh                ← サーバー自動実行ラッパー（cron から呼ばれる）
│
├── auto_content_loop.py       ← コンテンツキュー自動補充（note記事・X投稿）
├── auto_note_publish.py       ← note記事自動公開（Playwright・Chromeセッション使用）
├── auto_x_post.py             ← X投稿自動実行（Playwright・Chromeセッション使用）
├── auto_x_api_post.py         ← X投稿 API直接投稿版（Chrome不要・要APIキー設定）
├── auto_youtube_produce.py    ← YouTube長尺動画生成（pyopenjtalk TTS・Pillow）
├── auto_youtube_shorts.py     ← YouTube Shorts生成（縦型720x1280）
├── auto_youtube_upload.py     ← YouTube自動アップロード（Playwright）
├── auto_wikimedia_photos.py   ← Wikimedia Commons写真取得（CC BY-SA・¥0）
├── auto_affiliate.py          ← アフィリエイトリンク自動挿入
├── auto_repurpose.py          ← note記事→X投稿+Shorts台本 横断変換
├── auto_job_apply.py          ← CrowdWorks/Lancers 案件自動サーチ＆応募（Playwright）
├── auto_kpi_tracker.py        ← KPI自動計測（YouTube/note/X フォロワー・PV）
├── auto_self_eval.py          ← 自己評価ループ（10項目100点満点・自動改善）
├── .claudecode.md             ← AI従業員運用規約（CLAUDE.md に統合済み・参照用）
├── .sessions/                 ← 実行状態ファイル（キュー・ログ・cookieは除外）
│
├── mac_auto_cookie_all.py     ← [Mac専用] Chrome から全サービスのセッションを一括取得
├── mac_booth_publish.py       ← [Mac専用] BOOTH商品出品（2ステップ方式）
├── mac_booth_refresh.py       ← [Mac専用] BOOTH検索順位維持（週次更新日時更新）
├── mac_check_sales.py         ← [Mac専用] BOOTH売上30分ごと自動チェック＋Mac通知
├── mac_daily_report.py        ← [Mac専用] 毎朝8時の日次レポート＋Mac通知
├── mac_pipeline.py            ← [Mac専用] Lancers/CW 全自動パイプライン
├── booth_requests.py          ← BOOTHクライアントライブラリ（mac_booth_publish.py が使用）
├── check_booth_sales.py       ← BOOTH売上チェック（Playwright版）
├── daily_report.py            ← サーバー用日次レポート（cron から呼び出し可）
├── setup_booth.py             ← BOOTHセッション初期設定
│
├── CDO/                       ← 最高デジタル責任者（システム・自動化・技術・役職管理）
│   ├── _index.md              ← 成果物ログ・進行中タスク（台帳）
│   ├── prompt.md              ← 役割定義・性格・ワークフロー・境界線
│   ├── research/              ← 下書き・試作・調査
│   └── outputs/               ← 最終成果物: プロンプト集・ツール・ガイド
│
├── CFO/                       ← 最高財務責任者（財務・契約・事務）
│   ├── _index.md
│   ├── prompt.md
│   ├── research/              ← 契約・税務調査の下書き
│   └── outputs/               ← 最終: 請求書・契約書・経費報告
│
├── CMO/                       ← 最高マーケティング責任者（コンテンツ・SNS・LP・YouTube）
│   ├── _index.md
│   ├── prompt.md
│   ├── research/              ← コンテンツ戦略の下書き
│   └── outputs/               ← 最終: 台本・SNS投稿・LP
│
├── CPO/                       ← 最高プロダクト責任者（コース・セミナー・テンプレート）
│   ├── _index.md
│   ├── prompt.md
│   ├── research/              ← カリキュラム・プロダクト調査の下書き
│   └── outputs/               ← 最終: スライド・テンプレート・手順書
│
├── CSO/                       ← 最高営業責任者（顧客対話・提案・パイプライン管理）
│   ├── _index.md
│   ├── prompt.md
│   ├── research/              ← 顧客分析・市場調査の下書き
│   └── outputs/               ← 最終: 提案書・対話ログ・FAQ
│
├── CCO/                       ← 最高コマース責任者（2026-04-10 新設）
│   ├── _index.md              ← BOOTH/ランサーズ出品管理・価格戦略
│   ├── research/              ← プラットフォーム調査・競合分析
│   └── outputs/               ← 出品ページ・価格戦略・プラットフォーム設定
│
├── CGO/                       ← 最高グロース責任者（2026-04-10 新設）
│   ├── _index.md              ← 新規開拓・見込み客管理・成長戦略
│   ├── research/              ← 見込み客調査・市場開拓
│   └── outputs/               ← プロスペクトリスト・DMスクリプト・アクションプラン
│
├── context/                   ← オーナーの一次情報（タスク前に必ず参照）
│   ├── diary/                 ← 日記・日常の気づき・感情メモ
│   ├── ideas/                 ← アイデア・考え事・将来構想
│   └── references/            ← 参考資料・書籍メモ・外部情報
│
└── projects/                  ← 役職横断プロジェクト
    ├── _index.md              ← プロジェクト一覧（マスター台帳）
    └── 2026-04-08_月30万自動化/  ← 進行中プロジェクト（月30万自動化）
        ├── brief.md           ← 目標・期間・関与役職
        ├── cashflow.md        ← 月次キャッシュフロー予測・シナリオ分析
        ├── cost_breakdown.md  ← ツール費用・プラットフォーム手数料分析
        ├── A_ライティング/    ← 柱A: SEOライティング（service_design・service_page）
        ├── B_SNS運用代行/     ← 柱B: SNS運用代行（service_design・proposal_templates）
        ├── C_テンプレ販売/    ← 柱C: テンプレート販売（Vol.1〜4 コンテンツファイル）
        └── D_エクセル入力スクレイピング/  ← 柱D: 自動受注パイプライン
            ├── brief.md
            ├── pipeline/      ← Python 自動化スクリプト（00〜06 + run_pipeline.py）
            ├── templates/     ← 応募文テンプレート
            └── outputs/       ← 納品物ファイル（gitignore 対象）
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
| CCO | BOOTH/note/ランサーズ出品管理・価格戦略 | 出品ページ、価格設定、プラットフォーム戦略 |
| CGO | 新規クライアント開拓・見込み客アプローチ | プロスペクトリスト、DMスクリプト、成長計画 |
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

## プロンプトバリアント

### team_prompt.txt — 4役割文書作成チーム
- 役割: 企画（Planning）→ 本文（Body）→ 要約（Summary）→ チェック（Review）
- ユースケース: 一般的な社内文書作成
- 共通ルール: コンテンツを保持し、専門用語を説明し、意図を推察し、最終版を1つ出力する

```bash
./team_copy.sh    # クリップボードにコピー（macOS/pbcopy）
./team_show.sh    # stdout に出力
```

---

## サーバー

### agent-gateway（server.mjs）

#### 概要
- `server.mjs` は依存ゼロ（Node標準 `node:http` のみ）の JSON API サーバー
- バインド先: `127.0.0.1`（ローカルのみ）
- エンドポイント:
  - `GET /health` → `{ ok: true, time: ISO文字列 }`
  - `GET /version` → `{ name: "agent-gateway", version: "0.1.0" }`
  - `POST /echo` → 受け取ったJSONをそのまま返す（不正JSONは 400）
  - その他は 404 → `{ error: "Not Found" }`
- ログ: `METHOD /path STATUS 処理時間ms` を stdout に出力
- ステータスコード: 200 / 400（不正JSON）/ 404（未定義パス）/ 500（サーバーエラー）

#### 起動
```bash
node server.mjs           # デフォルト PORT=3000
PORT=8080 node server.mjs # ポート変更
```

#### 動作確認（curl）
```bash
curl -s http://127.0.0.1:${PORT:-3000}/health | python3 -m json.tool
curl -s http://127.0.0.1:${PORT:-3000}/version | python3 -m json.tool
curl -s -X POST http://127.0.0.1:${PORT:-3000}/echo \
  -H 'Content-Type: application/json' -d '{"hello":"world"}' | python3 -m json.tool
curl -s -X POST http://127.0.0.1:${PORT:-3000}/echo \
  -H 'Content-Type: application/json' -d 'not json' | python3 -m json.tool
curl -s http://127.0.0.1:${PORT:-3000}/unknown | python3 -m json.tool
```

---

### パイプラインサーバー（pipeline_server.mjs）

#### 概要
- `pipeline_server.mjs` は柱D（エクセル入力・スクレイピング）の自動受注パイプラインを  
  iPhone / スマートフォンから操作するための HTTP 制御サーバー
- バインド先: `0.0.0.0`（LAN 内の iPhone からアクセス可能）
- 認証: `PIPELINE_TOKEN` 環境変数（Bearer トークン または URLクエリパラメータ `?token=`）
- Python スクリプトをサブプロセスで起動し、結果を JSON で返す

#### エンドポイント

| メソッド | パス | 認証 | 概要 |
|---------|------|------|------|
| `GET /` | HTML パネル | 不要 | iPhone 操作パネル（ブラウザUI） |
| `GET /status` | JSON | 不要 | パイプライン稼働状況（idle/running/done/error） |
| `POST /search` | JSON | 必要 | 案件検索フェーズ開始（`run_pipeline.py search`） |
| `POST /deliver` | JSON | 必要 | 納品フェーズ開始（`run_pipeline.py deliver`） |
| `GET /results` | JSON | 必要 | 最新の案件評価結果（`*_evaluated.json`） |

#### 起動
```bash
PIPELINE_TOKEN=your-secret-token node pipeline_server.mjs   # デフォルト PORT=3001
PIPELINE_PORT=8081 PIPELINE_TOKEN=xxx node pipeline_server.mjs
```

#### 状態管理
- 同時実行は 1 フェーズのみ（実行中に別フェーズを起動すると 409 を返す）
- ログは最新 200 行をインメモリで保持（`GET /status` で最新 50 行を返す）
- 結果ファイルは `D_エクセル入力スクレイピング/outputs/` から最新の JSON を自動取得

#### 運用ルール
- 実行・curl での検証は「必ず事前承認」を取る
- `PIPELINE_TOKEN` 未設定時は警告を出力するが起動は続行する（開発環境のみ許容）

---

## 柱D：自動受注パイプライン（Python）

### 概要

`projects/2026-04-08_月30万自動化/D_エクセル入力スクレイピング/pipeline/` 配下の  
Python スクリプト群がクラウドワークス・ランサーズの案件を自動処理する。

### パイプライン構成

```
00_session_setup.py  ← ブラウザログイン・セッション保存（初回のみ手動）
01_search.py         ← 案件検索・詳細取得
02_evaluate.py       ← 案件評価・スコアリング（GO / CAUTION / NO-GO）
03_apply.py          ← 応募文生成・ブラウザ自動オープン
04_execute.py        ← 作業実行（Excel入力・スクレイピング）
05_review.py         ← 念査（品質チェック）
06_deliver.py        ← 納品文生成・納品ページ自動オープン
run_pipeline.py      ← 統合エントリポイント
```

### 実行方法

```bash
# 初回セットアップ（セッション確認）
python run_pipeline.py setup

# フェーズ1: 検索 → 評価 → 応募文生成
python run_pipeline.py search

# フェーズ2: 受注後の作業実行 → 念査 → 納品準備
python run_pipeline.py deliver
```

### 人手介入が必要な箇所（設計上2〜3回のみ）

1. 初回ログイン（`00_session_setup.py` 実行時）
2. 応募ボタンのクリック（ブラウザが自動で開くので押すだけ）
3. 納品ボタンのクリック（ファイルを添付して押すだけ）

### 出力ファイル
- `outputs/*_applications.json` — 応募情報（評価スコア・応募文・URL）
- `outputs/*_evaluated.json` — 評価済み案件リスト
- `outputs/` は `.gitignore` 対象（顧客データ・納品物を含むため）

---

## 進行中プロジェクト：月30万自動化（¥300K/月）

**目標**: 3ヶ月以内に月収¥300K達成（2026-04 〜 2026-06）  
**ランニングコスト**: ¥5,800/月（Claude Pro ¥3K + Canva ¥1.5K + Microsoft 365 ¥1.3K）  
**実質追加コスト**: ¥0〜1,300/月（Claude Code 契約済み・Google スプレッドシート活用の場合）  
**関与役職**: CMO, CPO, CSO, CDO  
**フォルダ**: `projects/2026-04-08_月30万自動化/`

### 4つの収益柱

| 柱 | サービス | 単価 | 月収目標 | 担当役職 |
|----|---------|------|---------|---------|
| A | SEOライティング代行 | ¥15K/記事 × 20本 | ¥300K | CSO・CMO・CDO |
| B | SNS運用代行 | ¥50K/社 × 6社 | ¥300K | CMO・CSO・CDO |
| C | テンプレート販売（note/BOOTH） | ¥500〜¥10K | ¥30K〜 | CPO・CMO・CDO |
| D | エクセル入力・スクレイピング受注 | 案件単価 | ¥100K〜 | CDO・CSO |

### 売上予測（現実的シナリオ）

| 月 | 月収 | 手取り（コスト差引） | 累計 |
|----|------|-------------------|------|
| Month 1 | ¥10K | ¥4,200 | ▲¥1,600 |
| Month 2 | ¥155K | ¥149,200 | ¥147,600 |
| Month 3 | ¥330K | ¥324,200 | ¥471,800 |

→ 詳細は `cashflow.md`・`cost_breakdown.md` を参照

### テンプレート販売（柱C）進捗

| Vol | タイトル | 価格 | ステータス |
|-----|---------|------|----------|
| Vol.1 | フリーランス収支管理スプレッドシート | ¥980 | **販売中（note）** |
| Vol.2 | SNSコンテンツカレンダー | 設計済 | 制作中 |
| Vol.3 | 飲食店向けプロンプト集 | 設計済 | 制作中 |
| Vol.4 | バンドルパック | 設計済 | Vol.1-3完成後 |

---

## 備考

- すべてのシェルスクリプトは `#!/bin/zsh` + `set -e` を使用
- シェルスクリプトは `$HOME/agent-team/` をリポジトリパスとして参照（macOS `pbcopy` 前提）
- すべてのプロンプトとドキュメント出力は日本語
- センシティブなファイル（請求書・契約書・顧客PII・納品物）は Git にコミットしない
- `pipeline_server.mjs` の出力ディレクトリ `outputs/` は `.gitignore` 対象
