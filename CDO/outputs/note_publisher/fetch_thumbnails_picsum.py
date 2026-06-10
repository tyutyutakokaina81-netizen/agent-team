#!/usr/bin/env python3
"""最終フォールバック: キー不要の無料写真サービス Picsum で、サムネ未取得の記事を必ず1枚埋める。

Gemini/Pexels/Pollinations のいずれでも埋まらなかった記事に対し、
https://picsum.photos/seed/{seed}/1280/720 から写真風画像を取得して保存する。
- キー不要・完全無料。
- seed=記事stem なので、同じ記事には常に同じ写真（再実行で変わらない）。
- 内容に厳密一致はしない（汎用写真）。relevant な画像は Gemini/Pexels 経路で取得し、
  ここはあくまで「サムネが1枚も無い」を無くすための保険。

使い方:
  python3 fetch_thumbnails_picsum.py
  python3 fetch_thumbnails_picsum.py --filter 2026-06-09
"""
from __future__ import annotations
import sys, glob, hashlib, urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parents[2]
ARTICLES_DIR = REPO / "CMO" / "outputs"
THUMB_DIR = SCRIPT_DIR / "thumbnails"
EXTS = (".jpg", ".jpeg", ".png", ".webp")


def has_thumb(stem: str) -> bool:
    return any((THUMB_DIR / f"{stem}{e}").exists() for e in EXTS)


def main() -> None:
    flt = ""
    if "--filter" in sys.argv:
        flt = sys.argv[sys.argv.index("--filter") + 1]
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    ok = skip = miss = 0
    for f in sorted(glob.glob(str(ARTICLES_DIR / "*note記事*.md"))):
        p = Path(f)
        stem = p.stem
        if flt and flt not in p.name:
            continue
        if has_thumb(stem):
            skip += 1
            continue
        seed = hashlib.md5(stem.encode("utf-8")).hexdigest()[:12]
        url = f"https://picsum.photos/seed/{seed}/1280/720"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            (THUMB_DIR / f"{stem}.jpg").write_bytes(data)
            print(f"  {stem}.jpg  <-  picsum/{seed}")
            ok += 1
        except Exception as e:
            print(f"  skip {stem}: {e}")
            miss += 1
    print(f"\npicsum filled {ok} / already {skip} / missed {miss}  → {THUMB_DIR}")


if __name__ == "__main__":
    main()
