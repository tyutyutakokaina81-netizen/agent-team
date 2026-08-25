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


def tiers(total, monthly_expense, months_buffer):
    t1 = min(total, monthly_expense * months_buffer)
    rest = total - t1
    t2 = int(rest * 0.3 // UNIT * UNIT)
    t3 = rest - t2
    return t1, t2, t3


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--total", type=int, default=3_000_000, help="運用に回せる総額（既定=モデル値300万円）")
    p.add_argument("--monthly-expense", type=int, default=200_000, help="月間生活費（既定=モデル値20万円）")
    p.add_argument("--months-buffer", type=int, default=6, help="第1層に置く生活費の月数（既定6）")
    p.add_argument("--rates", type=str, default="0.05,0.3,0.6,1.0,1.5", help="仮定する年利（%）のカンマ区切り")
    p.add_argument("--years", type=int, default=5, help="保有年数")
    p.add_argument("--lots", type=int, default=12, help="第3層を何回に分けて買うか（ラダー本数・既定12=毎月）")
    a = p.parse_args()

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
    lot = face // a.lots // UNIT * UNIT
    print()
    print("=" * 64)
    print(f"■ 第3層のラダー（{a.lots}回に分けて毎月購入）")
    print("=" * 64)
    rest_lot = face - lot * a.lots
    print(f"1回あたり購入額 : {yen(lot)} × {a.lots}回 = {yen(lot * a.lots)}")
    if rest_lot:
        print(f"  端数 {yen(rest_lot)} は初回にまとめて上乗せ（初回のみ {yen(lot + rest_lot)}）")
    print(f"  1〜12ヶ月目 : どのロットも中途換金不可（発行後1年ルール）")
    print(f"  13ヶ月目以降: 毎月 {yen(lot)} ずつ「いつでも換金できる資金」に変わる")
    print(f"  → 24ヶ月目には第3層の全額が換金可能な状態になる（利回りは維持したまま）")

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
