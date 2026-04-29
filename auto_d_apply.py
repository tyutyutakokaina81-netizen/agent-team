#!/usr/bin/env python3
"""
auto_d_apply.py — CW案件をリアルタイム検索して自動応募

固定URLではなく毎回検索して新着案件に応募する
対象: データ入力・スクレイピング・Excel・事務
"""

import json
import time
import sys
from pathlib import Path

REPO = Path(__file__).parent
SESSION_FILE = REPO / ".sessions" / "crowdworks_session.json"
APPLIED_FILE = REPO / ".sessions" / "cw_applied.json"
MAX_APPLY = 5  # 1日の最大応募数

# 検索キーワード（順番に試して案件を集める）
SEARCH_QUERIES = [
    "データ入力",
    "Excel 入力",
    "スクレイピング",
    "文字起こし",
    "リスト作成",
]

# 案件種別ごとの応募文テンプレート
TEMPLATES = {
    "default": """はじめまして。
ご案件を拝見し、ぜひ取り組みたいと思い応募いたします。

■ 対応可能な内容
・Excelおよびスプレッドシートでのデータ入力
・Webサイトからの情報収集・整理
・指示書に沿った正確な作業

■ 稼働
平日3〜5時間 / 土日も対応可能
納期は必ず厳守いたします。ダブルチェックで品質を確保します。

不明点はすぐにご確認します。お気軽にご連絡ください。
よろしくお願いいたします。""",

    "scraping": """はじめまして。
スクレイピング・データ収集のご案件に応募いたします。

■ 対応可能
・PythonによるWebスクレイピング（requests / Playwright）
・Excel / CSVへの自動出力
・取得データの整形・クレンジング

■ 稼働
平日3〜5時間 / 土日も対応可能
仕様をお伝えいただければ即日対応いたします。

よろしくお願いいたします。""",

    "excel": """はじめまして。
Excel作業のご案件に応募いたします。

■ 対応可能
・データ入力・整理・集計
・VLOOKUP / IF / ピボットテーブル
・フォーマット統一・エラーチェック

■ 稼働
平日3〜5時間 / 土日も対応可能
正確性を最優先に作業いたします。

よろしくお願いいたします。""",
}


def load_applied() -> set:
    if APPLIED_FILE.exists():
        data = json.loads(APPLIED_FILE.read_text())
        return set(data.get("urls", []))
    return set()


def save_applied(applied: set):
    APPLIED_FILE.parent.mkdir(exist_ok=True)
    APPLIED_FILE.write_text(json.dumps(
        {"urls": list(applied)}, ensure_ascii=False, indent=2))


def pick_template(title: str, description: str) -> str:
    text = (title + description).lower()
    if any(w in text for w in ["スクレイピング", "python", "自動", "収集"]):
        return TEMPLATES["scraping"]
    if any(w in text for w in ["excel", "エクセル", "スプレッドシート", "関数"]):
        return TEMPLATES["excel"]
    return TEMPLATES["default"]


def search_jobs(page, query: str) -> list[dict]:
    """CWで案件を検索してURLリストを返す"""
    url = f"https://crowdworks.jp/public/jobs/search?order=new&job_category_id=1&keyword={query}"
    page.goto(url, wait_until="networkidle", timeout=20000)
    time.sleep(2)

    jobs = []
    links = page.query_selector_all("article.job_offer a[href*='/public/jobs/']")
    for link in links[:8]:
        href = link.get_attribute("href")
        if href and "/public/jobs/" in href:
            full_url = href if href.startswith("http") else f"https://crowdworks.jp{href}"
            title_el = link.query_selector("h3, .job_offer_name, .title")
            title = title_el.inner_text().strip() if title_el else query
            jobs.append({"url": full_url, "title": title[:60]})
    return jobs


def apply_job(page, job: dict, template: str) -> bool:
    page.goto(job["url"], wait_until="networkidle", timeout=20000)
    time.sleep(2)

    # 応募ボタンを探してクリック
    for sel in ["a.btn-apply", "a[href*='apply']",
                "a:has-text('応募する')", "button:has-text('応募する')"]:
        btn = page.query_selector(sel)
        if btn:
            btn.click()
            time.sleep(2)
            break
    else:
        return False

    # 応募文入力
    for sel in ["textarea[name*='body']", "#job_offer_apply_body",
                "#body", "textarea.apply-body", "textarea"]:
        ta = page.query_selector(sel)
        if ta:
            ta.fill(template)
            time.sleep(0.5)
            break
    else:
        return False

    # 送信
    for sel in ["input[type='submit']", "button[type='submit']",
                "button:has-text('送信')", "button:has-text('応募')"]:
        btn = page.query_selector(sel)
        if btn:
            btn.click()
            time.sleep(3)
            return True
    return False


def extract_cw_cookies():
    """ChromeからCWセッションを自動取得"""
    try:
        import browser_cookie3
        cookies = list(browser_cookie3.chrome(domain_name=".crowdworks.jp"))
        if not cookies:
            return False
        state = {
            "cookies": [
                {"name": c.name, "value": c.value,
                 "domain": c.domain if c.domain.startswith(".") else f".{c.domain}",
                 "path": c.path or "/", "secure": bool(c.secure),
                 "httpOnly": False, "sameSite": "Lax"}
                for c in cookies if c.value
            ],
            "origins": [],
        }
        SESSION_FILE.parent.mkdir(exist_ok=True)
        SESSION_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))
        return True
    except Exception:
        return False


def run():
    # セッション自動取得
    if not SESSION_FILE.exists():
        print("  🍪 CWセッションをChromeから取得中...")
        if not extract_cw_cookies():
            print("  ❌ セッション取得失敗（Chromeでcrowdworks.jpにログインしてください）")
            return

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "playwright",
                        "-q", "--break-system-packages"], capture_output=True)
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"],
                       capture_output=True)
        from playwright.sync_api import sync_playwright

    applied = load_applied()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  CW 新着案件 自動応募（最大5件）")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    storage = json.loads(SESSION_FILE.read_text())
    done = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=200)
        ctx = browser.new_context(
            storage_state=storage,
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        )
        page = ctx.new_page()

        # 各キーワードで案件検索
        candidates = []
        for q in SEARCH_QUERIES:
            if len(candidates) >= MAX_APPLY * 3:
                break
            jobs = search_jobs(page, q)
            for j in jobs:
                if j["url"] not in applied and j not in candidates:
                    candidates.append(j)

        print(f"  候補: {len(candidates)}件 → 最大{MAX_APPLY}件に応募")

        for job in candidates[:MAX_APPLY]:
            print(f"\n  [{job['title'][:40]}]")
            template = pick_template(job["title"], "")
            try:
                ok = apply_job(page, job, template)
                if ok:
                    applied.add(job["url"])
                    done.append(job["title"][:30])
                    print(f"  ✅ 応募完了")
                else:
                    print(f"  ❌ 応募失敗（応募済み or セレクタ不一致）")
            except Exception as e:
                print(f"  ❌ エラー: {e}")
            time.sleep(5)

        ctx.storage_state(path=str(SESSION_FILE))
        browser.close()

    save_applied(applied)
    print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  完了: {len(done)}/{MAX_APPLY}件")
    for t in done:
        print(f"  ✅ {t}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    run()
