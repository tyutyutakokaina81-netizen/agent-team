#!/usr/bin/env python3
"""OG画像を Pexels API（無料）から自動取得して site/og/ に保存する。

私(code)のコンテナはネット遮断だが、**GitHub Actions はネット可**なのでそこで実行する。
→ フリー画像の手配（これまで cowork/オーナーの手作業だった部分）をクラウドで自動化。

必要: 環境変数 PEXELS_API_KEY（無料。https://www.pexels.com/api/ で取得→リポジトリ Secrets に登録）。
Pexels の写真は商用利用可・帰属任意（写真風＝オーナー方針に合致）。ドラえもん等キャラは検索語に含めない。

使い方（Actions/ローカル）:
  PEXELS_API_KEY=xxxx python3 site/fetch_og_images.py
  PEXELS_API_KEY=xxxx python3 site/fetch_og_images.py --force   # 既存も再取得
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from build import collect, OG_SRC, OG_EXTS  # noqa: E402

KEY = os.environ.get("PEXELS_API_KEY")

# スラッグ部分一致 → Pexels検索語（ドラえもん等キャラ語は使わず、場所/物で写真風を引く）
QUERY_RULES = [
    ("amaharashi", "Amaharashi coast Toyama sea and mountains"),
    ("gokayama", "Gokayama gassho thatched village Japan"),
    ("zuiryuji", "Japanese zen temple"),
    ("temple", "Japanese zen temple"),
    ("tram", "Japan tram streetcar city"),
    ("doraemon", "Takaoka Toyama Japan park"),
    ("fujiko", "Japanese art museum interior"),
    ("korokke", "croquette japanese food"),
    ("shiraebi", "white shrimp sashimi"),
    ("masuzushi", "japanese pressed sushi"), ("sushi", "japanese sushi"),
    ("ramen", "black soy ramen"), ("udon", "udon noodles"),
    ("wagyu", "wagyu beef"), ("beef", "wagyu beef"),
    ("konbu", "kelp sashimi"), ("oden", "oden hotpot"),
    ("market", "japan fish market morning"),
    ("station", "japan rural train station coast"),
    ("yamachosuji", "japanese old merchant townscape"),
    ("mount", "japan mountain view over town"),
    ("lacquer", "japanese lacquerware"), ("paper", "japanese washi paper"),
    ("carving", "japanese wood carving"), ("soba", "soba noodles"),
    ("sake", "japanese sake"), ("kamaboko", "japanese fish cake"),
]


def query_for(a) -> str:
    s = a["slug"]
    for key, q in QUERY_RULES:
        if key in s:
            return q
    cat = a["cat"]
    if cat == "Food & Drink":
        return "japanese cuisine toyama"
    if cat == "Doraemon & Fujiko":
        return "takaoka toyama japan"
    return "toyama japan landscape"


def has_image(slug: str) -> bool:
    return any((OG_SRC / f"{slug}{e}").exists() for e in OG_EXTS)


def fetch_url(query: str):
    url = "https://api.pexels.com/v1/search?" + urllib.parse.urlencode(
        {"query": query, "orientation": "landscape", "per_page": 1, "size": "medium"})
    req = urllib.request.Request(url, headers={"Authorization": KEY})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    photos = data.get("photos") or []
    if not photos:
        return None
    src = photos[0]["src"]
    return src.get("large") or src.get("landscape") or src.get("original")


def save(query: str, slug: str) -> bool:
    img = fetch_url(query)
    if not img:
        print(f"  no result: {slug} ({query})")
        return False
    urllib.request.urlretrieve(img, OG_SRC / f"{slug}.jpg")
    print(f"  {slug}.jpg  <-  {query}")
    return True


def main() -> None:
    if not KEY:
        sys.exit("PEXELS_API_KEY が未設定です。リポジトリ Secrets に登録してください。")
    force = "--force" in sys.argv
    OG_SRC.mkdir(parents=True, exist_ok=True)
    n = 0
    # 共通フォールバック
    if force or not has_image("default"):
        n += save("toyama japan tateyama mountains coast", "default")
    for a in collect():
        if not force and has_image(a["slug"]):
            continue
        try:
            n += save(query_for(a), a["slug"])
        except Exception as e:
            print(f"  skip {a['slug']}: {e}")
    print(f"fetched {n} image(s) → {OG_SRC}")


if __name__ == "__main__":
    main()
