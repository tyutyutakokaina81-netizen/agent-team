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
7. 以下4行を追加する案を提示（**A案：Plan B + 週1ハイブリッド + BAN検知 構成**）：
   ```
   # 朝7時：生成＋当日スケジュール
   0 7 * * * /bin/zsh -lc 'cd $HOME/ai-auto && ./run.sh >> logs/cron.log 2>&1'
   # 毎時：自動投稿ディスパッチ
   0 * * * * /bin/zsh -lc 'cd $HOME/ai-auto && python3 dispatcher.py >> logs/dispatcher.log 2>&1'
   # 朝9時：直近2週間の投稿が生きているか確認（BAN早期発見）
   0 9 * * * /bin/zsh -lc 'cd $HOME/ai-auto && python3 ban_detector.py >> logs/ban_check.log 2>&1'
   # 日曜18時：高単価候補3本を骨組み生成（人がWeb AIで肉付け）
   0 18 * * 0 /bin/zsh -lc 'cd $HOME/ai-auto && python3 sunday_polish.py >> logs/sunday.log 2>&1'
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

### Phase 5：A 案（Plan B + 週1ハイブリッド）の段階的本番化プランを提示（自動）

10. 以下の14日プランと A 案の運用プロトコルを表で提示してください：

**段階的本番化プラン**

| 期間 | DRY_RUN | 有効化するもの | 確認ポイント |
|------|---------|--------------|-------------|
| Day 1-7 | 1 | なし（観察のみ） | logs/scheduler.log に毎時動作の痕跡があるか |
| Day 8-14 | 0（Reddit のみ） | post_reddit.py 本番化 | .env に REDDIT_* 6項目を設定。1週間 BAN なしで通れば OK |
| Day 15-21 | 0（X 追加） | post_x.py 本番化 | 初回手動ログイン必要。1日3投稿×7日 = 21投稿で BAN なし確認 |
| Day 22-30 | 0（note 追加） | publish_note.py 本番化 | 初回手動ログイン必要。1日1記事×9日 |
| Day 31以降 | 必要に応じて | apply_crowdworks.py 本番化（任意） | **最高リスク**。やらない選択もアリ |

**A 案 週次ルーチン（オーナーが守る）**

| 曜日・時刻 | やること | 所要 |
|----------|---------|-----:|
| 平日 朝 | 何もしない（cron で全自動） | 0分 |
| 平日 朝9時 | ban_detector の結果をログで確認（異常時のみ対応） | 1分 |
| 日曜 18時 | sunday_polish.py が高単価候補3本を自動生成 → 通知 | 0分 |
| 日曜 18:00-19:00 | claude.ai に prompts/polish_prompts.md を貼って3本を肉付け | 30〜60分 |
| 日曜 19:00-19:30 | 1) 有料note公開（¥2,980） 2) SEO記事を CW 案件に提案 3) 提案書を法人案件に応募 | 30分 |
| 日曜 19:30 | published.py × 3 で記録 → kpi.py で進捗確認 | 5分 |

**月収目安（A 案 BAN リスク調整後）**

| 月 | 売上 | 主な構成 |
|----|-----:|--------|
| M1 | ¥42K | Plan B量 + 有料note¥2,980×4 |
| M2 | ¥84K | + SEO記事¥15K×2 |
| M3 | ¥146K | + ¥15K×4 |
| M4 | ¥210K | + AI支援¥30K |
| M5 | ¥276K | + 月額契約¥50K |
| M6 | ¥350K | + 月額×2社 |

**6ヶ月リスク調整後利益：¥831K（時給¥6,648相当）**

### Phase 6：手動ログイン手順を案内（私が「Reddit本番化したい」「X本番化したい」と言ってから）
- Reddit：reddit.com/prefs/apps で script アプリ作成 → .env の REDDIT_* に値を入れる
- X：~/ai-auto/.browser_profile を Playwright で起動して x.com に手動ログイン（具体コマンド提示）
- note：同様に note.com に手動ログイン
- CrowdWorks：同様に crowdworks.jp に手動ログイン

### Phase 7：iPhone から確認・操作できるようにする（私が「iPhone対応もする」と言ったら）

11. `.env` に `AI_AUTO_TOKEN` を生成して追記：
    ```bash
    echo "AI_AUTO_TOKEN=$(openssl rand -hex 24)" >> ~/ai-auto/.env
    ```
12. API サーバー起動：
    - mac内のみ：`~/ai-auto/run_server.sh`
    - 同一LAN公開：`~/ai-auto/run_server.sh lan`
    - mac 常駐：`cp ~/ai-auto/com.aiauto.server.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.aiauto.server.plist`
13. mac の IP アドレスとトークンを表示し、`~/ai-auto/iphone_shortcuts.md` を読むよう案内
14. iPhone のショートカットアプリで4本のショートカットを作成（KPI閲覧 / 生成物表示 / 公開記録 / DRY_RUN切替）
15. SSH 補助レシピも案内（mac で「リモートログイン」を有効化する手順を提示）

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
