# ops/auto_company — 完全自動AI会社のレール（CDO管轄）

完全自動AI会社の「3つの口」を、**API従量課金ゼロ・固定費ゼロ**で繋ぐ決定論的スクリプト群。
創作（記事・商品）は既払いのClaude Pro/Codeで行い、ここでは**LLMを一切呼ばない機械作業**だけを自動化する。

設計図の正本: `docs/2026-06-22_完全自動AI会社_設計図.md`

## スクリプト

| ファイル | 工程 | 役割 | 課金 |
|---|---|---|---|
| `guard_checks.py` | 監視 | 重複/未来日付/テスト記事/台帳整合/センシティブを機械検出。重大は exit=2 | ¥0 |
| `revenue_ledger.py` | ⑥MEASURE | `sales.csv` から採算表を自動生成（売上−手数料＝純利益・Phaseゲート判定） | ¥0 |
| `build_gumroad_pack.py` | ④PUBLISH | 商品mdから制作ノートを除去した配布用クリーン版を `ops/outbox/gumroad/` に生成 | ¥0 |

## 使い方

```bash
# 監視（公開前/コミット時の番人）
python3 ops/auto_company/guard_checks.py          # 重大があれば exit=2
python3 ops/auto_company/guard_checks.py --strict # 警告も exit=1 にする

# 採算集計（Gumroad/Stripeの売上CSVを sales.csv に置いてから）
#   sales.csv 形式: date,product,platform,amount_jpy
python3 ops/auto_company/revenue_ledger.py        # → CFO/outputs/採算表_自動生成.md

# 出品パック生成（制作ノート除去・流出防止）
python3 ops/auto_company/build_gumroad_pack.py [商品.md]  # → ops/outbox/gumroad/
```

## 無人運用

- `.github/workflows/auto-company-guardian.yml` が push時＋毎朝7時(JST)に `guard_checks.py` を自動実行（無料枠）。
- note公開の無人化は別レール（`ops/cowork_run.sh` をオーナーMacのcron/launchdで）。認証の都合でMac側でのみ動く（`docs/automation.md`）。

## 人が必ず確認する境界（自動化しない）

- 入金の引き出し・金額の最終確定（金銭）
- ファイル削除・上書き（破壊的操作）
- 商品の最終公開ボタン（外部送信）
