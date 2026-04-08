"""
01_search.py — 案件検索
クラウドワークス・ランサーズの公開ページから案件を収集する。
"""

import json
import time
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path

# 検索キーワード
KEYWORDS = [
    "データ入力",
    "エクセル入力",
    "Excel 入力",
    "スクレイピング",
    "CSV作成",
    "データ収集",
]

# 出力先
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


def fetch_page(url: str, delay: float = 2.0) -> str:
    """指定URLのHTMLを取得する（礼儀正しいクロール）"""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; JobSearchBot/1.0; "
            "+https://github.com/your-repo)"
        )
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            html = res.read().decode("utf-8", errors="replace")
        time.sleep(delay)  # サーバー負荷軽減
        return html
    except Exception as e:
        print(f"[ERROR] fetch_page: {url} -> {e}")
        return ""


def search_crowdworks(keyword: str) -> list[dict]:
    """クラウドワークスの案件検索結果ページをパース（スクレイピング）"""
    from html.parser import HTMLParser

    encoded = urllib.parse.quote(keyword)
    url = f"https://crowdworks.jp/public/jobs/search?order=new&keyword={encoded}"
    html = fetch_page(url)
    if not html:
        return []

    jobs = []

    class JobParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self._in_title = False
            self._current = {}
            self._capture = False

        def handle_starttag(self, tag, attrs):
            attrs_dict = dict(attrs)
            # 案件タイトルリンクの特定（クラス名は変更される可能性あり）
            if tag == "a" and "job_offers" in attrs_dict.get("href", ""):
                self._current = {
                    "url": "https://crowdworks.jp" + attrs_dict["href"],
                    "title": "",
                    "platform": "crowdworks",
                    "keyword": keyword,
                    "found_at": datetime.now().isoformat(),
                }
                self._capture = True

        def handle_data(self, data):
            if self._capture and data.strip():
                self._current["title"] += data.strip()

        def handle_endtag(self, tag):
            if self._capture and tag == "a":
                if self._current.get("title"):
                    jobs.append(self._current.copy())
                self._capture = False
                self._current = {}

    parser = JobParser()
    parser.feed(html)
    return jobs[:20]  # 最大20件


def search_lancers(keyword: str) -> list[dict]:
    """ランサーズの案件検索結果ページをパース（スクレイピング）"""
    from html.parser import HTMLParser

    encoded = urllib.parse.quote(keyword)
    url = f"https://www.lancers.jp/work/search?keyword={encoded}&open=1"
    html = fetch_page(url)
    if not html:
        return []

    jobs = []

    class JobParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self._current = {}
            self._capture = False

        def handle_starttag(self, tag, attrs):
            attrs_dict = dict(attrs)
            href = attrs_dict.get("href", "")
            if tag == "a" and "/work/detail/" in href:
                self._current = {
                    "url": (
                        href if href.startswith("http")
                        else "https://www.lancers.jp" + href
                    ),
                    "title": "",
                    "platform": "lancers",
                    "keyword": keyword,
                    "found_at": datetime.now().isoformat(),
                }
                self._capture = True

        def handle_data(self, data):
            if self._capture and data.strip():
                self._current["title"] += data.strip()

        def handle_endtag(self, tag):
            if self._capture and tag == "a":
                if self._current.get("title"):
                    jobs.append(self._current.copy())
                self._capture = False
                self._current = {}

    parser = JobParser()
    parser.feed(html)
    return jobs[:20]


def run():
    all_jobs = []
    for kw in KEYWORDS:
        print(f"[検索中] {kw}")
        all_jobs += search_crowdworks(kw)
        all_jobs += search_lancers(kw)

    # 重複除去（URL基準）
    seen = set()
    unique_jobs = []
    for job in all_jobs:
        if job["url"] not in seen:
            seen.add(job["url"])
            unique_jobs.append(job)

    out_path = OUTPUT_DIR / f"{datetime.now().strftime('%Y-%m-%d_%H%M')}_jobs.json"
    out_path.write_text(
        json.dumps(unique_jobs, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[完了] {len(unique_jobs)}件 → {out_path}")
    return unique_jobs


if __name__ == "__main__":
    run()
