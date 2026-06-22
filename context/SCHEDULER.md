# スケジューラ管理

> 「実行して」の自動トリガー化＆完全自動化の設定

## 自動実行フロー

毎日5:00 UTC（日本時間14:00）に以下が自動実行される想定：

| 時刻 | 実行内容 | 場所 | 担当 |
|------|--------|------|------|
| 14:00 | 本日の記事不足チェック | コンテナ | SessionStart hook |
| 14:05 | 本日の記事5本生成（不足分） | コンテナ | CMO（自動） |
| 14:20 | Reddit/X/EN素材自動生成 | コンテナ | CDO（自動） |
| 14:25 | commit & push | コンテナ | 自動 |
| 05:30 AM次日 | git pull → 公開 → 拡散 | Mac | LaunchAgent |

## セットアップ手順

### ステップ1: Macで LaunchAgent をインストール（1回限り）

```bash
bash ~/agent-team/scripts/setup_launchagent.sh install

# 確認
bash ~/agent-team/scripts/setup_launchagent.sh status
```

結果：毎日 05:30 AM に自動実行開始

### ステップ2: コンテナ側でScheduler Hook を有効化（CDO実装予定）

- SessionStartフック内で「本日の記事数チェック」
- 不足時に自動で記事生成トリガー
- ただし、これにはClaudeの定期タスク実行APIが必要（検討中）

現在は以下を手動実行：
```bash
# セッション開始時に一度だけ
echo "実行して" > /tmp/trigger.txt
```

## スケジュール詳細

### Macのcron実行（毎日5:30 AM JST）

ファイル: `scripts/daily_workflow.sh`

実行内容：
1. git pull origin claude/new-session-jn2hnw
2. python3 CDO/outputs/cross_post/gen_all.py --since $(date +%Y-%m-%d)
3. python3 CDO/outputs/note_publisher/batch_publish.py --date $(date +%Y-%m-%d)
4. 投稿素材をSlack/メールで通知（オプション）

ログ: `~/.claude_daily_YYYYMMDD.log`

### コンテナ内の記事生成（要 定期Task API）

理想形：
```
毎日14:00 UTC → Claude API で「実行して」を送信
    ↓
CMO が記事5本を自動生成
    ↓
CAO が分析を自動生成
    ↓
自動 commit & push
    ↓
翌5:30 AM Macで自動公開
```

現状の制約：
- セッションは「ユーザーが開いた時だけ」アクティブ
- コンテナ側から定期実行タスクは実行不可（スケジュール機能がない）

## 代案案

### Option A: GitHub Actions で記事生成を自動実行

```yaml
# .github/workflows/daily-generate.yml
name: Daily Article Generation
on:
  schedule:
    - cron: '0 5 * * *'  # 毎日 14:00 JST

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: |
          # Claude CLI でコンテナに「実行して」を送信
          claude invoke --message "実行して"
```

これなら完全自動化が実現します（Anthropic側の対応が必要）

### Option B: Macの定期タスク内で Claude API を呼び出し

```bash
# daily_workflow.sh 内で

# ① 記事生成リクエスト
RESPONSE=$(curl -s https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -d '{"model": "claude-opus-4-8", "messages": [{"role": "user", "content": "実行して"}]}')

# ② 記事生成完了まで待機
while [ $(ls CMO/outputs/$(date +%Y-%m-%d)_note記事_*.md | wc -l) -lt 5 ]; do
  sleep 10
done

# ③ クロスポスト＆公開
python3 CDO/outputs/cross_post/gen_all.py --since $(date +%Y-%m-%d)
python3 CDO/outputs/note_publisher/batch_publish.py --date $(date +%Y-%m-%d)
```

## 現在の推奨ワークフロー（実装済）

1. **毎日 5:30 AM** → Macで `daily_workflow.sh` 自動実行
2. **毎日 18:00** → ユーザーが手動で「実行して」を実行（またはScheduler API 実装待ち）
3. **翌5:30 AM** → Macで自動公開＆拡散完了

記事生成の部分のみ手動。その他は完全自動化されます。

## チェックリスト

- [ ] Macで LaunchAgent インストール: `bash ~/agent-team/scripts/setup_launchagent.sh install`
- [ ] 初回テスト実行: `bash ~/agent-team/scripts/daily_workflow.sh` で成功確認
- [ ] Anthropic API Key を Mac の `~/.anthropic` に保存（Option B 使用時）
- [ ] GitHub Actions を設定（Option A 使用時 → Anthropic 実装待ち）
