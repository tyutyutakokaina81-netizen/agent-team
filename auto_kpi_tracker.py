#!/usr/bin/env python3
"""
auto_kpi_tracker.py — 無料KPI計測（YouTube/note/X）

Playwright でアナリティクスページを読み取り、KPI履歴をJSONに保存。
外部API不要・無料・完全自動。

毎夕20時のrun_daily_auto.shから実行される。
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).parent
SESSIONS = REPO / ".sessions"
SESSIONS.mkdir(exist_ok=True)
KPI_FILE = SESSIONS / "kpi_history.json"
KPI_REPORT = REPO / "CMO" / "outputs" / f"kpi_report_{datetime.now().strftime('%Y-%m')}.md"

TARGET_DATE = datetime.now().strftime("%Y-%m-%d")


# ─── データ構造 ──────────────────────────────────────────────

def load_kpi() -> dict:
    if KPI_FILE.exists():
        return json.loads(KPI_FILE.read_text())
    return {"history": [], "monthly_best": {}}


def save_kpi(data: dict):
    KPI_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


# ─── YouTube Studio スクレイピング ─────────────────────────────

def fetch_youtube_kpi(browser_ctx) -> dict:
    """YouTube Studio アナリティクスから登録者・再生数を取得"""
    kpi = {"subscribers": 0, "views_28d": 0, "shorts_views": 0}
    try:
        page = browser_ctx.new_page()
        page.goto("https://studio.youtube.com/channel/UC/analytics/tab-overview/period-default",
                  wait_until="networkidle", timeout=30000)

        # 登録者数
        sub_el = page.query_selector('[aria-label*="subscribers"], [data-metric="subscribersNet"]')
        if sub_el:
            txt = sub_el.inner_text().strip().replace(",", "").replace("K", "000")
            kpi["subscribers"] = int(re.sub(r"[^\d]", "", txt) or 0)

        # 総再生数（28日）
        view_el = page.query_selector('[data-metric="views"]')
        if view_el:
            txt = view_el.inner_text().strip().replace(",", "")
            kpi["views_28d"] = int(re.sub(r"[^\d]", "", txt) or 0)

        page.close()
        print(f"  YouTube: 登録者={kpi['subscribers']}, 28日再生={kpi['views_28d']}")
    except Exception as e:
        print(f"  YouTube KPI取得失敗: {e}")
    return kpi


def fetch_note_kpi(browser_ctx) -> dict:
    """note アナリティクスから PV・売上件数を取得"""
    kpi = {"pv": 0, "paid_count": 0, "followers": 0}
    try:
        page = browser_ctx.new_page()
        page.goto("https://note.com/dashboard/stats", wait_until="networkidle", timeout=30000)

        # PV数
        pv_el = page.query_selector('[class*="stats"] [class*="count"], [data-testid*="pv"]')
        if pv_el:
            txt = pv_el.inner_text().strip().replace(",", "")
            kpi["pv"] = int(re.sub(r"[^\d]", "", txt) or 0)

        # フォロワー
        page.goto("https://note.com/dashboard", wait_until="networkidle", timeout=20000)
        fol_el = page.query_selector('[class*="follower"], [class*="count"]')
        if fol_el:
            kpi["followers"] = int(re.sub(r"[^\d]", "", fol_el.inner_text()) or 0)

        page.close()
        print(f"  note: PV={kpi['pv']}, フォロワー={kpi['followers']}")
    except Exception as e:
        print(f"  note KPI取得失敗: {e}")
    return kpi


def fetch_x_kpi(browser_ctx) -> dict:
    """X(Twitter) アナリティクスからインプレッション・フォロワーを取得"""
    kpi = {"followers": 0, "impressions_30d": 0}
    try:
        page = browser_ctx.new_page()
        page.goto("https://analytics.twitter.com/user/home", wait_until="networkidle", timeout=30000)

        # 28日インプレッション
        imp_el = page.query_selector('[data-metric-type="impressions"] .metric-value')
        if imp_el:
            txt = imp_el.inner_text().replace(",", "")
            kpi["impressions_30d"] = int(re.sub(r"[^\d]", "", txt) or 0)

        # プロフィールのフォロワー数
        page.goto("https://x.com/home", wait_until="networkidle", timeout=20000)
        fol_el = page.query_selector('[href$="/followers"] span')
        if fol_el:
            kpi["followers"] = int(re.sub(r"[^\d]", "", fol_el.inner_text()) or 0)

        page.close()
        print(f"  X: フォロワー={kpi['followers']}, 30日IMP={kpi['impressions_30d']}")
    except Exception as e:
        print(f"  X KPI取得失敗: {e}")
    return kpi


# ─── ブラウザCookie取得 ───────────────────────────────────────

def load_cookies_for(domain: str) -> list:
    try:
        import browser_cookie3
        jar = browser_cookie3.chrome(domain_name=domain)
        return [{"name": c.name, "value": c.value, "domain": c.domain,
                 "path": c.path, "secure": c.secure} for c in jar]
    except Exception:
        return []


def build_context(playwright, domain: str):
    browser = playwright.chromium.launch(headless=True)
    ctx = browser.new_context()
    cookies = load_cookies_for(domain)
    if cookies:
        ctx.add_cookies(cookies)
    return browser, ctx


# ─── KPIスコア計算 ───────────────────────────────────────────

TARGET_M1 = {
    "x_followers": 100, "note_pv": 500, "yt_subscribers": 50,
    "shorts_views": 1000, "note_paid_count": 5,
}
TARGET_M2 = {
    "x_followers": 300, "note_pv": 2000, "yt_subscribers": 200,
    "shorts_views": 10000, "note_paid_count": 30,
}


def calculate_score(today: dict) -> dict:
    """KPI達成率スコア（0-100）"""
    scores = {}
    mapping = [
        ("x_followers", "x", "followers"),
        ("note_pv", "note", "pv"),
        ("yt_subscribers", "youtube", "subscribers"),
    ]
    for key, src, field in mapping:
        actual = today.get(src, {}).get(field, 0)
        target = TARGET_M1[key]
        scores[key] = min(100, int(actual / max(target, 1) * 100))
    total = sum(scores.values()) // len(scores)
    return {"scores": scores, "overall": total}


# ─── マークダウンレポート生成 ─────────────────────────────────

def generate_report(history: list) -> str:
    if not history:
        return "# KPIレポート\n\nデータなし"

    latest = history[-1]
    date = latest["date"]
    yt = latest.get("youtube", {})
    nt = latest.get("note", {})
    xx = latest.get("x", {})
    sc = latest.get("score", {})

    lines = [
        f"# KPIレポート — {date}",
        "",
        "## 今日の数字",
        "",
        "| 指標 | 実績 | Month1目標 | 達成率 |",
        "|-----|------|-----------|-------|",
        f"| X フォロワー | {xx.get('followers', 0)} | {TARGET_M1['x_followers']} | {sc.get('scores', {}).get('x_followers', 0)}% |",
        f"| note PV | {nt.get('pv', 0)} | {TARGET_M1['note_pv']} | {sc.get('scores', {}).get('note_pv', 0)}% |",
        f"| YouTube登録者 | {yt.get('subscribers', 0)} | {TARGET_M1['yt_subscribers']} | {sc.get('scores', {}).get('yt_subscribers', 0)}% |",
        f"| Shorts再生 | {yt.get('shorts_views', 0)} | {TARGET_M1['shorts_views']} | — |",
        "",
        f"## 総合スコア: **{sc.get('overall', 0)}/100点**",
        "",
    ]

    if len(history) >= 2:
        prev = history[-2]
        lines += [
            "## 昨日比",
            "",
        ]
        for label, src, field in [("Xフォロワー", "x", "followers"), ("note PV", "note", "pv")]:
            cur = latest.get(src, {}).get(field, 0)
            prv = prev.get(src, {}).get(field, 0)
            diff = cur - prv
            arrow = "↑" if diff > 0 else ("↓" if diff < 0 else "→")
            lines.append(f"- {label}: {arrow}{abs(diff):+d}（{prv} → {cur}）")
        lines.append("")

    lines += [
        "## 改善アクション（スコア50%未満の指標）",
        "",
    ]
    for key, score in sc.get("scores", {}).items():
        if score < 50:
            actions = {
                "x_followers": "→ X投稿を比較・数字フックで2本追加",
                "note_pv": "→ noteのタイトルをSEO最適化して再公開",
                "yt_subscribers": "→ ShortsのCTAを「チャンネル登録」に変更",
            }
            lines.append(f"- **{key}** ({score}点): {actions.get(key, '要対応')}")

    lines.append("")
    lines.append("*このレポートはauto_kpi_tracker.pyが自動生成*")
    return "\n".join(lines)


# ─── メイン ──────────────────────────────────────────────────

def run():
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  KPI自動計測")
    print(f"  {TARGET_DATE}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "playwright",
                        "-q", "--break-system-packages"], capture_output=True)
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium",
                        "--with-deps"], capture_output=True)
        from playwright.sync_api import sync_playwright

    kpi_data = load_kpi()
    today = {"date": TARGET_DATE, "youtube": {}, "note": {}, "x": {}}

    with sync_playwright() as p:
        # YouTube
        print("\n  [YouTube]")
        browser, ctx = build_context(p, "youtube.com")
        try:
            today["youtube"] = fetch_youtube_kpi(ctx)
        finally:
            browser.close()

        # note
        print("\n  [note]")
        browser, ctx = build_context(p, "note.com")
        try:
            today["note"] = fetch_note_kpi(ctx)
        finally:
            browser.close()

        # X
        print("\n  [X]")
        browser, ctx = build_context(p, "twitter.com")
        try:
            today["x"] = fetch_x_kpi(ctx)
        finally:
            browser.close()

    today["score"] = calculate_score(today)

    kpi_data["history"].append(today)
    kpi_data["history"] = kpi_data["history"][-90:]  # 90日分保持
    save_kpi(kpi_data)

    report = generate_report(kpi_data["history"])
    KPI_REPORT.parent.mkdir(parents=True, exist_ok=True)
    KPI_REPORT.write_text(report, encoding="utf-8")

    print(f"\n  総合スコア: {today['score']['overall']}/100点")
    print(f"  レポート: {KPI_REPORT.name}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    return today["score"]["overall"]


if __name__ == "__main__":
    run()
