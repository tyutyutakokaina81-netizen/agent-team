#!/usr/bin/env python3
"""
agent_cfo.py — CFO（会計・財務）自動実行

毎週実行:
1. 収支サマリーを生成
2. 案件パイプラインから予想入金を試算
3. 財務レポートをCFO/outputs/に出力
"""

import json
from datetime import datetime, date
from pathlib import Path

REPO = Path(__file__).parent
SESSIONS = REPO / ".sessions"
OUTPUT_DIR = REPO / "CFO" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TODAY = date.today().isoformat()
MONTH = datetime.now().strftime("%Y-%m")

REVENUE_FILE = SESSIONS / "revenue_log.json"
PIPELINE_FILE = SESSIONS / "job_pipeline.json"


def load_revenue() -> dict:
    if REVENUE_FILE.exists():
        return json.loads(REVENUE_FILE.read_text())
    return {"records": [], "monthly": {}}


def load_pipeline() -> list:
    if PIPELINE_FILE.exists():
        return json.loads(PIPELINE_FILE.read_text()).get("jobs", [])
    return []


def calc_monthly_summary(revenue: dict) -> dict:
    records = revenue.get("records", [])
    this_month = [r for r in records if r.get("date", "").startswith(MONTH)]
    total_income = sum(r.get("amount", 0) for r in this_month if r.get("type") == "income")
    total_expense = sum(r.get("amount", 0) for r in this_month if r.get("type") == "expense")

    # 固定費（Claude Code¥3,000のみ）
    fixed_cost = 3000
    return {
        "income": total_income,
        "expense": total_expense + fixed_cost,
        "fixed_cost": fixed_cost,
        "net": total_income - total_expense - fixed_cost,
    }


def calc_pipeline_forecast(jobs: list) -> dict:
    """パイプラインから今月の予想入金を試算"""
    forecast = 0
    for job in jobs:
        stage = job.get("stage", "")
        amount = job.get("amount", 0)
        if stage in ["進行中", "納品済み"]:
            forecast += amount
        elif stage == "商談中":
            forecast += amount * 0.5  # 成約率50%で試算
    return {"forecast": int(forecast)}


def generate_report(summary: dict, forecast: dict, jobs: list) -> str:
    lines = [
        f"# CFO 財務レポート {MONTH}",
        f"生成: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "---",
        "",
        "## 今月の収支サマリー",
        f"| 項目 | 金額 |",
        f"|------|------|",
        f"| 収入合計 | ¥{summary['income']:,} |",
        f"| 支出合計 | ¥{summary['expense']:,} |",
        f"  （固定費: Claude Code ¥{summary['fixed_cost']:,}）",
        f"| **手取り** | **¥{summary['net']:,}** |",
        "",
        "## 入金見込み（パイプライン試算）",
        f"- 進行中・納品済み案件: ¥{forecast['forecast']:,}",
        f"- 月末予想入金: ¥{summary['income'] + forecast['forecast']:,}",
        "",
        "## 案件別収入",
        "| 案件 | 金額 | ステージ |",
        "|------|------|---------|",
    ]
    for job in jobs:
        if job.get("amount", 0) > 0:
            lines.append(f"| {job.get('title','－')[:20]} | ¥{job.get('amount',0):,} | {job.get('stage','－')} |")
    if not any(j.get("amount", 0) > 0 for j in jobs):
        lines.append("| （案件なし） | ¥0 | － |")

    lines += [
        "",
        "## 月次目標比較",
        f"| 月 | 目標 | 実績 | 達成率 |",
        f"|----|------|------|--------|",
        f"| {MONTH} | ¥10,000 | ¥{summary['income']:,} | {min(summary['income']//100, 100)}% |",
        "",
        "---",
        "*CFOより: 収入¥0の現状は案件応募・note公開の実行待ちです。CSOとCMOの実行を優先してください。*",
    ]
    return "\n".join(lines)


def run() -> dict:
    print("━" * 45)
    print("  CFO — 財務レポート")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("━" * 45)

    revenue = load_revenue()
    jobs = load_pipeline()
    summary = calc_monthly_summary(revenue)
    forecast = calc_pipeline_forecast(jobs)

    print(f"\n  今月収入: ¥{summary['income']:,}")
    print(f"  今月支出: ¥{summary['expense']:,}")
    print(f"  手取り:   ¥{summary['net']:,}")
    print(f"  入金見込: ¥{forecast['forecast']:,}")

    report = generate_report(summary, forecast, jobs)
    out = OUTPUT_DIR / f"{MONTH}_financial_report.md"
    out.write_text(report, encoding="utf-8")
    print(f"\n  ✅ 財務レポート保存: {out.name}")
    print("━" * 45)

    return {**summary, **forecast}


if __name__ == "__main__":
    run()
