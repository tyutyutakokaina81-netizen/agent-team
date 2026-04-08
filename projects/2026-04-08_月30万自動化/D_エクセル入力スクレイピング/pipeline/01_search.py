"""
01_search.py — 案件検索（Playwright版）
保存済みセッションを使って案件一覧を自動取得・詳細情報を収集する。

実行方法:
  python 01_search.py               # 全プラットフォーム検索
  python 01_search.py crowdworks    # クラウドワークスのみ
  python 01_search.py lancers       # ランサーズのみ
"""

import json
import random
import sys
import time
from datetime import datetime
from pathlib import Path

SESSION_DIR = Path(__file__).parent.parent / ".sessions"
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

KEYWORDS = [
    "データ入力",
    "エクセル入力",
    "スクレイピング",
    "データ収集",
    "CSV作成",
]

# ─────────────────────────────────────────────
# クラウドワークス
# ─────────────────────────────────────────────

def search_crowdworks(page, keyword: str) -> list[dict]:
    """クラウドワークスの案件一覧を取得"""
    jobs = []
    url = f"https://crowdworks.jp/public/jobs/search?order=new&keyword={keyword}"
    page.goto(url)
    _human_scroll(page)

    # 案件カードを取得
    cards = page.query_selector_all(".job_offer__item, .c-jobOffer__item")
    for card in cards[:10]:
        try:
            title_el = card.query_selector("a.job_offer__title, a.c-jobOffer__title")
            if not title_el:
                continue
            title = title_el.inner_text().strip()
            href = title_el.get_attribute("href") or ""
            url_full = href if href.startswith("http") else f"https://crowdworks.jp{href}"

            # 報酬・納期を取得
            budget_el = card.query_selector(".job_offer__budget, .c-jobOffer__budget")
            deadline_el = card.query_selector(".job_offer__deadline, .c-jobOffer__deadline")

            jobs.append({
                "title": title,
                "url": url_full,
                "platform": "crowdworks",
                "keyword": keyword,
                "budget_text": budget_el.inner_text().strip() if budget_el else "",
                "deadline_text": deadline_el.inner_text().strip() if deadline_el else "",
                "found_at": datetime.now().isoformat(),
            })
        except Exception:
            continue

    return jobs


def get_crowdworks_detail(page, job: dict) -> dict:
    """案件詳細ページから本文を取得"""
    try:
        page.goto(job["url"])
        _human_scroll(page)
        desc_el = page.query_selector(".job_offer__description, .c-jobOffer__description")
        job["description"] = desc_el.inner_text().strip() if desc_el else job["title"]
    except Exception:
        job["description"] = job["title"]
    return job


# ─────────────────────────────────────────────
# ランサーズ
# ─────────────────────────────────────────────

def search_lancers(page, keyword: str) -> list[dict]:
    """ランサーズの案件一覧を取得"""
    import urllib.parse
    jobs = []
    encoded = urllib.parse.quote(keyword)
    url = f"https://www.lancers.jp/work/search?keyword={encoded}&open=1&sort=new"
    page.goto(url)
    _human_scroll(page)

    cards = page.query_selector_all(".c-workCard, .p-workCard")
    for card in cards[:10]:
        try:
            title_el = card.query_selector("a.c-workCard__title, a.p-workCard__title, h3 a")
            if not title_el:
                continue
            title = title_el.inner_text().strip()
            href = title_el.get_attribute("href") or ""
            url_full = href if href.startswith("http") else f"https://www.lancers.jp{href}"

            budget_el = card.query_selector(".c-workCard__budget, .p-workCard__budget")

            jobs.append({
                "title": title,
                "url": url_full,
                "platform": "lancers",
                "keyword": keyword,
                "budget_text": budget_el.inner_text().strip() if budget_el else "",
                "found_at": datetime.now().isoformat(),
            })
        except Exception:
            continue

    return jobs


def get_lancers_detail(page, job: dict) -> dict:
    """案件詳細ページから本文を取得"""
    try:
        page.goto(job["url"])
        _human_scroll(page)
        desc_el = page.query_selector(".c-workDetail__description, .p-workDetail__body")
        job["description"] = desc_el.inner_text().strip() if desc_el else job["title"]
    except Exception:
        job["description"] = job["title"]
    return job


# ─────────────────────────────────────────────
# ユーティリティ
# ─────────────────────────────────────────────

def _human_scroll(page):
    """人間らしいスクロール動作"""
    page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
    time.sleep(random.uniform(0.8, 1.5))
    page.evaluate("window.scrollTo(0, document.body.scrollHeight * 2 / 3)")
    time.sleep(random.uniform(0.5, 1.0))


def _random_wait(min_sec=1.5, max_sec=3.5):
    """人間らしいランダム待機"""
    time.sleep(random.uniform(min_sec, max_sec))


# ─────────────────────────────────────────────
# メイン
# ─────────────────────────────────────────────

def run(platforms: list[str] | None = None) -> list[dict]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[ERROR] pip install playwright && playwright install chromium")
        return []

    if platforms is None:
        platforms = ["crowdworks", "lancers"]

    all_jobs = []

    with sync_playwright() as p:
        for platform in platforms:
            session_file = SESSION_DIR / f"{platform}_session.json"
            if not session_file.exists():
                print(f"[SKIP] {platform}: セッション未設定（00_session_setup.py を実行してください）")
                continue

            print(f"\n[{platform}] 検索開始...")
            storage = json.loads(session_file.read_text(encoding="utf-8"))
            context = p.chromium.launch(headless=True).new_context(
                storage_state=storage,
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()

            raw_jobs = []
            for kw in KEYWORDS:
                print(f"  検索: 「{kw}」", end=" ", flush=True)
                try:
                    if platform == "crowdworks":
                        jobs = search_crowdworks(page, kw)
                    else:
                        jobs = search_lancers(page, kw)
                    raw_jobs.extend(jobs)
                    print(f"→ {len(jobs)}件")
                except Exception as e:
                    print(f"→ エラー: {e}")
                _random_wait()

            # 重複除去
            seen = set()
            unique = [j for j in raw_jobs if not (j["url"] in seen or seen.add(j["url"]))]

            # 詳細取得（上位20件のみ）
            print(f"  詳細取得: {min(len(unique), 20)}件...")
            for i, job in enumerate(unique[:20]):
                try:
                    if platform == "crowdworks":
                        get_crowdworks_detail(page, job)
                    else:
                        get_lancers_detail(page, job)
                    print(f"  [{i+1}/{min(len(unique), 20)}] ✓", end="\r")
                except Exception:
                    pass
                _random_wait(1.0, 2.0)

            all_jobs.extend(unique[:20])
            context.close()
            print(f"[{platform}] {len(unique[:20])}件取得完了")

    # 重複除去（全プラットフォーム統合）
    seen = set()
    final = [j for j in all_jobs if not (j["url"] in seen or seen.add(j["url"]))]

    out = OUTPUT_DIR / f"{datetime.now().strftime('%Y-%m-%d_%H%M')}_jobs.json"
    out.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[完了] {len(final)}件 → {out}")
    return final


if __name__ == "__main__":
    targets = sys.argv[1:] if len(sys.argv) > 1 else None
    run(targets)
