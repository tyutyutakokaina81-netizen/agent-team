# AI自動収益化パイプライン

note・YouTube Shorts・Reddit・SNS・CrowdWorks を横断する **コンテンツ生成パイプライン**。

「仕組みはあるが、公開と応募が不足している」状態を解消するための、
**毎日 outputs/ に "公開・応募できる素材" を出し続ける** 共通インフラです。

## クイックスタート

```bash
cd /home/user/agent-team/projects/2026-05-06_AI自動収益化パイプライン
./pipeline/run.sh
```

成功すると `outputs/` に7ファイルが出力されます：

```
outputs/
├── 2026-05-06_2000_youtube_short.md
├── 2026-05-06_2000_heygen_script.md
├── 2026-05-06_2000_kling_prompt.md
├── 2026-05-06_2000_sns_posts.md
├── 2026-05-06_2000_paid_note.md
├── 2026-05-06_2000_crowdworks_application.md
└── 2026-05-06_2000_crowdworks_application.txt
```

## 仕組み

- **テーマは日次で自動ローテ**（`pipeline/themes.py`）
- 同じ日に複数回実行しても同じテーマ＝再現性あり
- 個別ジョブが失敗してもパイプラインは止まらない
- 全件成功すると `logs/posted_{date}_{slug}.log` に "READY" マーカ作成

## ディレクトリ

```
.
├── README.md          ← 本ファイル
├── brief.md           ← プロジェクト概要・5タスク・KPI
├── pipeline/          ← 実行スクリプト群
├── prompts/           ← AIに渡すテンプレート
├── outputs/           ← 生成物（gitignore 対象）
├── logs/              ← 実行ログ（gitignore 対象）
└── docs/
    ├── operation_flow.md
    └── kpi.md
```

## 個別ジョブだけを動かす

```bash
cd pipeline
python3 generate_youtube_short.py
python3 generate_heygen_script.py
python3 generate_kling_prompt.py
python3 generate_sns_posts.py
python3 generate_paid_note.py
python3 generate_crowdworks_application.py
```

## 環境変数（任意）

| 変数 | 用途 | 既定 |
|------|------|------|
| `CW_PROFILE_NAME` | CrowdWorks 応募文の名乗り | `高岡（フリーランス）` |
| `CW_MIN_HOURLY` | 応募チェック時の最低単価 | （なし／表示のみ） |

## cron 設定例（毎日20:00）

```
0 20 * * * cd $HOME/agent-team/projects/2026-05-06_AI自動収益化パイプライン && ./pipeline/run.sh
```

詳細は `docs/operation_flow.md` を参照。

## 設計方針

1. **依存ゼロ運用** — Python 標準ライブラリのみで動く
2. **テーマ固定** — 高岡・富山・地方暮らし・AI副業・50代の働き方
3. **必ず保存** — outputs/ と logs/ は両方書く
4. **完全自動投稿はしない** — 半自動運用で規約リスクを回避
5. **失敗してもパイプラインは止めない** — 個別失敗を吸収

## 関連

- 兄弟プロジェクト：`projects/2026-04-08_月30万自動化/`（事業設計）
- 全社ルール：`/CLAUDE.md`、`/company.md`
