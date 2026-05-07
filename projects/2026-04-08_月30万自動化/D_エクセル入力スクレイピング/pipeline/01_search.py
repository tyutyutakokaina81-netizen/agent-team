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
    # 汎用（広く拾う）
    "データ入力",
    "エクセル入力",
    "スクレイピング",
    "データ収集",
    "CSV作成",
    # 形式系（採用率の高い具体タスク）
    "リスト作成",
    "転記",
    "一覧化",
    # 高単価系（単価アップが見込める案件）
    "Excel自動化",
    "VBA",
    "マクロ",
    "API連携",
    # 継続系（継続契約に直結しやすい）
    "定期",
    "月次",
]

# ─────────────────────────────────────────────
# クラウドワークス
# ─────────────────────────────────────────────

def search_crowdworks(page, keyword: str) -> list[dict]:
    """クラウドワークスの案件一覧を取得（全リンクスキャン方式）"""
    import urllib.parse, re
    jobs = []
    encoded = urllib.parse.quote(keyword)
    url = f"https://crowdworks.jp/public/jobs/search?order=new&keyword={encoded}"
    page.goto(url)
    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass  # タイムアウトしても続行
    _human_scroll(page)

    # 全リンクを取得してjob URLをフィルタ
    links = page.query_selector_all("a")
    seen = set()
    for link in links:
        try:
            href = link.get_attribute("href") or ""
            if not href or href in seen:
                continue
            # crowdworksの案件URL（数字IDを含む）
            if not re.search(r'(crowdworks\.jp)?/public/jobs/\d+', href):
                continue
            # 検索ページ自体は除外
            if 'search' in href or 'category' in href:
                continue
            seen.add(href)
            title = link.inner_text().strip()
            if not title or len(title) < 5:
                continue
            url_full = href if href.startswith("http") else f"https://crowdworks.jp{href}"
            jobs.append({
                "title": title,
                "url": url_full,
                "platform": "crowdworks",
                "keyword": keyword,
                "budget_text": "",
                "deadline_text": "",
                "found_at": datetime.now().isoformat(),
            })
        except Exception:
            continue

    return jobs[:15]


def get_crowdworks_detail(page, job: dict) -> dict:
    """案件詳細ページから本文を取得"""
    try:
        page.goto(job["url"])
        _human_scroll(page)
        # 複数のセレクタを試す
        for sel in [".job_offer__description", ".c-jobOffer__description",
                    "[class*='description']", "article", "main"]:
            desc_el = page.query_selector(sel)
            if desc_el:
                text = desc_el.inner_text().strip()
                if len(text) > 20:
                    job["description"] = text
                    return job
        job["description"] = job["title"]
    except Exception:
        job["description"] = job["title"]
    return job


# ─────────────────────────────────────────────
# ランサーズ
# ─────────────────────────────────────────────

def search_lancers(page, keyword: str) -> list[dict]:
    """ランサーズの案件一覧を取得（全リンクスキャン方式）"""
    import urllib.parse, re
    jobs = []
    encoded = urllib.parse.quote(keyword)
    url = f"https://www.lancers.jp/work/search?keyword={encoded}&open=1&sort=new"
    page.goto(url)
    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass  # タイムアウトしても続行
    _human_scroll(page)

    # 全リンクを取得してjob URLをフィルタ
    links = page.query_selector_all("a")
    seen_lancers = set()
    for link in links:
        try:
            href = link.get_attribute("href") or ""
            if not href or href in seen_lancers:
                continue
            # lancersの案件URL（数字IDを含む）
            if not re.search(r'lancers\.jp/(work|tasks)/.*\d|^/(work|tasks)/.*\d', href):
                continue
            if 'search' in href or 'category' in href:
                continue
            seen_lancers.add(href)
            title = link.inner_text().strip()
            if not title or len(title) < 5:
                continue
            url_full = href if href.startswith("http") else f"https://www.lancers.jp{href}"
            jobs.append({
                "title": title,
                "url": url_full,
                "platform": "lancers",
                "keyword": keyword,
                "budget_text": "",
                "found_at": datetime.now().isoformat(),
            })
        except Exception:
            continue
    return jobs[:15]


def _lancers_old_card_parse(cards, jobs, keyword):
    """旧セレクタ（フォールバック用）"""
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
        for sel in [".c-workDetail__description", ".p-workDetail__body",
                    "[class*='description']", "article", "main"]:
            desc_el = page.query_selector(sel)
            if desc_el:
                text = desc_el.inner_text().strip()
                if len(text) > 20:
                    job["description"] = text
                    return job
        job["description"] = job["title"]
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
            browser = p.chromium.launch(
                headless=True,  # バックグラウンドで実行（画面表示なし）
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                storage_state=storage,
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()
            # 自動化フラグを非表示
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            raw_jobs = []
            first_kw = True
            for kw in KEYWORDS:
                print(f"  検索: 「{kw}」", end=" ", flush=True)
                try:
                    if platform == "crowdworks":
                        jobs = search_crowdworks(page, kw)
                    else:
                        jobs = search_lancers(page, kw)
                    # 最初のキーワードでスクリーンショット保存（デバッグ用）
                    if first_kw:
                        ss_path = OUTPUT_DIR / f"{platform}_debug.png"
                        page.screenshot(path=str(ss_path))
                        print(f"\n  [DEBUG] スクリーンショット保存: {ss_path}")
                        first_kw = False
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

            all_jobs.extend(unique[:30])
            context.close()
            print(f"[{platform}] {len(unique[:30])}件取得完了（うち詳細: 上位20件）")

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
