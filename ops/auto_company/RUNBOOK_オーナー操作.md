# RUNBOOK ― オーナーのMacで打つコマンド（完全自動AI会社・出荷〜採算）

リポジトリ: `~/agent-team` ／ ブランチ: `claude/agent-capability-review-hqzudr`
私（コンテナ）は外部ネット403で出られないため、外部に触れる手順だけオーナーが実行する。

---

## ① 最新を取得（最初に1回）
```bash
cd ~/agent-team
git fetch origin
git checkout claude/agent-capability-review-hqzudr
git pull origin claude/agent-capability-review-hqzudr
```

## ② 出品ファイルを開く（Gumroadにアップ）
```bash
open ops/outbox/gumroad/
```
アップする2点（制作ノート除去済のクリーン版）:
- `2026-06-22_AIプロンプト集_ひとり会社の実務_先行版.md` … ¥980
- `2026-06-22_AIプロンプト集_飲食店と小さな食ビジネス_先行版.md` … ¥1,280
- バンドル販売: 2点セットで ¥1,980

説明文・タグ・商品名:
- `projects/2026-06-22_有料化ライン構築/CPO/2026-06-22_Gumroad出品キット_先行版.md`
告知文（X 日本語3/英語2・購入後フォロー）:
- `projects/2026-06-22_有料化ライン構築/2026-06-22_先行版ローンチパック.md`

## ③ 出品URL確定 → 全127記事にCTA一括挿入
```bash
python3 ops/auto_company/apply_cta.py --url "https://<GumroadのURL>" --dry-run   # 確認
python3 ops/auto_company/apply_cta.py --url "https://<GumroadのURL>"            # 本実行
git add -A && git commit -m "全note記事にGumroad CTAを挿入" && git push origin claude/agent-capability-review-hqzudr
```

## ④ 売れたら → 採算表を自動更新
```bash
# date,product,platform,amount_jpy（platform=gumroad/stripe/note/manual）
echo "2026-06-25,AIプロンプト集先行版,gumroad,980" >> ops/auto_company/sales.csv
python3 ops/auto_company/revenue_ledger.py
cat CFO/outputs/採算表_自動生成.md
```

## ⑤ 監視（手動でも・Actionsで自動でも）
```bash
python3 ops/auto_company/guard_checks.py            # 重大があればexit=2
python3 ops/auto_company/guard_checks.py --strict   # 警告もexit=1
```

## ⑥ 台帳がズレたら自動修復
```bash
python3 ops/auto_company/sync_ledger.py --dry-run   # 確認
python3 ops/auto_company/sync_ledger.py             # 追記同期
```

---

### 補足
- note公開の無人化は別レール `ops/cowork_run.sh`（認証の都合でMac側のみ）。
- 金銭の引き出し・ファイル削除は自動化しない（人間ゲート）。
- 未解決の人間ゲート案件: 未来日付記事1(6/27)・重複タイトル11 の棚卸し（削除/統合は要確認）。
