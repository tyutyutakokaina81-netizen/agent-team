# AI Auto Monetization Project（全自動 / Plan B）

## 目的
note・YouTube Shorts・SNS・CrowdWorks を活用し、**Web自動化込みのフル全自動**で AI 収益化を回す。
時間分散とジッターで検知を下げる設計。BANリスクは依然として存在することを前提に運用する。

## 重要：規約・リスクの理解

| サービス | 自動化方法 | リスク |
|---------|----------|------|
| Reddit | 公式API (PRAW) | 低（レート制限注意） |
| YouTube | 公式API (Data v3) | 低 |
| note | Web自動化 (Playwright) | **中〜高**（規約上グレー） |
| X (Twitter) | Web自動化 (Playwright) | **中〜高** |
| CrowdWorks | Web自動化 (Playwright) | **高**（明示的禁止） |

**初回は必ず `DRY_RUN=1` で試運転**し、ログだけ確認すること。本番化は自己責任で `DRY_RUN=0` にする。

## 全体アーキテクチャ

```
07:00 cron → run.sh
            ├─ generate_daily_outputs.py（4本生成）
            └─ auto_schedule.py（当日のランダム時刻を schedule.json に書き出し）

毎時00分 cron → dispatcher.py
                ├─ schedule.json を読む
                ├─ 現在時刻±15分のpendingタスクを取得
                ├─ 0〜300秒のランダムジッター待機
                └─ kind に応じて post_*.py / publish_*.py / apply_*.py を実行
                   └─ 成功時：published.csv に自動追記
                   └─ 連続5回失敗：当日停止 + 通知
```

## 投稿時刻の分散ルール

| kind | 時間帯候補 | 1日上限 |
|------|----------|------:|
| note | 7-9 / 12-13 / 21-22 のいずれかでランダム1本 | 1 |
| x | 7-9 / 12-13 / 18-20 で各1回（計3本） | 3 |
| reddit | 22-23 / 5-7（米国朝） | 1 |
| crowdworks | 平日 10-12 / 13-17 でランダム | 3 |

**毎日違う時刻**＋**毎時実行のジッター 0〜5分**で、Botパターンを薄める。

## 構成

```
~/ai-auto/
├── README.md
├── requirements.txt
│
├── 朝の生成
│   ├── run.sh
│   ├── generate_daily_outputs.py
│   ├── auto_schedule.py        # 当日のランダム時刻を組む
│   └── _scheduler.py           # スケジューラ共通
│
├── 自動投稿
│   ├── dispatcher.py           # cron毎時起動の中継
│   ├── _browser.py             # Playwright共通（人間挙動）
│   ├── publish_note.py         # note 自動公開
│   ├── post_x.py               # X 自動投稿
│   ├── post_reddit.py          # Reddit 自動投稿（PRAW）
│   └── apply_crowdworks.py     # CW 自動応募
│
├── 生成
│   ├── generate_note.py / generate_paid_note.py
│   ├── generate_seo_article.py / generate_proposal.py
│   ├── generate_reddit.py / generate_youtube_short.py
│   └── cw_apply.py
│
├── 計測
│   ├── published.py            # 公開記録（自動 or 手動）
│   ├── kpi.py                  # L1/L2/L3 別売上
│   └── auto_post.py            # 最新生成物確認
│
├── prompts/
│   ├── themes.json / polish_prompts.md
│   └── note_paid.md / youtube_shorts.md
│
├── schedule.json   ← 当日の予定（.gitignore）
├── published.csv   ← 公開記録（.gitignore）
├── logs/ outputs/ .cost_log.json   ← 全て.gitignore
└── .env / .env.example
```

## 初回セットアップ手順

```bash
cd ~/ai-auto

# 1. Python 依存
pip install -r requirements.txt
playwright install chromium

# 2. 環境変数
cp .env.example .env
# DRY_RUN=1 のままにしておく（必須）
# Reddit を使うなら REDDIT_* を埋める

# 3. ブラウザプロファイルを手動で初期化（一度だけ）
python3 -c "
from playwright.sync_api import sync_playwright
from pathlib import Path
profile = Path.home() / '.ai-auto-profile'
profile.mkdir(exist_ok=True)
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(str(profile), headless=False)
    page = ctx.new_page()
    page.goto('https://note.com/login')
    input('note にログインしたら Enter')
    page.goto('https://x.com/login')
    input('X にログインしたら Enter')
    page.goto('https://crowdworks.jp/login')
    input('CrowdWorks にログインしたら Enter')
    ctx.close()
"

# 4. DRY_RUN で試運転
./run.sh
python3 dispatcher.py  # 何も起きないなら時刻が合うのを待つ

# 5. ログを確認
cat logs/scheduler.log
cat logs/run.log

# 6. 数日DRY_RUNで様子を見て、問題なければ .env で DRY_RUN=0
```

## cron 例

```cron
# 朝7:00 生成 + 当日スケジュール組
0 7 * * * /bin/zsh -lc 'cd $HOME/ai-auto && ./run.sh'

# 5分後にスケジュール再生成（念のため）
5 7 * * * /bin/zsh -lc 'cd $HOME/ai-auto && set -a && source .env && set +a && python3 auto_schedule.py'

# 毎時0分に dispatcher 起動
0 * * * * /bin/zsh -lc 'cd $HOME/ai-auto && set -a && source .env && set +a && python3 dispatcher.py >> logs/dispatcher.log 2>&1'
```

## 安全装置（既定 ON）

| 装置 | 動作 |
|------|------|
| `DRY_RUN=1`（既定） | ブラウザを開かず投稿スキップ。ログだけ |
| 1日上限 | note 1 / x 3 / reddit 1 / crowdworks 3 |
| 連続失敗5回 | 当日の自動化を完全停止＋通知 |
| ジッター | 各タスク前に 0〜300秒のランダム待機 |
| User-Agent 偽装 | 実 Chrome に偽装 |
| Cookie/セッション再利用 | 毎回ログインせず実プロファイル使用 |

## トラブル時

| 症状 | 対処 |
|------|------|
| 「未ログイン状態」エラー | 手動で `~/.ai-auto-profile` Chromium を起動して再ログイン |
| 連続失敗で停止した | `schedule.json` を消すと翌日リセット |
| BANされた | **即座に DRY_RUN=1 に戻し、当該サービスの自動化を一時停止** |
| API課金が出ている | `_ai.py` の DAILY_BUDGET_JPY を 0 にする or キーを削除 |

## 推奨運用

1. **最初の7日：DRY_RUN=1** でログだけ見る
2. **次の7日：Reddit のみ本番（API公式・低リスク）**
3. **次の14日：X 本番**
4. **次の30日：note 本番**
5. **CrowdWorks は最後**（最高リスク・最後まで手動でも良い）

段階的に有効化することで、何かあった時にどこが原因かを切り分けられる。
