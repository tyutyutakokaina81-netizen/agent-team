# 日次オペレーションフロー

```
1. cron (07:00 / 20:00) → run.sh 実行
2. generate_daily_outputs.py が以下6本を順番に生成：
   ├── YouTube Shorts 台本
   ├── HeyGen Annie スクリプト
   ├── Kling AI 動画プロンプト
   ├── SNS / Reddit 投稿セット
   ├── 有料note 下書き
   └── CrowdWorks 応募文
3. outputs/ に 7 ファイル（応募文は md+txt 二本）保存
4. 全件成功で logs/posted_{date}_{slug}.log マーカ作成
5. 人間が確認 → 公開・応募
6. 公開時刻を logs/posted_{date}_{slug}.log に追記
```

## 必ずやる3つ（毎日）

1. **note記事を1本公開する**（無料 or 有料どちらでも）
2. **CrowdWorksに1件応募する**（生成された応募文ベース）
3. **cronが正常動作しているか logs/run.log の末尾を確認する**

## 起動コマンド

### 手動実行
```
cd /home/user/agent-team/projects/2026-05-06_AI自動収益化パイプライン
./pipeline/run.sh
```

### cron 例（macOS / Linux 共通、毎日20:00）
```
0 20 * * * cd $HOME/agent-team/projects/2026-05-06_AI自動収益化パイプライン && ./pipeline/run.sh
```

### launchd 例（macOS）
LaunchAgent plist を ~/Library/LaunchAgents/com.takaoka.ai-monetization.plist に配置：
```xml
<key>ProgramArguments</key>
<array>
  <string>/bin/zsh</string>
  <string>-c</string>
  <string>cd $HOME/agent-team/projects/2026-05-06_AI自動収益化パイプライン && ./pipeline/run.sh</string>
</array>
<key>StartCalendarInterval</key>
<dict><key>Hour</key><integer>20</integer><key>Minute</key><integer>0</integer></dict>
```

## 失敗時の動き

- 個別ジョブが失敗しても、他のジョブは続行する。
- 失敗したジョブ名は `logs/run.log` に `FAILED <name>` として記録される。
- 連続3日同じジョブが失敗していたら、原因調査が必要：
  - `kling_prompt` 失敗 → API/有料プラン関係（テキスト生成は影響なし）
  - その他失敗 → コード起因の可能性が高い

## 主要ログ

| ファイル | 用途 |
|---------|------|
| `logs/run.log` | 起動／個別ジョブ成功・失敗 |
| `logs/daily.log` | 1日のサマリ |
| `logs/posted_{date}_{slug}.log` | 「準備完了」または「公開済」マーカ |
