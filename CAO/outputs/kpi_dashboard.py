#!/usr/bin/env python3
"""
CAO: 月30万自動化 KPIダッシュボード

用途: 全収益チャネルの実績を1か所に入力 → 月収集計 + Week4/Month3 の自動判定。
      推測ではなく「実数」を毎週ここに記録し、Go/No-Go を機械的に下すための土台。

実行:
  python3 kpi_dashboard.py                      # 現在の kpi_data.json を集計・判定
  python3 kpi_dashboard.py --record             # 対話形式で今週の実績を追記
  python3 kpi_dashboard.py --template           # 入力用 kpi_data.json の雛形を出力

設計思想（100点計画 Phase 1-3 と連動）:
  - 初月(Week1-4)の合計推定月収 >= ¥20K → Phase 2A(営業開始)
  - 初月 < ¥20K → Phase 2B(原因分析・代替戦略)
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

DATA_PATH = Path(__file__).parent / "kpi_data.json"

# 各チャネルの「1件あたり月次寄与額」想定（実績が入れば実数で上書きされる）
CHANNELS = {
    "note_membership": {"label": "noteメンバーシップ", "unit_price": 980, "recurring": True},
    "note_paid_article": {"label": "note有料記事(単発)", "unit_price": 500, "recurring": False},
    "solo_ceo_os": {"label": "Solo CEO OS(Gumroad)", "unit_price": 1980, "recurring": False},
    "template_vol2": {"label": "テンプレVol.2", "unit_price": 2980, "recurring": False},
    "seo_writing": {"label": "SEO記事代行", "unit_price": 25000, "recurring": False},
    "sns_management": {"label": "SNS運用代行", "unit_price": 75000, "recurring": True},
    "online_course": {"label": "オンラインコース", "unit_price": 5000, "recurring": False},
    "consulting": {"label": "個別相談", "unit_price": 5000, "recurring": False},
}


def template():
    """入力用の雛形を生成"""
    data = {
        "started_at": datetime.now().strftime("%Y-%m-%d"),
        "weeks": [
            {
                "week": 1,
                "date_range": "2026-06-23〜06-29",
                "channels": {k: {"new_units": 0, "active_units": 0, "actual_revenue": 0}
                             for k in CHANNELS},
                "funnel": {
                    "outreach_sent": 0, "opened": 0, "replied": 0,
                    "meetings": 0, "contracts": 0
                },
                "note": ""
            }
        ]
    }
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 雛形を生成: {DATA_PATH}")
    print("   各週の new_units(新規) / active_units(継続) / actual_revenue(実額) を埋めてください")


def aggregate(data: dict):
    """全週の実績を集計"""
    total_actual = 0
    channel_totals = {k: 0 for k in CHANNELS}
    latest_week = 0
    funnel = {"outreach_sent": 0, "opened": 0, "replied": 0, "meetings": 0, "contracts": 0}

    for w in data.get("weeks", []):
        latest_week = max(latest_week, w.get("week", 0))
        for ch, vals in w.get("channels", {}).items():
            rev = vals.get("actual_revenue", 0)
            channel_totals[ch] += rev
            total_actual += rev
        for fk in funnel:
            funnel[fk] += w.get("funnel", {}).get(fk, 0)

    return total_actual, channel_totals, latest_week, funnel


def monthly_estimate(data: dict):
    """直近週の active_units から月次の継続収益を推定"""
    if not data.get("weeks"):
        return 0
    last = data["weeks"][-1]
    est = 0
    for ch, vals in last.get("channels", {}).items():
        meta = CHANNELS[ch]
        active = vals.get("active_units", 0)
        new = vals.get("new_units", 0)
        if meta["recurring"]:
            est += active * meta["unit_price"]
        else:
            est += new * meta["unit_price"]  # 単発はその月の新規分
    return est


def verdict(total_actual: int, monthly_est: int, latest_week: int, funnel: dict):
    """Go/No-Go 判定（100点計画のロジック）"""
    lines = []
    lines.append("=" * 56)
    lines.append("📊 判定（100点計画 Phase ロジック）")
    lines.append("=" * 56)

    if latest_week < 4:
        lines.append(f"現在 Week {latest_week}：Phase 1（基礎構築中）")
        lines.append(f"  → Week 4 終了時に Go/No-Go 判定を実施")
    else:
        lines.append(f"Week {latest_week}：Phase 1 完了 → 判定実行")
        if monthly_est >= 20000:
            lines.append(f"  ✅ GO：推定月収 ¥{monthly_est:,} ≥ ¥20,000")
            lines.append(f"  → Phase 2A：B2B営業パイロット開始")
        else:
            lines.append(f"  ⚠️  NO-GO：推定月収 ¥{monthly_est:,} < ¥20,000")
            lines.append(f"  → Phase 2B：原因分析 + 代替戦略（コース化/コンサル）")

    # 営業ファネルの健全性（データがあれば）
    if funnel["outreach_sent"] > 0:
        reply_rate = funnel["replied"] / funnel["outreach_sent"] * 100
        lines.append("")
        lines.append(f"営業ファネル: 送信{funnel['outreach_sent']} → 開封{funnel['opened']} "
                     f"→ 返信{funnel['replied']}({reply_rate:.1f}%) "
                     f"→ 商談{funnel['meetings']} → 成約{funnel['contracts']}")
        if reply_rate < 3 and funnel["outreach_sent"] >= 30:
            lines.append("  ⚠️  返信率<3%：メッセージ/ターゲットの見直しを推奨")

    return "\n".join(lines)


def show(data: dict):
    total_actual, channel_totals, latest_week, funnel = aggregate(data)
    monthly_est = monthly_estimate(data)

    print("=" * 56)
    print("📊 月30万自動化 KPIダッシュボード")
    print("=" * 56)
    print(f"開始日: {data.get('started_at', '?')} ／ 記録週数: {len(data.get('weeks', []))}")
    print()
    print("【チャネル別 累計実績】")
    for ch, meta in CHANNELS.items():
        amt = channel_totals[ch]
        bar = "█" * min(int(amt / 5000), 30)
        print(f"  {meta['label']:<22} ¥{amt:>9,} {bar}")
    print("  " + "-" * 44)
    print(f"  {'累計実績合計':<22} ¥{total_actual:>9,}")
    print()
    print(f"【直近週ベースの推定月収】 ¥{monthly_est:,}")
    print(f"  目標¥300,000 に対する達成率: {monthly_est/300000*100:.1f}%")
    print()
    print(verdict(total_actual, monthly_est, latest_week, funnel))


def record(data: dict):
    """対話形式で今週の実績を追記"""
    next_week = (data["weeks"][-1]["week"] + 1) if data.get("weeks") else 1
    print(f"=== Week {next_week} の実績を入力（Enterで0/空）===")
    entry = {"week": next_week,
             "date_range": input("期間(例 2026-06-30〜07-06): ") or "",
             "channels": {}, "funnel": {}, "note": ""}
    for ch, meta in CHANNELS.items():
        print(f"-- {meta['label']} --")
        new_u = input("  新規件数: ") or "0"
        act_u = input("  継続件数(月額系のみ): ") or "0"
        rev = input("  実売上¥: ") or "0"
        entry["channels"][ch] = {
            "new_units": int(new_u), "active_units": int(act_u),
            "actual_revenue": int(rev)
        }
    print("-- 営業ファネル --")
    for fk, label in [("outreach_sent", "営業送信数"), ("opened", "開封数"),
                      ("replied", "返信数"), ("meetings", "商談数"), ("contracts", "成約数")]:
        entry["funnel"][fk] = int(input(f"  {label}: ") or "0")
    entry["note"] = input("メモ: ") or ""

    data.setdefault("weeks", []).append(entry)
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ Week {next_week} を記録しました")


def load():
    if DATA_PATH.exists():
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return {"started_at": datetime.now().strftime("%Y-%m-%d"), "weeks": []}


def main():
    parser = argparse.ArgumentParser(description="KPIダッシュボード")
    parser.add_argument("--template", action="store_true", help="入力雛形を生成")
    parser.add_argument("--record", action="store_true", help="今週の実績を対話入力")
    args = parser.parse_args()

    if args.template:
        template()
        return
    data = load()
    if args.record:
        record(data)
        data = load()
    show(data)


if __name__ == "__main__":
    main()
