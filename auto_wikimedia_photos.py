#!/usr/bin/env python3
"""
auto_wikimedia_photos.py — Wikimedia Commons から高岡市の無料写真を自動取得

CC BY-SA ライセンス（商用利用可・帰属表示必要）
動画・note記事の背景画像として使用
"""

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).parent
PHOTO_DIR = REPO / "CMO" / "assets" / "takaoka_photos"
PHOTO_DIR.mkdir(parents=True, exist_ok=True)
LICENSE_LOG = PHOTO_DIR / "licenses.json"

# 取得する写真リスト（ファイル名→保存名のマッピング）
TARGETS = [
    {
        "query": "Zuiryuji Temple Takaoka",
        "save_as": "zuiryuji.jpg",
        "scene": "瑞龍寺",
    },
    {
        "query": "Takaoka Daibutsu Buddha",
        "save_as": "daibutsu.jpg",
        "scene": "高岡大仏",
    },
    {
        "query": "Kanayamachi Takaoka",
        "save_as": "kanayamachi.jpg",
        "scene": "金屋町",
    },
    {
        "query": "Takaoka city Toyama",
        "save_as": "takaoka_overview.jpg",
        "scene": "高岡市全景",
    },
    {
        "query": "Hokuriku Shinkansen",
        "save_as": "shinkansen.jpg",
        "scene": "北陸新幹線",
    },
    {
        "query": "Japanese korokke croquette street food",
        "save_as": "takaoka_food.jpg",
        "scene": "高岡グルメ",
    },
    {
        "query": "Takaoka copperware casting",
        "save_as": "copperware.jpg",
        "scene": "高岡銅器",
    },
]

API = "https://commons.wikimedia.org/w/api.php"


def search_image(session, query: str) -> dict | None:
    """Wikimedia Commons で画像を検索して最初のヒットを返す"""
    params = {
        "action": "query",
        "list": "search",
        "srsearch": f"{query} filetype:bitmap",
        "srnamespace": "6",  # File namespace
        "srlimit": "5",
        "format": "json",
    }
    try:
        r = session.get(API, params=params, timeout=10)
        data = r.json()
        results = data.get("query", {}).get("search", [])
        for res in results:
            title = res["title"]
            if any(ext in title.lower() for ext in [".jpg", ".jpeg", ".png"]):
                return {"title": title}
    except Exception as e:
        print(f"  検索エラー: {e}")
    return None


def get_image_url(session, title: str) -> dict | None:
    """画像のダウンロードURLとライセンス情報を取得"""
    params = {
        "action": "query",
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|size",
        "iiurlwidth": "1280",
        "format": "json",
    }
    try:
        r = session.get(API, params=params, timeout=10)
        data = r.json()
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            info = page.get("imageinfo", [{}])[0]
            meta = info.get("extmetadata", {})
            return {
                "url": info.get("thumburl") or info.get("url"),
                "license": meta.get("LicenseShortName", {}).get("value", "Unknown"),
                "author": meta.get("Artist", {}).get("value", "Unknown"),
                "title": title,
            }
    except Exception as e:
        print(f"  URL取得エラー: {e}")
    return None


def download_photo(session, url: str, save_path: Path) -> bool:
    try:
        r = session.get(url, timeout=30, stream=True)
        r.raise_for_status()
        save_path.write_bytes(r.content)
        return True
    except Exception as e:
        print(f"  ダウンロードエラー: {e}")
        return False


def copy_to_announcer_dir(save_as: str):
    """動画生成で使うannouncerディレクトリにもコピー"""
    src = PHOTO_DIR / save_as
    dst = REPO / "CMO" / "assets" / "announcer" / save_as
    if src.exists() and not dst.exists():
        import shutil
        shutil.copy(src, dst)


def fetch_all():
    try:
        import requests
    except ImportError:
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "requests",
                        "-q", "--break-system-packages"], capture_output=True)
        import requests

    session = requests.Session()
    session.headers["User-Agent"] = "agent-team-bot/1.0 (takaoka tourism project)"

    licenses = {}
    if LICENSE_LOG.exists():
        licenses = json.loads(LICENSE_LOG.read_text())

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  Wikimedia Commons 写真取得")
    print("  ライセンス: CC BY-SA（商用可・帰属必要）")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    for target in TARGETS:
        save_path = PHOTO_DIR / target["save_as"]
        if save_path.exists():
            print(f"  ✅ {target['save_as']} 既存（スキップ）")
            copy_to_announcer_dir(target["save_as"])
            continue

        print(f"\n  [{target['scene']}] 検索中: {target['query']}")
        result = search_image(session, target["query"])
        if not result:
            print(f"  ⚠️  見つからず（プレースホルダーのまま）")
            continue

        info = get_image_url(session, result["title"])
        if not info or not info.get("url"):
            print(f"  ⚠️  URL取得失敗")
            continue

        ok = download_photo(session, info["url"], save_path)
        if ok:
            licenses[target["save_as"]] = {
                "title": info["title"],
                "license": info["license"],
                "author": info["author"],
                "source": "Wikimedia Commons",
            }
            copy_to_announcer_dir(target["save_as"])
            print(f"  ✅ {target['save_as']} 取得完了 ({info['license']})")
        time.sleep(1)  # API負荷軽減

    LICENSE_LOG.write_text(json.dumps(licenses, ensure_ascii=False, indent=2))
    print(f"\n  保存先: {PHOTO_DIR}")
    print(f"  ライセンス: {LICENSE_LOG}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    fetch_all()
