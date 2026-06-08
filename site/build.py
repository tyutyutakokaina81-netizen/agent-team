#!/usr/bin/env python3
"""英語SEOサイト ビルダー（依存ゼロ・Python標準ライブラリのみ）。

CMO/outputs/*_note記事_*.md の「## English」ブロックを抽出し、
海外Google検索に最適化した静的HTML（個別ページ＋index＋sitemap＋robots）を
site/public/ に生成する。GitHub Pages / Cloudflare Pages にそのまま配信できる。

なぜ作るか: note.com は海外英語検索に弱い。所有・高速・meta制御できる
英語ネイティブのSEO面を持ち、Doraemon/Kanazawa等の旅行クエリで実際に
見つかるようにするため（North Star=海外読者）。

使い方:
  python3 site/build.py                       # site/public/ を生成
  SITE_BASE_URL=https://example.com python3 site/build.py
"""
from __future__ import annotations

import html
import os
import pathlib
import re
import datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "CMO" / "outputs"
OUT = ROOT / "site" / "public"

# ---- サイト設定（オーナーは独自ドメインに差し替え可） ----
SITE_NAME = os.environ.get("SITE_NAME", "Hidden Hokuriku")
SITE_TAGLINE = "Takaoka, Toyama & the real hometown of Doraemon — day trips from Kanazawa"
BASE_URL = os.environ.get("SITE_BASE_URL", "https://example.github.io").rstrip("/")
AUTHOR = "A Takaoka resident"

# 分類用キーワード
FOOD_KW = ["寿司", "ブラック", "かまぼこ", "ホタルイカ", "へしこ", "豆腐", "地酒", "和菓子",
           "黒造り", "うどん", "地ビール", "昆布", "わかめ", "おでん", "干物", "せんべい",
           "ノドグロ", "フクラギ", "鮎", "バイ貝", "ゲンゲ", "岩がき", "素麺", "白えび",
           "唐揚", "コロッケ", "そば", "牛", "山菜", "大根", "ぶり"]
DORAEMON_KW = ["ドラえもん", "藤子", "Doraemon", "笑ゥせぇるすまん", "潮風ギャラリー"]


def slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s-]+", "-", s).strip("-")
    return s[:70] or "article"


def extract_english(text: str):
    """## English ブロックの (title, [paragraphs]) を返す。無ければ None。"""
    m = re.search(r"^##\s*English[^\n]*\n+```\n(.+?)\n```", text, re.S | re.M)
    if not m:
        return None
    block = m.group(1).strip()
    lines = [ln.rstrip() for ln in block.splitlines()]
    # 先頭の非空行をタイトル、残りを本文段落に
    title = ""
    rest_start = 0
    for i, ln in enumerate(lines):
        if ln.strip():
            title = ln.strip()
            rest_start = i + 1
            break
    paras, cur = [], []
    for ln in lines[rest_start:]:
        if ln.strip():
            cur.append(ln.strip())
        else:
            if cur:
                paras.append(" ".join(cur)); cur = []
    if cur:
        paras.append(" ".join(cur))
    return title, paras


def category_of(name: str) -> str:
    if any(k in name for k in DORAEMON_KW):
        return "Doraemon & Fujiko"
    if any(k in name for k in FOOD_KW):
        return "Food & Drink"
    return "Places & Culture"


def collect():
    arts = []
    for p in sorted(SRC.glob("*_note記事_*.md")):
        text = p.read_text(encoding="utf-8")
        en = extract_english(text)
        if not en:
            continue
        title, paras = en
        if not title or not paras:
            continue
        date = p.name[:10]
        slug = slugify(title)
        desc = re.sub(r"\s+", " ", paras[0])[:155]
        arts.append({
            "title": title, "paras": paras, "slug": slug, "date": date,
            "desc": desc, "cat": category_of(p.name), "src": p.name,
        })
    # slug 衝突回避
    seen = {}
    for a in arts:
        if a["slug"] in seen:
            seen[a["slug"]] += 1
            a["slug"] = f"{a['slug']}-{seen[a['slug']]}"
        else:
            seen[a["slug"]] = 1
    return arts


CSS = """
:root{--ink:#1a1a1a;--muted:#666;--accent:#0a6cff;--bg:#fff;--line:#eee}
*{box-sizing:border-box}
body{margin:0;font:17px/1.7 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--ink);background:var(--bg)}
.wrap{max-width:720px;margin:0 auto;padding:0 20px}
header.site{border-bottom:1px solid var(--line);padding:22px 0}
header.site a{color:var(--ink);text-decoration:none;font-weight:700;font-size:20px}
header.site .tag{color:var(--muted);font-size:14px;margin-top:4px}
h1{font-size:30px;line-height:1.25;margin:28px 0 6px}
.meta{color:var(--muted);font-size:14px;margin-bottom:24px}
article p{margin:0 0 18px}
.cat{display:inline-block;font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:var(--accent);font-weight:700}
.card{display:block;padding:18px 0;border-bottom:1px solid var(--line);text-decoration:none;color:inherit}
.card h2{font-size:20px;margin:6px 0 4px}
.card p{color:var(--muted);font-size:15px;margin:0}
.group h3{margin:34px 0 8px;font-size:15px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}
footer{border-top:1px solid var(--line);margin-top:48px;padding:24px 0;color:var(--muted);font-size:14px}
.back{display:inline-block;margin:24px 0;color:var(--accent);text-decoration:none}
"""


