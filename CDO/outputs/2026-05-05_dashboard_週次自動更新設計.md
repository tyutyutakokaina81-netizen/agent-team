# ダッシュボード 週次自動更新 設計（2026-05-05）

**目的**：`projects/2026-04-08_月30万自動化/dashboard.md` を毎週日曜23:00に自動更新し、月30万達成までの進捗を機械的にトラッキングする。

**実装方針**：費用ゼロ（既存 Python + launchd）／ローカル完結／関連スクリプトは既存の `scripts/status_report.py` を拡張して再利用。

---

## 入力データソース

| データ | 取得元 | 取得方法 |
|-------|-------|---------|
| 応募件数（柱A） | `scripts/applications.csv` | csv モジュールで集計 |
| 応募ステータス | `scripts/applications.csv` の status 列 | 同上 |
| 営業送信件数（柱B） | （新規）`scripts/sales_log.csv` | 手入力 or 専用CLIで追加 |
| テンプレ販売数（柱C） | （新規）CFO の販売台帳CSV | エクスポート手動 |
| 月固定費 | 定数 ¥5,800 | コード内定数 |
| 進行中タスク | 各役職の `_index.md` | grep で「進行中」セクション抽出 |

---

## スクリプト構成

### 新規ファイル：`scripts/update_dashboard.py`

```
責務:
  1. 上記データソースから今週の数字を集計
  2. dashboard.md の該当セクションをin-place更新
  3. 旧バージョンを dashboard.md.bak として保管
  4. 更新ログを logs/dashboard_update.log に追記

入力なし、副作用は dashboard.md の上書きのみ
冪等性: 同じデータで実行すれば結果は同じ
```

### 既存依存

- `scripts/applications.csv`（作成済）
- `scripts/status_report.py`（柱A集計ロジックを流用）
- `scripts/deliver/RULES.md`（鉄則4原則準拠）

### 新規必要

- `scripts/sales_log.csv`（柱B営業送信ログ／空ファイル先行作成）
- `CFO/outputs/_export/sales_data.csv`（CFO台帳の月次エクスポート先）

---

## 自動実行（launchd plist 追加）

ファイル：`~/Library/LaunchAgents/com.agentteam.dashboard.plist`

```xml
<key>Label</key><string>com.agentteam.dashboard</string>
<key>ProgramArguments</key>
  <array>
    <string>/opt/homebrew/bin/python3</string>
    <string>/Users/apple/agent-team/scripts/update_dashboard.py</string>
  </array>
<key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key><integer>0</integer>
    <key>Hour</key><integer>23</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
```

→ 毎週日曜23:00に自動起動

### 教訓の反映（2026-05-04 launchd cleanup より）

- スクリプト本体を削除する場合は plist も同時に削除する
- plist 設置時は `CDO/outputs/2026-05-04_launchd_cleanup_record.md` のフォーマットで台帳に追記する
- `StandardErrorPath` を `logs/dashboard_err.log` に指定し、エラーは別ファイルへ

---

## ダッシュボードの更新範囲

### 自動更新する箇所

```markdown
## 収入進捗（最終更新: 2026-MM-DD HH:MM 自動）

| 柱 | 目標/月 | 今月実績 | 達成率 |  ← この表を自動更新
```

### 自動更新しない箇所（手作業のまま）

- プラットフォーム登録状況（オーナー判断）
- 実行ログ・所感（オーナー記述）
- 戦略レビュー欄

---

## 実装ステップ（合計約60分・別日テーマ）

| Step | 担当 | 所要 | 内容 |
|------|------|------|------|
| 1 | CDO（Claude） | 30分 | `update_dashboard.py` 実装＋ユニットテスト |
| 2 | 藤森さん | 5分 | `~/Library/LaunchAgents/com.agentteam.dashboard.plist` を設置・load |
| 3 | CDO（Claude） | 10分 | 初回実行＋出力検証 |
| 4 | 藤森さん | 5分 | 出力された dashboard.md を目視確認 |
| 5 | CDO（Claude） | 10分 | `_index.md`／`launchd_cleanup_record.md` に追記 |

**注意**：本作業は柱C/A実行と並行して進めない（ルール3「1日1テーマ」）。
柱C初動売上が落ち着いてから別日に着手。

---

## 設計上のリスクと対策

| リスク | 対策 |
|-------|------|
| 旧 launchd ジョブと同様のエラー連鎖 | スクリプト削除時の plist 同時削除を `CDO/outputs/` の運用記録で固定 |
| dashboard.md の手動更新と競合 | バックアップ `dashboard.md.bak` を毎回作成、差分が大きい場合は警告 |
| sales_log.csv のスキーマ不統一 | applications.csv と同じ7列スキーマで統一（date, site, job_name, price, status, url, note） |
| 月跨ぎの集計バグ | dt.date.today().replace(day=1) を月初定数として使用、テストで検証 |

---

## 改訂履歴

| 日付 | 変更 |
|------|------|
| 2026-05-05 | 初版作成（実装は別日テーマ・本日は設計のみ） |
