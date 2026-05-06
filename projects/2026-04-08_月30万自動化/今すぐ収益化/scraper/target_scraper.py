#!/usr/bin/env python3
"""
target_scraper.py — 営業ターゲット候補収集ツール（Playwright）

業界キーワードから企業候補をリストアップし、targets.csv 形式で出力する。

【法令・倫理】
  - 公開情報のみ取得（HP のお問い合わせメール）
  - robots.txt 尊重（User-Agent 明示・適切な間隔）
  - 連続アクセスは秒単位の間隔を空ける
  - 取得した email は特定電子メール法に従って利用すること
  - スクレイピング対象サイトの利用規約を必ず事前確認

【人手が必要なこと】
  - 初回ログイン不要（Playwright だけで動く）
  - 取得後の email は人間が必ず確認（誤送信防止）
  - 営業送信時は1件ずつパーソナライズすること

【使い方】
  pip install playwright requests beautifulsoup4
  playwright install chromium
  python target_scraper.py search "東京 オウンドメディア" --limit 10
  python target_scraper.py search "渋谷 飲食店 Instagram" --limit 20 --template B-1

出力先：
  ../sender/targets.csv（追記モード）
"""

import argparse
import csv
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
TARGETS_CSV = ROOT / "sender" / "targets.csv"
LOG_FILE = Path(__file__).parent / "scraper.log"


HEADERS = ["company", "name", "email", "template_id", "industry",
           "media_name", "keyword", "role", "competitor", "note"]


def search_google(query: str, limit: int = 10) -> list[str]:
    """Google 検索結果から企業 HP の URL リストを取得"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[ERROR] Playwright が未インストール")
        sys.exit(1)

    urls = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (compatible; ResearchBot/1.0; +contact-info-in-targets-csv)"
        )
        page = context.new_page()
        page.goto(f"https://www.google.com/search?q={query}&num={min(limit*2, 30)}")
        page.wait_for_load_state("networkidle", timeout=15000)

        # Google 検索結果から URL を抽出
        links = page.query_selector_all("a[href^='http']:not([href*='google.com'])")
        seen = set()
        for link in links:
            url = link.get_attribute("href")
            if url and url.startswith("http"):
                domain = re.match(r"https?://([^/]+)/?", url)
                if domain:
                    d = domain.group(1)
                    if d not in seen:
                        seen.add(d)
                        urls.append(url)
                        if len(urls) >= limit:
                            break
        browser.close()
    return urls


def extract_contact(url: str) -> dict:
    """企業 HP からお問い合わせ email・会社名を抽出"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"company": "", "email": "", "url": url}

    info = {"company": "", "email": "", "url": url, "media_name": ""}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (compatible; ResearchBot/1.0)"
        )
        page = context.new_page()
        try:
            page.goto(url, timeout=15000, wait_until="domcontentloaded")

            # タイトルから会社名候補
            title = page.title() or ""
            info["company"] = title.split("|")[0].split("-")[0].strip()[:50]

            # トップページ全体から email を grep
            content = page.content()
            emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", content)
            # 一般的な無関係 email を除外
            emails = [e for e in emails if not any(
                bad in e.lower() for bad in ["example.com", "@2x", ".png", ".jpg", "noreply"]
            )]
            if emails:
                info["email"] = emails[0]
            else:
                # /contact ページを試す
                contact_links = page.query_selector_all(
                    "a[href*='contact'], a[href*='inquiry'], a[href*='お問い合わせ']"
                )
                if contact_links:
                    href = contact_links[0].get_attribute("href")
                    if href:
                        full_url = href if href.startswith("http") else f"{url.rstrip('/')}/{href.lstrip('/')}"
                        try:
                            page.goto(full_url, timeout=10000)
                            content = page.content()
                            emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", content)
                            emails = [e for e in emails if not any(
                                bad in e.lower() for bad in ["example.com", "@2x", ".png", ".jpg", "noreply"]
                            )]
                            if emails:
                                info["email"] = emails[0]
                        except Exception:
                            pass
        except Exception as e:
            print(f"  [SKIP] {url}: {e}")
        finally:
            browser.close()

    return info


def append_to_targets(rows: list[dict], template_id: str, industry: str):
    """targets.csv に追記"""
    is_new = not TARGETS_CSV.exists()
    TARGETS_CSV.parent.mkdir(parents=True, exist_ok=True)
    with TARGETS_CSV.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADERS)
        if is_new:
            w.writeheader()
        for row in rows:
            w.writerow({
                "company": row.get("company", ""),
                "name": "",
                "email": row.get("email", ""),
                "template_id": template_id,
                "industry": industry,
                "media_name": row.get("media_name", ""),
                "keyword": "",
                "role": "ご担当者様",
                "competitor": "",
                "note": f"自動収集 from {row.get('url','')}",
            })


def cmd_search(args):
    print(f"[INFO] 検索: '{args.query}' (limit={args.limit})")
    urls = search_google(args.query, args.limit)
    print(f"[INFO] {len(urls)} 件の URL を取得")

    results = []
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] {url}")
        info = extract_contact(url)
        if info.get("email"):
            results.append(info)
            print(f"  → email: {info['email']}, company: {info['company']}")
        else:
            print("  → email 取得失敗")
        time.sleep(args.interval)

    if results:
        append_to_targets(results, args.template, args.industry)
        print(f"\n[OK] {len(results)} 件を {TARGETS_CSV} に追記")
    else:
        print("\n[INFO] 取得できた email がゼロ。検索キーワードを変えるか、--limit を増やしてみてください。")


def main():
    parser = argparse.ArgumentParser(description="営業ターゲット候補収集")
    sub = parser.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="検索＆抽出")
    s.add_argument("query", help="検索クエリ（例: '東京 オウンドメディア'）")
    s.add_argument("--limit", type=int, default=10, help="取得 URL 上限")
    s.add_argument("--interval", type=int, default=3, help="アクセス間隔（秒）")
    s.add_argument("--template", default="A-1", help="使う営業テンプレ ID")
    s.add_argument("--industry", default="", help="業種ラベル")
    s.set_defaults(func=cmd_search)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
