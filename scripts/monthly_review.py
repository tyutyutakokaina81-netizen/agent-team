"""monthly_review.py — 月初に「先月の実績＋今月の優先タスク」を Markdown で自動生成

設計書: CDO/outputs/2026-05-05_完全自動化パイプライン設計.md（B1）

使い方:
  python3 scripts/monthly_review.py            # 先月分のレビューを生成
  python3 scripts/monthly_review.py 2026-04    # 指定月のレビューを生成

出力:
  CDO/outputs/{YYYY-MM}_monthly_review.md
"""
from __future__ import annotations

import csv
import datetime as dt
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
APPLICATIONS_CSV = REPO / "scripts/applications.csv"
SALES_DATA_CSV = REPO / "CFO/outputs/_export/sales_data.csv"
SALES_LOG_CSV = REPO / "scripts/sales_log.csv"
DASHBOARD = REPO / "projects/2026-04-08_月30万自動化/dashboard.md"
OUT_DIR = REPO / "CDO/outputs"

ROLES = ["CDO", "CFO", "CMO", "CPO", "CSO"]


def parse_target_month(arg: str | None) -> tuple[dt.date, dt.date, str]:
    """対象月の開始日・終了日・YYYY-MM 文字列を返す。"""
    today = dt.date.today()
    if arg:
        m = re.match(r"^(\d{4})-(\d{2})$", arg.strip())
        if not m:
            raise ValueError(f"YYYY-MM 形式で指定: {arg}")
        year, month = int(m.group(1)), int(m.group(2))
    else:
        # 先月（today.month - 1）
        first_this = today.replace(day=1)
        last_prev = first_this - dt.timedelta(days=1)
        year, month = last_prev.year, last_prev.month
    start = dt.date(year, month, 1)
    next_month_first = dt.date(year + (month // 12), (month % 12) + 1, 1)
    end = next_month_first - dt.timedelta(days=1)
    return start, end, f"{year:04d}-{month:02d}"


def read_csv_safe(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        with path.open(encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def in_range(date_str: str, start: dt.date, end: dt.date) -> bool:
    try:
        d = dt.date.fromisoformat((date_str or "").strip())
    except ValueError:
        return False
    return start <= d <= end


def aggregate_pillar_a(start: dt.date, end: dt.date) -> dict:
    rows = read_csv_safe(APPLICATIONS_CSV)
    applied = contracted = revenue = 0
    sites = {}
    for r in rows:
        if not in_range(r.get("date", ""), start, end):
            continue
        st = (r.get("status") or "").strip()
        site = (r.get("site") or "?").strip()
        sites[site] = sites.get(site, 0) + 1
        if st == "応募":
            applied += 1
        elif st in ("受注", "契約", "完了"):
            contracted += 1
            try:
                revenue += int((r.get("price") or "0").replace(",", "") or 0)
            except ValueError:
                pass
    return {"applied": applied, "contracted": contracted, "revenue": revenue, "sites": sites}


def aggregate_pillar_c(start: dt.date, end: dt.date) -> dict:
    rows = read_csv_safe(SALES_DATA_CSV)
    count = revenue = 0
    products = {}
    platforms = {}
    for r in rows:
        d_str = (r.get("販売日") or r.get("date", "")).strip()
        if not in_range(d_str, start, end):
            continue
        try:
            price = int((r.get("販売価格") or r.get("price") or "0").replace(",", "").replace("¥", "") or 0)
        except ValueError:
            price = 0
        revenue += price
        count += 1
        prod = (r.get("商品") or r.get("product") or "?").strip()
        plat = (r.get("プラットフォーム") or r.get("platform") or "?").strip()
        products[prod] = products.get(prod, 0) + 1
        platforms[plat] = platforms.get(plat, 0) + 1
    return {"count": count, "revenue": revenue, "products": products, "platforms": platforms}


def gather_progress_tasks() -> dict[str, list[str]]:
    """各役職の _index.md から進行中タスクを抽出。"""
    out = {}
    for role in ROLES:
        idx = REPO / role / "_index.md"
        if not idx.exists():
            out[role] = []
            continue
        text = idx.read_text(encoding="utf-8")
        m = re.search(r"^## 進行中タスク\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
        if m is None:
            out[role] = []
            continue
        tasks = re.findall(r"^- (.+)$", m.group(1), re.MULTILINE)
        out[role] = tasks
    return out


def build_review(target_month: str, start: dt.date, end: dt.date) -> str:
    pa = aggregate_pillar_a(start, end)
    pc = aggregate_pillar_c(start, end)
    progress = gather_progress_tasks()
    total_revenue = pa["revenue"] + pc["revenue"]
    target = 300000

    lines = [
        f"# 月次経営レビュー — {target_month}",
        "",
        f"_自動生成: {dt.datetime.now().strftime('%Y-%m-%d %H:%M')} / 対象期間: {start} 〜 {end}_",
        "",
        "---",
        "",
        "## 1. 実績サマリ",
        "",
        f"- **総売上**: ¥{total_revenue:,} / 目標 ¥{target:,}（達成率 {total_revenue / target * 100:.1f}%）",
        f"- **柱A 売上**: ¥{pa['revenue']:,}（応募 {pa['applied']} 件 / 契約 {pa['contracted']} 件）",
        f"- **柱C 売上**: ¥{pc['revenue']:,}（販売 {pc['count']} 件）",
        f"- **月固定費**: ¥5,800",
        f"- **純利益**: ¥{total_revenue - 5800:,}",
        "",
    ]

    if pa["sites"]:
        lines.append("### 柱A サイト別応募")
        for site, n in sorted(pa["sites"].items(), key=lambda x: -x[1]):
            lines.append(f"- {site}: {n} 件")
        lines.append("")
    if pc["products"]:
        lines.append("### 柱C 商品別販売")
        for prod, n in sorted(pc["products"].items(), key=lambda x: -x[1]):
            lines.append(f"- {prod}: {n} 件")
        lines.append("")
    if pc["platforms"]:
        lines.append("### 柱C プラットフォーム別販売")
        for plat, n in sorted(pc["platforms"].items(), key=lambda x: -x[1]):
            lines.append(f"- {plat}: {n} 件")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## 2. 各役職の進行中タスク（次月持ち越し）",
        "",
    ])
    for role in ROLES:
        tasks = progress.get(role, [])
        lines.append(f"### {role}")
        if not tasks:
            lines.append("- （進行中タスクなし）")
        else:
            for t in tasks:
                lines.append(f"- {t}")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## 3. 自動評価コメント",
        "",
    ])
    if total_revenue == 0:
        lines.append("- 売上発生なし。柱A/B/C いずれも初契約・初販売を最優先テーマとする。")
    elif total_revenue < target * 0.1:
        lines.append("- 初動段階。施策を増やすより「成功した1件」を分析して横展開する。")
    elif total_revenue < target * 0.5:
        lines.append("- 成長軌道に乗りつつあり。リピート率と単価上げの両軸を検討。")
    elif total_revenue < target:
        lines.append("- 目標まで残り少ない。固定費プラスαで黒字化が見えている。")
    else:
        lines.append("- 月次目標達成。次月は単価上げ・新柱の検討を推奨。")
    if pa["applied"] > 0 and pa["contracted"] == 0:
        lines.append("- 柱A：応募はあるが契約ゼロ → 応募文・プロフィール・サンプル記事の見直しを優先。")
    if pc["count"] == 0 and (REPO / "projects/2026-04-08_月30万自動化/C_テンプレ販売/Vol2_SNS投稿カレンダー.xlsx").exists():
        lines.append("- 柱C：実体（.xlsx）は完成済 → note/BOOTH の登録未完了が販売ゼロのボトルネック。")

    lines.extend([
        "",
        "---",
        "",
        "## 4. 次月の優先タスク（推奨）",
        "",
        "1. ボトルネック解消（上記コメント参照）",
        "2. 進行中タスクのうちオーナー作業（最終アップ承認のみ）を優先消化",
        "3. 別日テーマのうち最大ROI項目を1日1テーマで実装",
        "",
        "---",
        "",
        f"_次回実行: 翌月初に `python3 scripts/monthly_review.py` で再生成_",
    ])
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    arg = argv[1] if len(argv) >= 2 else None
    try:
        start, end, label = parse_target_month(arg)
    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 2

    review = build_review(label, start, end)
    out_path = OUT_DIR / f"{label}_monthly_review.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(review, encoding="utf-8")

    print(f"✅ 生成: {out_path}")
    print(f"   対象期間: {start} 〜 {end}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
