"""
fetch_past_thumbnails.py — 過去のnote投稿からサムネ画像とタイトルを収集する

実行：
    NOTE_SESSION_COOKIE='...' python fetch_past_thumbnails.py

または authenticated cookie がなくても、note.comはサムネ画像が公開なので
ログインなしで取れる可能性がある（試行する）。

出力：
- assets/thumbnail_reference/<記事ID>.jpg            （サムネ画像）
- assets/thumbnail_reference/style_summary.txt        （色味・構図の英語サマリ）
- assets/style_guide.md                                （文体ガイド：タイトル一覧から推定）
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PROJECT_DIR = Path(__file__).resolve().parents[1]
REFERENCE_DIR = PROJECT_DIR / "assets" / "thumbnail_reference"
STYLE_GUIDE = PROJECT_DIR / "assets" / "style_guide.md"

NOTE_USER = os.environ.get("NOTE_USER", "safe_canna441")
PROFILE_URL = f"https://note.com/{NOTE_USER}"


def setup_browser():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[ERROR] playwright未インストール。`pip install playwright && playwright install chromium`")
        sys.exit(3)
    return sync_playwright


def collect_articles(page) -> list[dict]:
    """プロフィールページから記事一覧（タイトル + サムネURL + 記事URL）を収集する。

    note.com のプロフィールページは無限スクロール式。スクロールを数回繰り返して取得。
    """
    page.goto(PROFILE_URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)

    for _ in range(5):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(1500)

    articles_raw = page.evaluate(
        """
        () => {
          const items = [];
          document.querySelectorAll('a[href*="/n/"]').forEach((a) => {
            const href = a.getAttribute('href');
            const img = a.querySelector('img');
            const title = a.innerText.trim().split('\\n')[0];
            if (href && img && title) {
              items.push({ href, src: img.src, title });
            }
          });
          return items;
        }
        """
    )
    seen = set()
    deduped = []
    for a in articles_raw:
        key = a["href"]
        if key in seen:
            continue
        seen.add(key)
        deduped.append(a)
    return deduped


def download_image(url: str, dest: Path) -> None:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        dest.write_bytes(resp.read())


def write_style_guide(articles: list[dict]) -> None:
    titles = [a["title"] for a in articles]
    body = (
        "# 文体ガイド（過去タイトル一覧から自動生成）\n\n"
        f"参照アカウント：{PROFILE_URL}\n\n"
        f"取得記事数：{len(titles)}本\n\n"
        "## 過去タイトル一覧\n\n"
        + "\n".join(f"- {t}" for t in titles)
        + "\n"
    )
    STYLE_GUIDE.parent.mkdir(parents=True, exist_ok=True)
    STYLE_GUIDE.write_text(body, encoding="utf-8")


def main() -> int:
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    sync_playwright = setup_browser()
    cookie_json = os.environ.get("NOTE_SESSION_COOKIE", "").strip()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        if cookie_json:
            try:
                context.add_cookies(json.loads(cookie_json))
            except json.JSONDecodeError:
                print("[WARN] cookieのJSON parse失敗。匿名取得を試みます")

        page = context.new_page()
        articles = collect_articles(page)
        print(f"[INFO] 取得記事数: {len(articles)}")

        for i, a in enumerate(articles[:20]):
            article_id = re.sub(r"[^a-zA-Z0-9]", "_", a["href"].split("/")[-1])
            dest = REFERENCE_DIR / f"{i:02d}_{article_id}.jpg"
            try:
                download_image(a["src"], dest)
                print(f"[OK] {dest.name} ← {a['title'][:30]}")
            except Exception as e:
                print(f"[WARN] {a['title'][:30]}: {e}")

        write_style_guide(articles)
        print(f"[OK] 文体ガイド更新: {STYLE_GUIDE.relative_to(REPO_ROOT)}")

        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
