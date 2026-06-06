# Claude Code × Cowork 役割分担

最終更新: 2026-06-07

## なぜこのドキュメントが必要か

同じオーナーのために **Claude Code**（コード・ファイル・git エージェント）と
**Cowork**（ブラウザ自動化・スケジュールタスクのエージェント）が並走している。
現状の問題：

- 役割境界が曖昧で、Cowork が Claude Code が得意な「ファイル整理」「git 操作」を
  ブラウザ UI 経由で何百ターンも消費している
- Claude Code が Cowork が得意な「note 公開」「定期実行」を引き受けようとして、
  そもそも外部ネット遮断のため失敗する
- 連絡手段が PR #12 のコメントだけで、片方向・非構造化・遅延が大きい

→ 得意領域に仕事を振り分けて稼働率を上げる。

---

## 1. Claude Code が担う領域

**特性：** ファイルシステム直アクセス／git・gh CLI／構造化された読み書き／コード実行。
ただし外部ネットは遮断（note.com など 403）、ブラウザ操作は不可、定期実行も不可。

### 1-1. git 操作（独占領域）

- ブランチ作成・切り替え（`claude/<topic>` 系）
- コミット・push（「実行して」プロトコル中は無確認 push 可）
- PR 作成（`gh pr create`）／PR コメント投稿（`gh pr comment`）
- マージコンフリクト解消
- 履歴調査（`git log`, `git blame`, `git diff`）

→ Cowork は GitHub Web UI を触らない。

### 1-2. ファイル・スクリプト生成

- 記事下書き `CMO/outputs/YYYY-MM-DD_*.md` の新規・追記
- Python / シェルスクリプトの作成・修正（`CDO/outputs/note_publisher/`, `CDO/outputs/cross_post/` 等）
- `_index.md` 台帳の正本維持（**Claude Code 側が正本**、実ファイル走査で再生成可能）
- `context/STATE.md` 等メモリファイルの更新

### 1-3. リポジトリ設定のメンテナンス

- `CLAUDE.md`, `company.md`, `.gitignore`, `.github/workflows/*.yml`
- 各役職の `prompt.md`
- SessionStart フック設定

### 1-4. データ処理・分析

- CSV / JSON パース、集計
- ログ解析（公開済み記事数、カテゴリ偏り、英語要約パターン重複検知）
- 重複監査・整合性チェック・テンプレ感セルフチェック
- 海外導線の横展開（英語サブタイトル付与、Travel CTA 統一）

### 1-5. やってはいけない（Claude Code から見て不可能）

| やらない | 理由 |
|---|---|
| note.com への投稿・閲覧 | 外部ネット 403 |
| X / Reddit 投稿 | 同上 + セッション認証なし |
| 画像生成 | 画像生成 AI なし |
| 定期実行（毎朝○時に動く） | コンテナは使い捨て・常駐不可 |
| ブラウザ操作 | Playwright/Chrome なし |

---

## 2. Cowork が担う領域

**特性：** Chrome 経由のブラウザ自動化／セッション Cookie 保持／cron/launchd 相当のスケジューラ／
複数タスク並列。コード生成・git 操作も可能だが**得意ではない**ので最小限に。

### 2-1. ブラウザ自動化（独占領域）

- **note.com への公開**（`publish_to_note.py` 相当の処理を Cowork が直接実行可能）
- **note のサムネ後追い添付**
- **X 投稿**（クロスポスト素材 `EN/outputs/*_x.txt` を使う）
- **Reddit 投稿**（`EN/outputs/*_reddit.md` を使う）
- アクセス解析画面のスクレイピング（PV・国別セッション・リファラ）

### 2-2. スケジュールタスク

- 毎朝のモニタリング（公開状況・コメント・PV）
- 「○時に X 投稿」「○曜に週次レポート」等の cron 的処理
- 公開済み記事の反応集計（CAO が後で読む形でリポジトリに書き戻す）

### 2-3. 複数タスクの並列オーケストレーション

- 「5本同時に公開して」「全記事のサムネを順に上げて」等の大量バッチ
- ブラウザ × N タブの並列処理

### 2-4. セッション認証が必要な操作

- note / X / Reddit / Gmail などログイン状態が要るもの全般
- API キーを持たないサービスへの代理アクセス

