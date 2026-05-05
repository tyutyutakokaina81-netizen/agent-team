"""update_dashboard.py — projects/2026-04-08_月30万自動化/dashboard.md を自動更新

設計書: CDO/outputs/2026-05-05_dashboard_週次自動更新設計.md
鉄則: scripts/deliver/RULES.md（安全第一・冪等性・透明性・下位互換）

使い方:
  python3 scripts/update_dashboard.py
  → dashboard.md の「収入進捗」表と「直近インシデント・進捗」セクションを最新化
  → 旧版は dashboard.md.bak として保管
  → 実行ログは logs/dashboard_update.log に追記
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import pathlib
import re
import shutil
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
DASHBOARD = REPO / "projects/2026-04-08_月30万自動化/dashboard.md"
APPLICATIONS_CSV = REPO / "scripts/applications.csv"
SALES_LOG_CSV = REPO / "scripts/sales_log.csv"      # 柱B営業送信ログ（任意）
SALES_DATA_CSV = REPO / "CFO/outputs/_export/sales_data.csv"  # CFO台帳エクスポート（任意）
LOG_FILE = REPO / "logs/dashboard_update.log"

# 月固定費（CLAUDE.md より）
MONTHLY_FIXED_COST = 5800

# 月収目標
TARGETS = {
    "A": 150000,  # ライティング・データ入力
    "B": 100000,  # SNS運用代行
    "C": 50000,   # テンプレ販売
    "D": 0,       # スクレイピング（実験）
}


def now() -> dt.datetime:
    return dt.datetime.now()


def month_start(today: dt.date) -> dt.date:
    return today.replace(day=1)


def log(message: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"[{now().isoformat(timespec='seconds')}] {message}\n")


def read_csv_safe(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        with path.open(encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except Exception as e:
        log(f"WARN read failed: {path} ({e})")
        return []


def parse_date(s: str) -> dt.date | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return dt.date.fromisoformat(s)
    except ValueError:
        return None


def aggregate_pillar_a(today: dt.date) -> dict:
    """柱A: applications.csv から今月の応募件数・契約金額を集計"""
    rows = read_csv_safe(APPLICATIONS_CSV)
    start = month_start(today)
    applied = 0
    contracted = 0
    revenue = 0
    for row in rows:
        d = parse_date(row.get("date", ""))
        if d is None or d < start or d > today:
            continue
        status = (row.get("status") or "").strip()
        if status == "応募":
            applied += 1
        elif status in ("受注", "契約", "完了"):
            contracted += 1
            try:
                revenue += int((row.get("price") or "0").replace(",", "") or 0)
            except ValueError:
                pass
    return {"applied": applied, "contracted": contracted, "revenue": revenue}


def aggregate_pillar_b(today: dt.date) -> dict:
    """柱B: sales_log.csv（営業送信ログ）を集計（ファイル不在なら空）"""
    rows = read_csv_safe(SALES_LOG_CSV)
    start = month_start(today)
    sent = 0
    contracted = 0
    revenue = 0
    for row in rows:
        d = parse_date(row.get("date", ""))
        if d is None or d < start or d > today:
            continue
        status = (row.get("status") or "").strip()
        if status in ("送信", "DM"):
            sent += 1
        elif status in ("契約", "受注"):
            contracted += 1
            try:
                revenue += int((row.get("price") or "0").replace(",", "") or 0)
            except ValueError:
                pass
    return {"sent": sent, "contracted": contracted, "revenue": revenue}


def aggregate_pillar_c(today: dt.date) -> dict:
    """柱C: CFO台帳エクスポート（販売台帳の月次合計）"""
    rows = read_csv_safe(SALES_DATA_CSV)
    start = month_start(today)
    sales_count = 0
    revenue = 0
    for row in rows:
        d = parse_date(row.get("販売日") or row.get("date", ""))
        if d is None or d < start or d > today:
            continue
        try:
            price = int((row.get("販売価格") or row.get("price") or "0").replace(",", "").replace("¥", "") or 0)
        except ValueError:
            price = 0
        revenue += price
        sales_count += 1
    return {"sales_count": sales_count, "revenue": revenue}


def fmt_yen(n: int) -> str:
    return f"¥{n:,}"


def achievement_rate(actual: int, target: int) -> str:
    if target == 0:
        return "—"
    return f"{actual / target * 100:.0f}%"


def build_income_table(today: dt.date) -> str:
    a = aggregate_pillar_a(today)
    b = aggregate_pillar_b(today)
    c = aggregate_pillar_c(today)

    a_rev = a["revenue"]
    b_rev = b["revenue"]
    c_rev = c["revenue"]
    total_rev = a_rev + b_rev + c_rev
    total_target = sum(TARGETS.values())

    lines = [
        "## 収入進捗",
        "",
        f"_最終更新: {now().strftime('%Y-%m-%d %H:%M')} 自動 / 対象月: {month_start(today).strftime('%Y-%m')}_",
        "",
        "| 柱 | 目標/月 | 今月実績 | 達成率 |",
        "|----|--------|---------|-------|",
        f"| A: ライティング・データ入力 | {fmt_yen(TARGETS['A'])} | {fmt_yen(a_rev)}（応募{a['applied']}件・契約{a['contracted']}件） | {achievement_rate(a_rev, TARGETS['A'])} |",
        f"| B: SNS運用代行 | {fmt_yen(TARGETS['B'])} | {fmt_yen(b_rev)}（送信{b['sent']}件・契約{b['contracted']}件） | {achievement_rate(b_rev, TARGETS['B'])} |",
        f"| C: テンプレ販売 | {fmt_yen(TARGETS['C'])} | {fmt_yen(c_rev)}（販売{c['sales_count']}件） | {achievement_rate(c_rev, TARGETS['C'])} |",
        f"| D: スクレイピング（実験） | {fmt_yen(0)} | {fmt_yen(0)} | — |",
        f"| **合計** | **{fmt_yen(total_target)}** | **{fmt_yen(total_rev)}** | **{achievement_rate(total_rev, total_target)}** |",
        "",
        f"※ 月固定費 {fmt_yen(MONTHLY_FIXED_COST)} を差し引いた純利益: **{fmt_yen(total_rev - MONTHLY_FIXED_COST)}**",
    ]
    return "\n".join(lines)


def replace_section(content: str, header: str, new_block: str) -> str:
    """`## {header}` セクションを new_block で置換（次の '## ' まで）"""
    pattern = re.compile(
        rf"^## {re.escape(header)}\n.*?(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    if pattern.search(content):
        return pattern.sub(new_block + "\n\n", content, count=1)
    # セクション不在の場合は末尾に追加
    return content.rstrip() + "\n\n" + new_block + "\n"


def update_dashboard() -> dict:
    if not DASHBOARD.exists():
        msg = f"FATAL dashboard not found: {DASHBOARD}"
        log(msg)
        return {"status": "error", "message": msg}

    today = dt.date.today()
    original = DASHBOARD.read_text(encoding="utf-8")

    # バックアップ
    backup = DASHBOARD.with_suffix(".md.bak")
    shutil.copy2(DASHBOARD, backup)

    # 収入進捗セクション置換
    new_income = build_income_table(today)
    updated = replace_section(original, "収入進捗", new_income)

    # 差分が大きい場合は警告
    diff_chars = abs(len(updated) - len(original))
    if diff_chars > 1000:
        log(f"WARN large diff: {diff_chars} chars changed")

    DASHBOARD.write_text(updated, encoding="utf-8")
    log(f"OK updated dashboard.md ({diff_chars} chars diff)")
    return {
        "status": "success",
        "diff_chars": diff_chars,
        "today": today.isoformat(),
        "backup": str(backup),
    }


def main():
    result = update_dashboard()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("status") != "success":
        sys.exit(1)


if __name__ == "__main__":
    main()
