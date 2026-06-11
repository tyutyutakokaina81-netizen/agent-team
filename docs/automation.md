# 自動化（2026-06-07）

「code↔cowork↔公開」をできる限り自動化する。**完全自動が可能な範囲と、cowork側の一度きり設定**を分けて記す。

## ① 完全自動（code側・人手ゼロ）
- **GitHub Actions `.github/workflows/audit.yml`**：main への push 毎に
  記事カバレッジ監査＋台帳整合チェックを自動実行。台帳未記載があれば失敗で通知。
  → 品質・整合の見張りが無人化。

## ② cowork側の自動化（オーナーのMacで一度だけ設定）
- **`ops/cowork_run.sh`**：main を pull → `drafts/queue/` の記事を
  `publish_to_note.py` で公開 → `drafts/published/` へ → outbox に報告 → push。
- これを cron/launchd で定期実行すれば、**公開が無人化**する。
  例（crontab、毎朝8時）：
  ```
  0 8 * * * cd ~/agent-team && bash ops/cowork_run.sh >> ops/logs/cron.log 2>&1
  ```

## ③ 自動化できない境界（正直に）
- **code から cowork セッションを起こすことは不可**（別環境・直接の通信路なし）。
  →「指示が来たら即」を完全自動にするには、cowork側が GitHub webhook 購読 or 上記 cron を持つ必要がある。
- **note公開の認証**はブラウザセッション必須＝Mac側の `cowork_run.sh`（②）でしか動かない。
- 配信は二段構え：②が動かない時はオーナー手動 `publish_to_note.py`。

## 結論
- 「監査・整合」は①で**完全無人化**。
- 「公開」は②の cron 設定で**ほぼ無人化**（初回設定のみ人手）。
- 残る人手は「cron を一度仕込む」だけ。これで日次運用は回る。
