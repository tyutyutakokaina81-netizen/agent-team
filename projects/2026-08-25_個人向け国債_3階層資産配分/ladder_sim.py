#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""個人向け国債・3階層資産配分シミュレータ（依存ゼロ / ネット不要 / 実額はgitに残さない）

使い方（オーナーのMacでローカル実行。引数に実額を渡してもファイルには書き出さない）:
    python3 ladder_sim.py
    python3 ladder_sim.py --total 5000000 --monthly-expense 250000 --months-buffer 6
    python3 ladder_sim.py --rates 0.05,0.3,0.6,1.0,1.5 --years 5

注意: 適用金利は毎月変わる。--rates は「もしこの金利ならいくらか」を見るための仮定値であり、
      実際の値は必ず財務省「個人向け国債」ページの当月回号で確認すること。
"""
import argparse

TAX_KEEP = 0.79685          # 20.315%源泉徴収後に手元に残る割合
MIN_RATE = 0.05             # 最低金利保証（年 %）
UNIT = 10000                # 購入単位（額面1万円）


def yen(n):
    return f"{int(n):,}円"


def after_tax_coupon(face, annual_rate_pct):
    """半年分の税引後利子（円未満切り捨て）"""
    gross = face * (annual_rate_pct / 100) / 2
    return int(gross * TAX_KEEP)


def ladder(face, lots):
    """額面を lots 回に分ける。1万円単位に収めるため、端数は先頭から1万円ずつ配る。
    戻り値: (基準ロット, 1万円上乗せするロット数)"""
    base = face // lots // UNIT * UNIT
    k = (face - base * lots) // UNIT
    return base, k


def ladder_text(face, lots, fmt):
    base, k = ladder(face, lots)
    if k == 0:
        return f"{fmt(base)} × {lots}回"
    return f"{fmt(base + UNIT)} × {k}回 ＋ {fmt(base)} × {lots - k}回"


def tiers(total, monthly_expense, months_buffer):
    t1 = min(total, monthly_expense * months_buffer)
    rest = total - t1
    t2 = int(rest * 0.3 // UNIT * UNIT)
    t3 = rest - t2
    return t1, t2, t3


# ============================================================
# 自動計算モード（--auto）: 実額を渡さなくても、早見表を全パターン計算して出力する
# ============================================================

MAN = 10_000  # 万円

EXPENSES = [100_000, 120_000, 150_000, 180_000, 200_000, 250_000, 300_000]
BUFFER_MONTHS = [3, 6, 12]
REMAINS = [500_000, 1_000_000, 1_500_000, 2_000_000, 2_500_000,
           3_000_000, 4_000_000, 5_000_000, 7_000_000, 10_000_000]
T3S = [350_000, 700_000, 1_050_000, 1_400_000, 1_750_000, 2_100_000,
       2_800_000, 3_500_000, 4_900_000, 7_000_000]
AUTO_RATES = [0.05, 0.30, 0.60, 1.00, 1.50]


def man(n):
    """円を「◯万円」表記に（1万円未満は円で併記）"""
    if n % MAN == 0:
        return f"{n // MAN:,}万円"
    return f"{n / MAN:,.1f}万円"


def split_remain(remain, lots=12):
    t2 = int(remain * 0.3 // UNIT * UNIT)
    t3 = remain - t2
    face = t3 // UNIT * UNIT
    return t2, t3, face


def auto_report(lots=12, years=5):
    out = []
    w = out.append
    w("# 自動計算結果（早見表）")
    w("")
    w("> **このファイルは `ladder_sim.py --auto` が生成したものです。手で書いていません。**")
    w("> 再生成: `python3 ladder_sim.py --auto > 自動計算結果.md`")
    w(">")
    w("> オーナーの実額はここに書かれていません。**下の3つの表から自分の行を読むだけ**で配分と利子が分かります。")
    w("> 金利は仮定値（当月の実数は財務省「個人向け国債」ページで確認）。金額はすべて**税引後**（20.315%控除後）。")
    w("")

    # 表1
    w("## 表1. 第1層＝生活防衛資金（普通預金に置く額）")
    w("")
    w("**月間生活費 × 何ヶ月分**。収入が安定＝3〜6ヶ月、自営・フリーランス＝6〜12ヶ月。")
    w("")
    w("| 月間生活費 | 3ヶ月分 | 6ヶ月分 | 12ヶ月分 |")
    w("|---|---|---|---|")
    for e in EXPENSES:
        cells = " | ".join(man(e * m) for m in BUFFER_MONTHS)
        w(f"| {man(e)} | {cells} |")
    w("")
    w("**総額 − 第1層 ＝ 残額**。この残額を表2で引く。")
    w("")

    # 表2
    w("## 表2. 残額の分け方（第2層3割 / 第3層7割）と12ヶ月ラダー")
    w("")
    w(f"| 残額 | 第2層（1年以内・預金） | 第3層（国債） | 毎月いくら買うか（{lots}ヶ月で買い切る） |")
    w("|---|---|---|---|")
    for r in REMAINS:
        t2, t3, face = split_remain(r, lots)
        w(f"| {man(r)} | {man(t2)} | {man(t3)} | {ladder_text(face, lots, man)} |")
    w("")
    w("- 端数は「先頭の数ヶ月だけ1万円多く買う」形で吸収する（国債は1万円単位のため）。")
    w("- 1〜12ヶ月目：第3層は全額ロック（発行後1年は中途換金不可）。**第1層＋第2層だけで回す期間**。")
    w("- 13ヶ月目以降：毎月1ロットずつ解禁され、いつでも換金できる資金に変わる（買った順に1年後）。")
    w("- 24ヶ月目：第3層の全額が解禁済み＝**利息は国債水準のまま、流動性は預金並み**。")
    w("")

    # 表3
    w("## 表3. 第3層が生む利子（税引後・年間 / " + str(years) + "年累計）")
    w("")
    w("金利がその水準で続いたと仮定した単純計算（複利なし＝利子は半年ごとに入金される）。")
    w("")
    head = " | ".join(f"年{r:.2f}%" for r in AUTO_RATES)
    w(f"| 第3層の額 | {head} |")
    w("|---|" + "---|" * len(AUTO_RATES))
    for t3 in T3S:
        face = t3 // UNIT * UNIT
        cells = []
        for r in AUTO_RATES:
            half = after_tax_coupon(face, max(r, MIN_RATE))
            cells.append(f"{half*2:,} / {half*2*years:,}")
        w(f"| {man(t3)} | " + " | ".join(cells) + " |")
    w("")
    w("※セルは「**年間 / " + str(years) + "年累計**」（円・税引後）。年0.05%は最低金利保証＝この行より下はない。")
    w("※変動10年の金利＝基準金利×0.66。10年国債の実勢が1.5%なら適用金利は約0.99%（＝年1.00%の列が目安）。")
    w("")

    # 表4
    w("## 表4. 中途換金したら引かれる額")
    w("")
    w("中途換金調整額 ＝ 直前2回分の各利子（税引前）× 0.79685 ＝ **表3の「年間」の値とほぼ同額**。")
    w("別表は不要で、**表3の年間の数字がそのまま「1年経過直後に換金したときに消える儲け」**になる。")
    w("")
    w("| 換金した時期 | 手元に残る利子 | 元本 |")
    w("|---|---|---|")
    w("| 1年経過直後 | **0円**（受け取った分をそのまま返す） | 満額 |")
    w("| 1年6ヶ月後 | 表3の年間 × 0.5 | 満額 |")
    w("| 2年後 | 表3の年間 × 1.0 | 満額 |")
    w("| 3年後 | 表3の年間 × 2.0 | 満額 |")
    w("| 5年後 | 表3の年間 × 4.0 | 満額 |")
    w("")
    w("**＝最悪でも「儲けが0」で、元本は減らない。** 損失が出る換金タイミングは存在しない（名目ベース）。")
    w("")

    # 使い方
    w("## 使い方（3ステップ）")
    w("")
    w("1. **表1** で月間生活費の行を見て、第1層に置く額を決める。")
    w("2. **総額 − 第1層 = 残額** を計算し、**表2** で近い行を見て第2層／第3層／毎月の購入額を読む。")
    w("3. **表3** で第3層の額の行を見て、年間いくらの利子になるか確認する。")
    w("")
    w("表にない金額なら、実額を渡して直接計算する（結果は画面に出るだけでファイルに残らない）:")
    w("")
    w("```bash")
    w("python3 ladder_sim.py --total <総額> --monthly-expense <月間生活費> --months-buffer 6")
    w("```")
    return "\n".join(out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--total", type=int, default=3_000_000, help="運用に回せる総額（既定=モデル値300万円）")
    p.add_argument("--monthly-expense", type=int, default=200_000, help="月間生活費（既定=モデル値20万円）")
    p.add_argument("--months-buffer", type=int, default=6, help="第1層に置く生活費の月数（既定6）")
    p.add_argument("--rates", type=str, default="0.05,0.3,0.6,1.0,1.5", help="仮定する年利（%）のカンマ区切り")
    p.add_argument("--years", type=int, default=5, help="保有年数")
    p.add_argument("--lots", type=int, default=12, help="第3層を何回に分けて買うか（ラダー本数・既定12=毎月）")
    p.add_argument("--auto", action="store_true",
                   help="実額を渡さずに早見表を全パターン自動計算し、Markdownで出力する")
    a = p.parse_args()

    if a.auto:
        print(auto_report(lots=a.lots, years=a.years))
        return

    t1, t2, t3 = tiers(a.total, a.monthly_expense, a.months_buffer)
    rates = [float(x) for x in a.rates.split(",")]

    print("=" * 64)
    print("■ 3階層の配分")
    print("=" * 64)
    print(f"総額                       : {yen(a.total)}")
    print(f"第1層 即時換金（普通預金） : {yen(t1)}  ← 生活費{a.months_buffer}ヶ月分")
    print(f"第2層 1年以内（定期/待機） : {yen(t2)}")
    print(f"第3層 3〜5年（個人向け国債）: {yen(t3)}")
    if t3 % UNIT:
        print(f"  ※国債は1万円単位。第3層は {yen(t3 // UNIT * UNIT)} まで購入可（端数 {yen(t3 % UNIT)} は第2層へ）")

    face = t3 // UNIT * UNIT
    base, k = ladder(face, a.lots)
    print()
    print("=" * 64)
    print(f"■ 第3層のラダー（{a.lots}回に分けて毎月購入）")
    print("=" * 64)
    print(f"毎月の購入額 : {ladder_text(face, a.lots, yen)} ＝ 合計 {yen(face)}")
    print(f"  1〜{a.lots}ヶ月目 : どのロットも中途換金不可（発行後1年ルール）")
    print(f"  {a.lots+1}ヶ月目以降: 毎月1ロットずつ「いつでも換金できる資金」に変わる")
    print(f"  → {a.lots*2}ヶ月目には第3層の全額が換金可能な状態になる（利回りは維持したまま）")

    print()
    print("=" * 64)
    print(f"■ 第3層 {yen(t3 // UNIT * UNIT)} の税引後利子（金利が{a.years}年間一定と仮定した単純計算）")
    print("=" * 64)
    print(f"{'年利':>7} | {'半年ごと':>11} | {'年間':>11} | {a.years}年累計")
    print("-" * 60)
    for r in rates:
        r = max(r, MIN_RATE)
        half = after_tax_coupon(face, r)
        print(f"{r:>6.2f}% | {yen(half):>11} | {yen(half*2):>11} | {yen(half*2*a.years)}")
    print(f"※年{MIN_RATE}%は最低金利保証。実際の変動10年は半年ごとに金利が変わるため、上表は「その水準が続いたら」の目安。")

    print()
    print("=" * 64)
    print("■ 中途換金したときに引かれる額（中途換金調整額）")
    print("=" * 64)
    print("計算式: 直前2回分の各利子（税引前）相当額 × 0.79685 ＝ 直近1年分の税引後利子とほぼ同額")
    print("元本（額面）は満額戻る＝名目の元本割れなし。")
    print()
    for r in rates:
        r = max(r, MIN_RATE)
        half = after_tax_coupon(face, r)
        print(f"  年{r:>5.2f}% : 差引額 約{yen(half*2):>11}"
              f" / 1年で換金→実質0円、1.5年→約{yen(half)}、2年→約{yen(half*2)} が手元に残る")


if __name__ == "__main__":
    main()