### 2-5. やらないでほしい（Claude Code に投げる）

| やらない | 投げ先 |
|---|---|
| `_index.md` の編集 | Claude Code（正本） |
| 大規模コード変更 | Claude Code |
| PR 作成・コメント・マージ | Claude Code |
| 記事本文の執筆 | Claude Code（CMO 役職） |
| `context/STATE.md` の構造変更 | Claude Code |

> 補足：PR #12 では「執筆=Cowork／整理=Claude Code」案も出ているが、
> 現状の運用実績では Claude Code 側（CMO 役職）が執筆実績を積み上げており、
> Cowork はブラウザ系に集中させた方が稼働率が上がる。執筆分担は今後の実測で見直す。

---

## 3. 連携インターフェース（改善案）

### 3-1. 現状の問題

- 連絡手段が **PR #12 のコメントだけ**
- コメントは時系列で流れるので「未処理の指示が何件あるか」が分からない
- Cowork → Claude Code の指示は人間（オーナー）が中継する必要がある
- 構造化されていない自然文なので、Claude Code 側のパースが不安定

### 3-2. 改善案：共有ファイル経由の指示チャネル

ファイルベースの非同期キューを切る。git に乗るので両者から参照可能。

```
ops/
├── inbox/                       ← 未処理の指示
│   ├── 2026-06-07_001_<from>_<to>.md
│   └── 2026-06-07_002_<from>_<to>.md
├── processed/                   ← 処理済み（消さずに移動）
│   └── 2026-06-06_001_*.md
└── README.md
```

#### ファイル形式（YAML フロントマター + 本文）

```markdown
---
id: 2026-06-07_001
from: cowork
to: claude-code
created: 2026-06-07T08:30:00+09:00
priority: normal       # urgent / normal / low
type: instruction      # instruction / report / question
status: open           # open / in-progress / done
---

# 6/14 を 5本に揃えてください

現状 6/14 は 3本のみ（食 1本）。あと食 1本と任意カテゴリ 1本を追加してください。
公開待ち。
```

#### 運用ルール

| アクション | 誰が | やり方 |
|---|---|---|
| 指示を出す | Cowork / Claude Code | `ops/inbox/` に新規ファイル commit |
| 引き受ける | 受け手 | フロントマターの `status: open → in-progress` に編集 + commit |
| 完了する | 受け手 | ファイルを `ops/processed/` に移動 + 結果サマリを末尾追記 |
| 未処理確認 | どちらも | `ls ops/inbox/` で一覧 |

#### PR コメントとの使い分け

- **PR コメント**：人間（オーナー）が見る・議論する用途
- **`ops/inbox/`**：エージェント間の機械的な指示・報告
- 「方針議論」は PR コメント、「タスク発注」は `ops/inbox/`

### 3-3. もう一段上の改善（将来）

- `pipeline_server.mjs`（既存）に `/ops` エンドポイントを生やして
  ファイル commit せずに JSON POST で指示を渡す
- 受信時に Claude Code セッションを wake する webhook を Cowork に提供
- 現状は git 経由の非同期で十分。サーバー化は本数が増えてから検討。

---

## 4. 衝突回避のための所有ルール

| 領域 | 正本 | 編集可能 |
|---|---|---|
| `CMO/outputs/*.md`（記事本文） | 作成者 | 両方（新規追加は衝突しない） |
| `CMO/_index.md`（台帳） | **Claude Code** | Claude Code のみ（再生成可能） |
| `context/STATE.md`（メモリ） | 手動マージ | 両方（追記式・決定ログ消さない） |
| `CDO/outputs/note_publisher/`（公開ツール） | Claude Code | Claude Code（破壊的変更時は別ブランチ） |
| `ops/inbox/`, `ops/processed/`（指示） | なし | 両方 |
| ブランチ命名 | - | `claude/*` = Claude Code、`cowork/*` = Cowork |

---

## 5. 次のステップ

1. このドキュメントを PR #12 にコメントで要約投稿（合意形成）
2. オーナー承認後、`ops/inbox/` ディレクトリを切って初回の往復を試す
3. 2週間運用してインターフェースを見直す（KPI: PR コメント数の減少／指示の取りこぼし数）
