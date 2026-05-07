# PDCA スケジュール自動化セットアップ

**目的**：朝会・夕方チェックインを毎日自動実行する。
**対象 OS**：macOS（推奨）／Linux／Windows
**費用**：¥0（OS 標準機能のみ使用、新規 SaaS 不要）

---

## 全体構成

```
07:30  ── morning_meeting.mjs 自動実行
       ↓
       朝会レポート生成（CDO/research/meetings/YYYY-MM-DD_morning.md）
       ↓
       オーナーがレポートを読む（1分）
       ↓
       Top3 アクション実行
       ↓
17:00  ── evening_checkin.mjs 自動実行
       ↓
       夕方チェックイン生成 + スタンドアップ自動更新
       ↓
       オーナーが記入（5分）
       ↓
       明日の朝会に自動反映
```

---

# macOS：launchd で自動実行（推奨）

macOS は cron より launchd が標準。下記の plist を作成すれば毎日自動実行されます。

## 朝会の自動化

### 1. plist ファイル作成

```bash
mkdir -p ~/Library/LaunchAgents
```

`~/Library/LaunchAgents/com.agent-team.morning-meeting.plist` を作成：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.agent-team.morning-meeting</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/node</string>
        <string>/Users/YOUR_USERNAME/agent-team/CDO/outputs/morning_meeting.mjs</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/YOUR_USERNAME/agent-team</string>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>7</integer>
        <key>Minute</key>
        <integer>30</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>/tmp/agent-team-morning.log</string>

    <key>StandardErrorPath</key>
    <string>/tmp/agent-team-morning.err</string>
</dict>
</plist>
```

### 2. 置換が必要な箇所

```
- /usr/local/bin/node → 実際の node のパス（`which node` で確認）
- /Users/YOUR_USERNAME/agent-team/ → リポジトリの絶対パス
```

### 3. 登録

```bash
launchctl load ~/Library/LaunchAgents/com.agent-team.morning-meeting.plist
```

### 4. 即時実行テスト

```bash
launchctl start com.agent-team.morning-meeting
```

→ `/tmp/agent-team-morning.log` を確認して動作確認。

### 5. 解除

```bash
launchctl unload ~/Library/LaunchAgents/com.agent-team.morning-meeting.plist
```

---

## 夕方チェックインの自動化

`~/Library/LaunchAgents/com.agent-team.evening-checkin.plist` を作成：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.agent-team.evening-checkin</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/node</string>
        <string>/Users/YOUR_USERNAME/agent-team/CDO/outputs/evening_checkin.mjs</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/YOUR_USERNAME/agent-team</string>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>17</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>/tmp/agent-team-evening.log</string>

    <key>StandardErrorPath</key>
    <string>/tmp/agent-team-evening.err</string>
</dict>
</plist>
```

登録：

```bash
launchctl load ~/Library/LaunchAgents/com.agent-team.evening-checkin.plist
```

---

# Linux：crontab で自動実行

### 1. crontab 編集

```bash
crontab -e
```

### 2. 追加する行

```cron
# 朝会（毎朝7:30）
30 7 * * * cd /home/USER/agent-team && /usr/bin/node CDO/outputs/morning_meeting.mjs >> /tmp/agent-team-morning.log 2>&1

# 夕方チェックイン（毎夕17:00）
0 17 * * * cd /home/USER/agent-team && /usr/bin/node CDO/outputs/evening_checkin.mjs >> /tmp/agent-team-evening.log 2>&1
```

### 3. 置換が必要な箇所

```
- /usr/bin/node → 実際の node のパス（`which node` で確認）
- /home/USER/agent-team → リポジトリの絶対パス
```

---

# Windows：タスク スケジューラ

### 1. タスク スケジューラを起動
- スタートメニュー → 「タスク スケジューラ」

### 2. 朝会タスクを作成

- 「タスクの作成」をクリック
- 全般タブ：名前「Agent Team 朝会」
- トリガータブ：「毎日」「7:30:00」
- 操作タブ：プログラム/スクリプト「node」、引数「CDO\outputs\morning_meeting.mjs」、開始（オプション）「C:\Users\YOUR_USER\agent-team」

### 3. 夕方チェックインも同様に作成
- 名前「Agent Team 夕会」、時刻「17:00:00」、引数「CDO\outputs\evening_checkin.mjs」

---

# 通知連携（任意・追加費用ゼロ）

朝会レポート生成時に macOS 通知を表示する：

`morning_meeting.mjs` の最後に下記を追加（osascript 経由・無料）：

```javascript
// macOS 通知（既存機能・追加費用ゼロ）
if (process.platform === 'darwin') {
  try {
    sh(`osascript -e 'display notification "今日の朝会レポート生成済み" with title "Agent Team" sound name "Glass"'`);
  } catch {}
}
```

→ 朝7:30 にスクリーンに通知が出る。

---

# トラブルシューティング

## 自動実行されない

1. **node のパスを確認**：`which node` の出力をそのまま使う
2. **絶対パスで指定**：相対パス（`./CDO/...`）は launchd / cron では動かない
3. **PATH 環境変数**：cron は最小 PATH なので、フルパス必須
4. **macOS のセキュリティ**：システム環境設定 → セキュリティとプライバシー → アクセシビリティ で許可

## ログを確認

```bash
# macOS / Linux
tail -f /tmp/agent-team-morning.log
tail -f /tmp/agent-team-evening.err
```

## 手動実行に切り替え

スケジュール自動化が難しい場合、毎日手動で：

```bash
# 朝
node CDO/outputs/morning_meeting.mjs

# 夕方
node CDO/outputs/evening_checkin.mjs
```

→ 慣れたらシェルエイリアスで省略：

```bash
# ~/.zshrc に追記
alias morning='cd ~/agent-team && node CDO/outputs/morning_meeting.mjs'
alias evening='cd ~/agent-team && node CDO/outputs/evening_checkin.mjs'
```

→ ターミナルで `morning` / `evening` だけで実行。

---

# 動作確認チェックリスト

セットアップ完了後、下記を確認：

```
□ morning_meeting.mjs を手動実行 → CDO/research/meetings/YYYY-MM-DD_morning.md が生成される
□ evening_checkin.mjs を手動実行 → CDO/research/checkins/YYYY-MM-DD_evening.md が生成される
□ launchd / cron / タスクスケジューラ に登録した
□ 翌朝 7:30 に自動実行された（log 確認）
□ 翌夕方 17:00 に自動実行された（log 確認）
```

---

# 運用初日の流れ（推奨）

```
Day 1（今日）：
  □ pdca_scheduling_setup.md を読む（5分）
  □ launchd / cron の設定（10分）
  □ 手動で morning_meeting.mjs を1回実行して動作確認

Day 2 朝：
  □ 自動実行されたか確認
  □ 朝会レポートを読んで Top3 を実行

Day 2 夕方：
  □ evening_checkin.mjs が自動実行されたか確認
  □ チェックインに記入（5分）

Week 1 末：
  □ 5日分のスタンドアップ・チェックインを蓄積
  □ 週次レトロ実施（weekly_retrospective.md フォーマット）
```

---

# 費用集計

| 項目 | 金額 |
|------|------|
| launchd / cron / タスクスケジューラ | ¥0（OS 標準機能） |
| Node.js 実行 | ¥0（既にインストール済み） |
| 通知（macOS osascript） | ¥0 |
| ログ保存（/tmp） | ¥0 |
| **追加発生コスト** | **¥0** |
