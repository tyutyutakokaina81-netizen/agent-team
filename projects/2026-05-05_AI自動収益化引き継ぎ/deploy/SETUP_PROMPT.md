# Mac 側 Claude Code に貼り付ける完全プロンプト

このファイルは「mac で Claude Code を起動して、下のブロックをそのまま貼り付ければ、ai-auto 全自動システムが動き出す」ための単一プロンプトです。

---

## 使い方

1. mac でターミナルを開く
2. `cd ~/agent-team`（リポジトリが無ければ `git clone` してから）
3. `git pull origin claude/ai-monetization-handover-epkiB` で最新化
4. `claude` コマンドで Claude Code を起動
5. 下の「貼り付けるプロンプト」を**そのままコピペ**して送信
6. Claude Code が手順を1つずつ進めてくれる（途中で確認を求められる）

---

## 貼り付けるプロンプト（ここから下をコピー）

```
~/agent-team/projects/2026-05-05_AI自動収益化引き継ぎ/deploy/ にある AI 自動収益化システム（Plan B：時間分散型 Web 自動化）を、私の mac の ~/ai-auto/ にデプロイし、cron で全自動運用できる状態にしてください。

## 前提
- このプロンプトを貼った時点で、私は mac のターミナルで claude を起動しています
- ~/agent-team/ は既に最新（git pull 済み）です
- Python 3 と pip3 はインストール済みと想定（無ければ案内してください）
- 安全のため初回は DRY_RUN=1（実際には投稿しない）で進めます

## 実行してほしい手順

### Phase 1：デプロイ（自動実行可）
1. `bash ~/agent-team/projects/2026-05-05_AI自動収益化引き継ぎ/deploy/install.sh` を実行
   - これだけで ~/ai-auto/ への配置・依存インストール・Playwright Chromium 取得・DRY_RUN 試運転まで完了します
   - 失敗したらエラーを見せて停止してください

### Phase 2：DRY_RUN 動作確認（自動）
2. `cd ~/ai-auto && DRY_RUN=1 python3 post_reddit.py` を実行 → "OK: DRY_RUN" が出ることを確認
3. `DRY_RUN=1 python3 publish_note.py` → "OK: DRY_RUN: would publish '<タイトル>...'" を確認
4. `DRY_RUN=1 python3 post_x.py` → "OK: DRY_RUN: would tweet '...'" を確認
5. `DRY_RUN=1 python3 apply_crowdworks.py` → "OK: DRY_RUN: would apply to 3 jobs" を確認

### Phase 3：cron 登録（私に確認してから実行）
6. 現在の crontab を `crontab -l` で表示
7. 以下2行を追加する案を提示：
   ```
   0 7 * * * /bin/zsh -lc 'cd $HOME/ai-auto && ./run.sh >> logs/cron.log 2>&1'
   0 * * * * /bin/zsh -lc 'cd $HOME/ai-auto && python3 dispatcher.py >> logs/dispatcher.log 2>&1'
   ```
8. 私が「いい」と返したら `crontab -e` 相当の操作で追加（既存設定は壊さない）

### Phase 4：明日の朝の確認方法を教える（自動）
9. 翌朝の確認コマンドを表示：
   ```
   tail -20 ~/ai-auto/logs/run.log
   tail -20 ~/ai-auto/logs/dispatcher.log
   tail -20 ~/ai-auto/logs/scheduler.log
   cat ~/ai-auto/schedule.json | python3 -m json.tool
   ```

### Phase 5：段階的本番化プランを提示（自動）
10. 以下の14日プランを表で提示してください：

| 期間 | DRY_RUN | 有効化するもの | 確認ポイント |
|------|---------|--------------|-------------|
| Day 1-7 | 1 | なし（観察のみ） | logs/scheduler.log に毎時動作の痕跡があるか |
| Day 8-14 | 0（Reddit のみ） | post_reddit.py 本番化 | .env に REDDIT_* 6項目を設定。1週間 BAN なしで通れば OK |
| Day 15-21 | 0（X 追加） | post_x.py 本番化 | 初回手動ログイン必要。1日3投稿×7日 = 21投稿で BAN なし確認 |
| Day 22-30 | 0（note 追加） | publish_note.py 本番化 | 初回手動ログイン必要。1日1記事×9日 |
| Day 31以降 | 必要に応じて | apply_crowdworks.py 本番化（任意） | **最高リスク**。やらない選択もアリ |

### Phase 6：手動ログイン手順を案内（私が「Reddit本番化したい」「X本番化したい」と言ってから）
- Reddit：reddit.com/prefs/apps で script アプリ作成 → .env の REDDIT_* に値を入れる
- X：~/ai-auto/.browser_profile を Playwright で起動して x.com に手動ログイン（具体コマンド提示）
- note：同様に note.com に手動ログイン
- CrowdWorks：同様に crowdworks.jp に手動ログイン

## 重要な制約
- **私が明示的に「DRY_RUN=0 にして」と言うまで、絶対に DRY_RUN=0 にしない**
- crontab の編集は事前確認必須
- pip install は --user で実行（sudo は使わない）
- BAN リスクのあるサービス（note / X / CrowdWorks）は段階的有効化を厳守
- API 課金は発生しない設計だが、念のため AI_DAILY_BUDGET_JPY=100 のままにする

## 完了の定義
- ~/ai-auto/ に全ファイルが配置されている
- DRY_RUN で各 post スクリプトが OK を返す
- cron に2行追加されている（私の承認後）
- 私が「翌朝の確認方法」を理解した

エラーが出たら止まって相談してください。「とりあえず進める」はしないこと。
```

## プロンプトはここまで（ここから上をコピー）

---

## 補足：mac で Claude Code を初めて使う場合

```bash
# Claude Code のインストール（公式手順）
curl -fsSL https://claude.ai/install.sh | sh

# リポジトリ取得
cd ~ && git clone <REPO_URL> agent-team
cd agent-team
git checkout claude/ai-monetization-handover-epkiB
git pull

# Claude Code 起動
claude
```

その後、上の「貼り付けるプロンプト」をペーストして送信。

---

## トラブル時の問い合わせ用テンプレート

セットアップ中に詰まったら、以下を Claude Code に貼って状況共有：

```
セットアップが Phase X で止まりました。
以下のエラーが出ています：

[エラーメッセージをここに貼る]

~/ai-auto/ の状態：
$ ls ~/ai-auto/
[ls の結果]

~/ai-auto/logs/run.log 末尾：
[tail の結果]
```
