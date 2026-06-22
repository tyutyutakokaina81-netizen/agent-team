#!/usr/bin/env python3
"""
revenue_ledger.py — 収益ループ工程⑥ MEASURE の自動集計（CFO採算表ジェネレータ）

設計思想:
- LLMを呼ばない決定論的集計のみ（API従量課金ゼロ）
- Gumroad/Stripe からCSVエクスポートした売上を読み、手数料・純利益・Phaseゲートを自動判定
- 金額の最終確認・入金引き出しは人が行う（金銭は要確認の原則）

入力 CSV (ops/auto_company/sales.csv) 例:
    date,product,platform,amount_jpy
    2026-06-25,AIプロンプト集先行版,gumroad,980
    2026-06-26,AIプロンプト集先行版,stripe,980

出力: CFO/outputs/採算表_自動生成.md （売上ログ＋月次サマリ＋Phaseゲート判定）
使い方: python3 ops/auto_company/revenue_ledger.py
"""
import os
import csv
import sys
from collections import defaultdict

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SALES_CSV = os.path.join(os.path.dirname(__file__), "sales.csv")
OUT = os.path.join(REPO, "CFO", "outputs", "採算表_自動生成.md")

# 手数料率（採算計算用・2026年初の一般値。確定値は各社規約で更新）
FEE = {"gumroad": 0.10, "stripe": 0.036, "note": 0.20, "manual": 0.0}

# Phaseゲート（月次純利益ベース）
GATES = [
    (0, "Phase 0 着手", 1, "1件売れたらPhase 1解放（本版制作）"),
    (1, "Phase 1", 10000, "月¥10,000でPhase 2解放（教材・定期）"),
    (10000, "Phase 2", 50000, "月¥50,000でPhase 3解放（完全無人化）"),
    (50000, "Phase 3", 150000, "月¥150,000で柱A/B（代行）着手"),
]


def phase_for(net):
    label, nxt = "Phase 0 着手", "1件売れたらPhase 1解放"
    for floor, lbl, gate, nx in GATES:
        if net >= floor:
            label, nxt = lbl, nx
    return label, nxt


def main():
    if not os.path.isfile(SALES_CSV):
        print(f"売上CSVが未配置: {SALES_CSV}")
        print("Gumroad/Stripe から CSV をエクスポートし、date,product,platform,amount_jpy 形式で保存してください。")
        print("まだ売上ゼロなら Phase 0（出品して1件売る）が次の一手です。")
        return 0

    rows = []
    with open(SALES_CSV, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            try:
                amt = int(float(r["amount_jpy"]))
            except (KeyError, ValueError):
                continue
            plat = (r.get("platform") or "manual").strip().lower()
            fee = round(amt * FEE.get(plat, 0.10))
            rows.append({
                "date": r.get("date", "").strip(),
                "product": r.get("product", "").strip(),
                "platform": plat,
                "amount": amt,
                "fee": fee,
                "net": amt - fee,
            })

    monthly = defaultdict(lambda: {"gross": 0, "fee": 0, "net": 0})
    cum = 0
    lines = []
    for r in sorted(rows, key=lambda x: x["date"]):
        cum += r["net"]
        m = r["date"][:7]
        monthly[m]["gross"] += r["amount"]
        monthly[m]["fee"] += r["fee"]
        monthly[m]["net"] += r["net"]
        lines.append(f"| {r['date']} | {r['product']} | {r['platform']} | ¥{r['amount']:,} | ¥{r['fee']:,} | ¥{r['net']:,} | ¥{cum:,} |")

    out = ["# 採算表（自動生成）― revenue_ledger.py 出力",
           "",
           "> `ops/auto_company/sales.csv` から自動集計（LLM不使用・課金ゼロ）。手入力の正本は `2026-06-22_採算表テンプレート.md`。",
           "",
           "## 売上ログ",
           "",
           "| 日付 | 商品 | PF | 売上 | 手数料 | 純利益 | 累計純利益 |",
           "|---|---|---|---|---|---|---|"]
    out += lines or ["| (売上なし) | | | | | | ¥0 |"]
    out += ["", "## 月次サマリ＆Phaseゲート", "",
            "| 月 | 売上 | 手数料 | 純利益 | 現Phase | 次の解放条件 |",
            "|---|---|---|---|---|---|"]
    for m in sorted(monthly):
        s = monthly[m]
        ph, nxt = phase_for(s["net"])
        out.append(f"| {m} | ¥{s['gross']:,} | ¥{s['fee']:,} | ¥{s['net']:,} | {ph} | {nxt} |")
    if not monthly:
        out.append("| (データなし) | ¥0 | ¥0 | ¥0 | Phase 0 着手 | 1件売れたらPhase 1解放 |")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print(f"✅ 採算表を生成: {os.path.relpath(OUT, REPO)}（{len(rows)}件・累計純利益 ¥{cum:,}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
