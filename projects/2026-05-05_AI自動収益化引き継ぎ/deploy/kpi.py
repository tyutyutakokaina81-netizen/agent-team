"""KPI 集計：published.csv から 7日 / 30日 / 90日の達成状況と Level別売上を表示。

使い方:
    python3 kpi.py
"""
from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path.home() / "ai-auto"
CSV_PATH = BASE / "published.csv"

WINDOWS = {"7日": 7, "30日": 30, "90日": 90}
TARGETS = {
    "note":         {"7日":  7, "30日": 30, "90日": 90},
    "paid_note":    {"7日":  2, "30日": 10, "90日": 30},
    "crowdworks":   {"7日":  7, "30日": 30, "90日": 90},
    "shorts":       {"7日":  3, "30日": 20, "90日": 60},
    "revenue_jpy":  {"7日": 1000, "30日": 30000, "90日": 100000},
}

LEVEL_OF_KIND = {
    "note": "L1",
    "reddit": "L1",
    "shorts": "L1",
    "x": "L1",
    "crowdworks": "L1",  # データ入力主体は L1
    "paid_note": "L2",
    "seo_article": "L2",
    "writer": "L2",
    "ai_support": "L3",
    "consultant": "L3",
    "proposal": "L3",
}


def load() -> list[dict]:
    if not CSV_PATH.exists():
        return []
    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def in_window(rows: list[dict], days: int) -> list[dict]:
    cutoff = datetime.now() - timedelta(days=days)
    return [r for r in rows if datetime.fromisoformat(r["timestamp"]) >= cutoff]


def summarize(rows: list[dict]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    revenue = 0
    for r in rows:
        counts[r["kind"]] += 1
        revenue += int(r.get("revenue_jpy") or 0)
    out = dict(counts)
    out["revenue_jpy"] = revenue
    return out


def level_breakdown(rows: list[dict]) -> dict[str, int]:
    by_level: dict[str, int] = defaultdict(int)
    for r in rows:
        level = LEVEL_OF_KIND.get(r["kind"], "L1")
        by_level[level] += int(r.get("revenue_jpy") or 0)
    return dict(by_level)


def fmt(actual: int, target: int) -> str:
    mark = "OK" if actual >= target else "..."
    return f"{actual:>5} / {target:<5} {mark}"


def main() -> None:
    rows = load()
    if not rows:
        print(f"{CSV_PATH} がありません。published.py で記録してください。")
        return

    print(f"\n=== KPI（{datetime.now():%Y-%m-%d} 時点 / source: {CSV_PATH.name}）===\n")
    print(f"{'指標':<14}" + "".join(f"{w:<18}" for w in WINDOWS))
    summaries = {label: summarize(in_window(rows, days)) for label, days in WINDOWS.items()}
    for kind, targets in TARGETS.items():
        cells = [fmt(summaries[w].get(kind, 0), targets[w]) for w in WINDOWS]
        print(f"{kind:<14}" + "".join(f"{c:<18}" for c in cells))

    print("\n--- Level別売上分解 ---")
    print(f"{'Level':<8}" + "".join(f"{w:<18}" for w in WINDOWS))
    levels = ["L1", "L2", "L3"]
    breakdowns = {label: level_breakdown(in_window(rows, days)) for label, days in WINDOWS.items()}
    for lv in levels:
        cells = [f"¥{breakdowns[w].get(lv, 0):>8,}" for w in WINDOWS]
        print(f"{lv:<8}" + "".join(f"{c:<18}" for c in cells))

    last30_total = sum(breakdowns["30日"].get(lv, 0) for lv in levels)
    if last30_total > 0:
        print("\n--- 30日のLevel構成比 ---")
        for lv in levels:
            v = breakdowns["30日"].get(lv, 0)
            pct = v / last30_total * 100
            bar = "#" * int(pct / 2)
            print(f"  {lv}: {pct:>5.1f}%  {bar}")

    total = sum(int(r.get("revenue_jpy") or 0) for r in rows)
    print(f"\n累計収益: ¥{total:,}（記録件数 {len(rows)} 件）")

    last30 = sum(int(r.get("revenue_jpy") or 0) for r in in_window(rows, 30))
    if last30 > 0:
        l1_pct = breakdowns["30日"].get("L1", 0) / last30 * 100
        l3_pct = breakdowns["30日"].get("L3", 0) / last30 * 100
        if l1_pct > 60:
            print("\nヒント：30日売上の60%超が L1。L2案件（SEO記事執筆）への応募シフトを検討。")
        elif l3_pct > 30:
            print("\nヒント：L3比率が高い。継続契約管理を強化するタイミング。")


if __name__ == "__main__":
    main()