def page_head(title, desc, url, is_article):
    t = html.escape(title)
    d = html.escape(desc)
    og_type = "article" if is_article else "website"
    return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{t}</title>
<meta name="description" content="{d}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
<meta property="og:url" content="{url}">
<meta property="og:site_name" content="{html.escape(SITE_NAME)}">
<meta name="twitter:card" content="summary_large_image">
<style>{CSS}</style>
</head><body>
<header class="site"><div class="wrap"><a href="{BASE_URL}/">{html.escape(SITE_NAME)}</a>
<div class="tag">{html.escape(SITE_TAGLINE)}</div></div></header>
<div class="wrap">"""


FOOT = f"""</div><footer><div class="wrap">© {datetime.date.today().year} {html.escape(SITE_NAME)} · Written by {html.escape(AUTHOR)} ·
Day trips to Takaoka & Toyama from Kanazawa (Hokuriku Shinkansen).</div></footer></body></html>"""


def render_article(a):
    url = f"{BASE_URL}/{a['slug']}/"
    body = "\n".join(f"<p>{html.escape(p)}</p>" for p in a["paras"])
    ld = (
        '<script type="application/ld+json">{'
        '"@context":"https://schema.org","@type":"Article",'
        f'"headline":{_j(a["title"])},"description":{_j(a["desc"])},'
        f'"datePublished":{_j(a["date"])},"author":{{"@type":"Person","name":{_j(AUTHOR)}}},'
        f'"publisher":{{"@type":"Organization","name":{_j(SITE_NAME)}}},'
        f'"mainEntityOfPage":{_j(url)}'
        '}</script>'
    )
    return (page_head(a["title"], a["desc"], url, True) + ld +
            f'<span class="cat">{html.escape(a["cat"])}</span>'
            f'<h1>{html.escape(a["title"])}</h1>'
            f'<div class="meta">{a["date"]} · {html.escape(SITE_NAME)}</div>'
            f'<article>{body}</article>'
            f'<a class="back" href="{BASE_URL}/">← All stories</a>' + FOOT)


def _j(s: str) -> str:
    import json
    return json.dumps(s, ensure_ascii=False)


def render_index(arts):
    url = f"{BASE_URL}/"
    groups = {}
    for a in arts:
        groups.setdefault(a["cat"], []).append(a)
    order = ["Doraemon & Fujiko", "Places & Culture", "Food & Drink"]
    parts = [page_head(
        f"{SITE_NAME} — {SITE_TAGLINE}",
        "Hidden day trips to Takaoka and Toyama from Kanazawa: the real hometown of Doraemon, "
        "craft towns, World Heritage villages, and the food of the Sea of Japan.",
        url, False)]
    parts.append(f"<h1>{html.escape(SITE_NAME)}</h1>")
    parts.append(f'<p class="meta">{html.escape(SITE_TAGLINE)}. '
                 'Fifteen minutes from Kanazawa by Hokuriku Shinkansen — and almost no crowds.</p>')
    for cat in order:
        items = groups.get(cat, [])
        if not items:
            continue
        parts.append(f'<div class="group"><h3>{html.escape(cat)}</h3>')
        for a in items:
            parts.append(
                f'<a class="card" href="{BASE_URL}/{a["slug"]}/">'
                f'<span class="cat">{html.escape(a["cat"])}</span>'
                f'<h2>{html.escape(a["title"])}</h2>'
                f'<p>{html.escape(a["desc"])}</p></a>')
        parts.append("</div>")
    parts.append(FOOT)
    return "".join(parts)


def render_sitemap(arts):
    today = datetime.date.today().isoformat()
    urls = [f"{BASE_URL}/"] + [f"{BASE_URL}/{a['slug']}/" for a in arts]
    body = "".join(
        f"<url><loc>{u}</loc><lastmod>{today}</lastmod></url>" for u in urls)
    return ('<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f"{body}</urlset>")


def main():
    arts = collect()
    OUT.mkdir(parents=True, exist_ok=True)
    # index
    (OUT / "index.html").write_text(render_index(arts), encoding="utf-8")
    # articles（/slug/index.html でクリーンURL）
    for a in arts:
        d = OUT / a["slug"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(render_article(a), encoding="utf-8")
    # sitemap / robots
    (OUT / "sitemap.xml").write_text(render_sitemap(arts), encoding="utf-8")
    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n", encoding="utf-8")
    # .nojekyll（GitHub PagesでJekyll処理を無効化）
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    print(f"built {len(arts)} pages → {OUT}")
    print(f"BASE_URL = {BASE_URL}（独自ドメインは SITE_BASE_URL で上書き）")


if __name__ == "__main__":
    main()
