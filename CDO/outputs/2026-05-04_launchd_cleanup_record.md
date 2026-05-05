# launchd クリーンアップ記録（2026-05-04）

## 目的

`~/Library/LaunchAgents/` に残っていた agentteam 系の launchd ジョブ3件が、
スクリプト本体不在のまま空回りしていた状態を解消する。

## 【事実】停止前の状態

| Label | plist | 呼出スクリプト | スケジュール | 状態 |
|-------|-------|---------------|------------|------|
| com.agentteam.sales | com.agentteam.sales.plist | `~/agent-team/mac_check_sales.py` | 30分ごと + RunAtLoad | スクリプト不在で失敗継続 |
| com.agentteam.booth | com.agentteam.booth.plist | `~/agent-team/mac_auto_cookie.py` | 日曜22:00 + RunAtLoad | スクリプト不在で失敗継続 |
| com.agentteam.report | com.agentteam.report.plist | `~/agent-team/mac_daily_report.py` | 毎日08:00 | スクリプト不在で失敗継続 |

### 影響

- `logs/sales_err.log` が 121KB / 537行（全て同一エラー "No such file or directory"）まで肥大化
- `logs/booth_err.log` 約2KB、`logs/report_err.log` 約3KB に同種エラーが蓄積
- 30分ごとに `You have new mail.` がローカルメール spool に蓄積
- 売上監視機能は 5/1 13:55 を最後に実質停止 → 4日間機能していなかった

### 推測される原因

- スクリプト本体（mac_check_sales.py / mac_auto_cookie.py / mac_daily_report.py）を
  リポジトリ整理時に削除した際、launchd plist の方を残してしまった
- リポジトリ内に当該スクリプトを参照するコードは現存しない（grep で 0 件）

## 【実施】停止手順

```bash
# 1. unload（即時停止）
launchctl unload ~/Library/LaunchAgents/com.agentteam.sales.plist
launchctl unload ~/Library/LaunchAgents/com.agentteam.booth.plist
launchctl unload ~/Library/LaunchAgents/com.agentteam.report.plist

# 2. .disabled リネーム（再起動後の自動復活を防止・可逆）
mv ~/Library/LaunchAgents/com.agentteam.sales.plist  ~/Library/LaunchAgents/com.agentteam.sales.plist.disabled
mv ~/Library/LaunchAgents/com.agentteam.booth.plist  ~/Library/LaunchAgents/com.agentteam.booth.plist.disabled
mv ~/Library/LaunchAgents/com.agentteam.report.plist ~/Library/LaunchAgents/com.agentteam.report.plist.disabled

# 3. 確認
launchctl list | grep agentteam   # 出力が空ならOK
```

## 【検証済み】停止後の状態

- `launchctl list | grep agentteam` 出力ゼロ
- `sales_err.log` の追記停止（最終追記: 2026-05-04 20:59）
- 全3つの plist が `.disabled` 拡張子付きで `~/Library/LaunchAgents/` に保管

## 【可逆】復元手順（必要になった場合）

スクリプト本体を再作成した上で、以下のコマンドで復活可能：

```bash
# 1. .disabled を外す
mv ~/Library/LaunchAgents/com.agentteam.sales.plist.disabled  ~/Library/LaunchAgents/com.agentteam.sales.plist

# 2. load（即起動）
launchctl load ~/Library/LaunchAgents/com.agentteam.sales.plist
```

## 【判断】各機能の復活優先度

| 機能 | 優先度 | 理由 |
|------|-------|------|
| sales（30分ごと売上チェック） | 低 | 現在の販売規模（ほぼ¥0）では手動チェックで十分 |
| report（毎日朝レポート） | 中 | 行動ルーティンの一部だが、`scripts/status_report.py` で代替可能 |
| booth（日曜のCookie更新） | 低 | BOOTH購入が発生してから検討で十分 |

復活が必要になった場合、**ルールv1「1日1テーマ」厳守** で別日に新規実装。
旧スクリプトは存在しないため、`scripts/deliver/RULES.md` の鉄則4原則
（安全第一・冪等性・透明性・下位互換）に沿って一から設計する。

## 関連ファイル

- 本日同時対応: `apply.py` の通知機能（38-52行目 `notify()`）動作確認済
- `scripts/status_report.py` が日次レポートの代替として既に存在

## 改訂履歴

| 日付 | 変更 |
|------|------|
| 2026-05-04 | 初版作成（launchd 3件の停止記録） |
