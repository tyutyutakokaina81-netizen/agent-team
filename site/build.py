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
import shutil
import datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "CMO" / "outputs"
OUT = ROOT / "site" / "public"
OG_SRC = ROOT / "site" / "og"          # OG画像の置き場（コミット対象・フリー画像を配置）
OG_EXTS = (".jpg", ".jpeg", ".png", ".webp")


def og_image_for(slug: str):
    """site/og/<slug>.* があればそのURL、無ければ default.*、それも無ければ None。"""
    if not OG_SRC.exists():
        return None
    for stem in (slug, "default"):
        for ext in OG_EXTS:
            if (OG_SRC / f"{stem}{ext}").exists():
                return f"{BASE_URL}/og/{stem}{ext}"
    return None

# ---- サイト設定（オーナーは独自ドメインに差し替え可） ----
SITE_NAME = os.environ.get("SITE_NAME") or "Hidden Hokuriku"
SITE_TAGLINE = "Takaoka, Toyama & the real hometown of Doraemon — day trips from Kanazawa"
BASE_URL = (os.environ.get("SITE_BASE_URL") or "https://example.github.io").rstrip("/")
AUTHOR = "A Takaoka resident"

# ---- 収益化・計測・拡散の設定（env で差し替え可。未設定なら安全に省略/プレースホルダ） ----
PAID_GUIDE_URL = os.environ.get("PAID_GUIDE_URL", "")        # 有料ガイド(note/Gumroad)のURL
NEWSLETTER_URL = os.environ.get("NEWSLETTER_URL", "")        # メール登録(Substack/Buttondown)
ANALYTICS_DOMAIN = os.environ.get("ANALYTICS_DOMAIN", "")    # Plausible のドメイン
AFFIL = {  # 旅行アフィリ（登録後にenvで実URLへ差替。未設定はリンクなしで文だけ）
    "klook": os.environ.get("KLOOK_URL", ""),
    "booking": os.environ.get("BOOKING_URL", ""),
    "jalan": os.environ.get("JALAN_URL",
        "https://px.a8.net/svt/ejp?a8mat=1CCUH0+929KAA+14CS+64RJ5&a8ejpredirect=https%3A%2F%2Fwww.jalan.net%2Fken%2Fjapan_160000%2F"),
}


def analytics_tag() -> str:
    if not ANALYTICS_DOMAIN:
        return ""
    return (f'<script defer data-domain="{html.escape(ANALYTICS_DOMAIN)}" '
            'src="https://plausible.io/js/script.js"></script>')


def cta_block() -> str:
    """各記事末尾の収益化＋メール登録ブロック（景表法のPR表記つき）。"""
    links = []
    if AFFIL["klook"]:
        links.append(f'<a href="{AFFIL["klook"]}" rel="sponsored nofollow">JR passes & tours (Klook)</a>')
    if AFFIL["booking"]:
        links.append(f'<a href="{AFFIL["booking"]}" rel="sponsored nofollow">Hotels (Booking.com)</a>')
    if AFFIL["jalan"]:
        links.append(f'<a href="{AFFIL["jalan"]}" rel="sponsored nofollow">Stay near Takaoka (Jalan)</a>')
    paid = (f'<p><a class="cta" href="{PAID_GUIDE_URL}">Get the complete day-trip guide →</a></p>'
            if PAID_GUIDE_URL else "")
    mail = (f'<p>Like quiet corners of Japan? <a href="{NEWSLETTER_URL}">Get new stories by email →</a></p>'
            if NEWSLETTER_URL else "")
    plan = (f'<p class="plan">Plan the trip: {" · ".join(links)}</p>' if links else "")
    if not (paid or mail or plan):
        return ""
    disc = '<p class="disc">Some links are affiliate links; bookings help support this site at no cost to you.</p>'
    return f'<div class="cta-box">{paid}{plan}{mail}{disc}</div>'


# 分類用キーワード
FOOD_KW = ["寿司", "ブラック", "かまぼこ", "ホタルイカ", "へしこ", "豆腐", "地酒", "和菓子",
           "黒造り", "うどん", "地ビール", "昆布", "わかめ", "おでん", "干物", "せんべい",
           "ノドグロ", "フクラギ", "鮎", "バイ貝", "ゲンゲ", "岩がき", "素麺", "白えび",
           "唐揚", "コロッケ", "そば", "牛", "山菜", "大根", "ぶり"]
DORAEMON_KW = ["ドラえもん", "藤子", "Doraemon", "笑ゥせぇるすまん", "潮風ギャラリー"]
# 場所・文化（観光面）。これら or FOOD or DORAEMON に該当する記事だけサイトに載せる
# （フリーランス/AI/ひとり仕事 等の国内向け記事は travel SEO の topic を薄めるので除外）
PLACE_KW = ["高岡", "富山", "氷見", "越中", "五箇山", "雨晴", "新湊", "砺波", "井波", "八尾",
            "庄川", "二上", "瑞龍寺", "勝興寺", "大仏", "古城", "万葉線", "倶利伽羅", "称名滝",
            "立山", "銅器", "漆器", "和紙", "彫刻", "山町筋", "市場", "海岸", "観光地",
            "白川郷", "合掌", "峠", "駅", "御清水", "大門", "青貝"]

# 「For English readers」形式で抽出タイトルが文の途中になる地元記事へ、SEO向けの整題を割当
TITLE_MAP = {
    "おとぎの森公園_世界が会いに来ていた": "Otogi-no-Mori Park: Where the World Comes to Meet Doraemon",
    "高岡おとぎの森公園_藤子F不二雄のふるさと": "Doraemon's Hometown Park: Otogi-no-Mori, Takaoka",
    "高岡の職人に学ぶ個人で稼ぐ力": "Lessons from Takaoka's 400-Year Metal Craftsmen",
    "雨晴駅_海と山が並ぶ場所": "Amaharashi Station: Where the Sea Meets 3,000-Metre Peaks",
    "白えび丼_富山湾の宝石": "Shiraebi Donburi: Toyama Bay's Translucent White Shrimp",
    "高岡コロッケ_鋳物の町のB級グルメ": "Takaoka Korokke: The Croquette of Japan's Metal-Casting Town",
    "昆布じめ_刺身を昆布で寝かせる文化": "Konbu-jime: Toyama's Kelp-Cured Sashimi Tradition",
    "新湊きっときと市場の朝": "Shinminato Market: Toyama Bay Fish, Same-Day Fresh",
    "観光地に住んでいるということ": "Living in a Tourist Town: A Resident's View of Takaoka",
    "雨晴海岸の早朝散歩": "Amaharashi Coast at Dawn: Toyama's Sea-and-Mountains View",
    "瑞龍寺_国宝のなかで職人は祈っていた": "Zuiryuji: A National-Treasure Zen Temple in Takaoka",
    "おとぎの森の初夏_ドラえもん広場": "Otogi-no-Mori in Early Summer: Takaoka's Doraemon Square",
    "笑ゥせぇるすまん_大人になって会いに行く": "Warau Salesman: Himi, Home of the 'Other' Fujiko",
}


def is_travel(name: str) -> bool:
    return any(k in name for k in (FOOD_KW + DORAEMON_KW + PLACE_KW))


def title_override(name: str) -> str | None:
    for key, val in TITLE_MAP.items():
        if key in name:
            return val
    return None


def slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s-]+", "-", s).strip("-")
    return s[:70] or "article"


def _paragraphs(block: str):
    """空行区切りで段落配列にする。"""
    paras, cur = [], []
    for ln in block.splitlines():
        if ln.strip():
            cur.append(ln.strip())
        else:
            if cur:
                paras.append(" ".join(cur)); cur = []
    if cur:
        paras.append(" ".join(cur))
    return paras


def extract_english(text: str):
    """note記事から英語の (title, [paragraphs]) を返す。2書式に対応。無ければ None。
    (A) 「## English」コードブロック：先頭行=タイトル、残り=本文。
    (B) 「(🌏) For English readers」：以降〜コードブロック閉じ までを英語本文とし、
        英語タイトルが無いので先頭文からタイトルを生成。
    """
    # (A) ## English ブロック
    m = re.search(r"^##\s*English[^\n]*\n+```\n(.+?)\n```", text, re.S | re.M)
    if m:
        lines = [ln.rstrip() for ln in m.group(1).strip().splitlines()]
        title, rest = "", 0
        for i, ln in enumerate(lines):
            if ln.strip():
                title, rest = ln.strip(), i + 1
                break
        paras = _paragraphs("\n".join(lines[rest:]))
        if title and paras:
            return title, paras
        return None
    # (B) For English readers 形式（本文コードブロック内に英語が混在）
    m2 = re.search(r"(?:🌏\s*)?For English readers\b", text)
    if m2:
        tail = text[m2.end():].split("\n```")[0]  # 本文ブロックの閉じ ``` まで
        paras = _paragraphs(tail)
        if paras:
            first = paras[0]
            title = re.split(r"(?<=[.!?])\s", first)[0].strip()[:70] or first[:60]
            return title, paras
    return None


def category_of(name: str) -> str:
    if any(k in name for k in DORAEMON_KW):
        return "Doraemon & Fujiko"
    if any(k in name for k in FOOD_KW):
        return "Food & Drink"
    return "Places & Culture"


def collect():
    arts = []
    for p in sorted(SRC.glob("*_note記事_*.md")):
        # 旅行/地元コンテンツに絞る（国内向け実務記事はtravel SEOのtopicを薄めるので除外）
        if not is_travel(p.name):
            continue
        text = p.read_text(encoding="utf-8")
        en = extract_english(text)
        if not en:
            continue
        title, paras = en
        # SEO向けの整題があれば優先
        title = title_override(p.name) or title
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
.related{margin:40px 0 8px;padding-top:20px;border-top:1px solid var(--line)}
.related h3{margin:0 0 10px;font-size:14px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
.related .rel{display:block;padding:8px 0;color:var(--accent);text-decoration:none;font-size:16px}
.hero{margin:26px 0 30px;padding:22px;background:#f6f8fc;border:1px solid var(--line);border-radius:10px}
.hero p{margin:0 0 12px;font-size:16px}
.hero a.cta{display:inline-block;background:var(--accent);color:#fff;padding:10px 16px;border-radius:8px;text-decoration:none;font-weight:600}
.cta-box{margin:36px 0 8px;padding:18px;background:#f6f8fc;border:1px solid var(--line);border-radius:10px}
.cta-box a.cta{display:inline-block;background:var(--accent);color:#fff;padding:9px 15px;border-radius:8px;text-decoration:none;font-weight:600}
.cta-box .plan a{color:var(--accent);text-decoration:none}.cta-box .disc{color:var(--muted);font-size:12px;margin:8px 0 0}
.hubnav{margin:10px 0 0;font-size:14px}.hubnav a{color:var(--accent);text-decoration:none;margin-right:14px}
.langnav{margin:14px 0;font-size:14px;color:var(--muted)}.langnav a{color:var(--accent);text-decoration:none;margin-right:10px}
"""


def page_head(title, desc, url, is_article, image=None, lang="en", extra_head=""):
    t = html.escape(title)
    d = html.escape(desc)
    og_type = "article" if is_article else "website"
    img_tags = ""
    if image:
        img_tags = (f'<meta property="og:image" content="{image}">'
                    f'<meta name="twitter:image" content="{image}">')
    return f"""<!doctype html><html lang="{lang}"><head>{extra_head}
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{t}</title>
<meta name="description" content="{d}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
<meta property="og:url" content="{url}">
<meta property="og:site_name" content="{html.escape(SITE_NAME)}">
{img_tags}
<meta name="twitter:card" content="summary_large_image">
{analytics_tag()}
<style>{CSS}</style>
</head><body>
<header class="site"><div class="wrap"><a href="{BASE_URL}/">{html.escape(SITE_NAME)}</a>
<div class="tag">{html.escape(SITE_TAGLINE)}</div></div></header>
<div class="wrap">"""


FOOT = f"""</div><footer><div class="wrap">© {datetime.date.today().year} {html.escape(SITE_NAME)} · Written by {html.escape(AUTHOR)} ·
Day trips to Takaoka & Toyama from Kanazawa (Hokuriku Shinkansen).</div></footer></body></html>"""


def render_article(a, related=None):
    url = f"{BASE_URL}/{a['slug']}/"
    body = "\n".join(f"<p>{html.escape(p)}</p>" for p in a["paras"])
    rel_html = ""
    if related:
        cards = "".join(
            f'<a class="rel" href="{BASE_URL}/{r["slug"]}/">{html.escape(r["title"])}</a>'
            for r in related)
        rel_html = f'<div class="related"><h3>Related stories</h3>{cards}</div>'
    ld = (
        '<script type="application/ld+json">{'
        '"@context":"https://schema.org","@type":"Article",'
        f'"headline":{_j(a["title"])},"description":{_j(a["desc"])},'
        f'"datePublished":{_j(a["date"])},"author":{{"@type":"Person","name":{_j(AUTHOR)}}},'
        f'"publisher":{{"@type":"Organization","name":{_j(SITE_NAME)}}},'
        f'"mainEntityOfPage":{_j(url)}'
        '}</script>'
    )
    return (page_head(a["title"], a["desc"], url, True, og_image_for(a["slug"])) + ld +
            f'<span class="cat">{html.escape(a["cat"])}</span>'
            f'<h1>{html.escape(a["title"])}</h1>'
            f'<div class="meta">{a["date"]} · {html.escape(SITE_NAME)}</div>'
            f'<article>{body}</article>' + cta_block() + rel_html +
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
        url, False, og_image_for("default"))]
    parts.append(f"<h1>{html.escape(SITE_NAME)}</h1>")
    parts.append(f'<p class="meta">{html.escape(SITE_TAGLINE)}. '
                 'Fifteen minutes from Kanazawa by Hokuriku Shinkansen — and almost no crowds.</p>')
    lead = next((a for a in arts if a["slug"].startswith("skip-shirakawa-go")), None)
    if lead:
        parts.append(
            '<div class="hero"><p><strong>Staying in Kanazawa?</strong> Most travelers spend day two '
            "on the packed bus to Shirakawa-go. There's an easier trip almost no guide writes about: "
            'the real hometown of Doraemon, 15 minutes away by Shinkansen — no reservation, almost no crowds.</p>'
            f'<a class="cta" href="{BASE_URL}/{lead["slug"]}/">Start here → the Doraemon day trip</a></div>')
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
    # 出力先をクリーンしてから生成（除外・改題した古いページを残さない）
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    # index
    (OUT / "index.html").write_text(render_index(arts), encoding="utf-8")
    # articles（/slug/index.html でクリーンURL）＋同カテゴリの関連記事リンク（内部SEO/回遊）
    by_cat = {}
    for a in arts:
        by_cat.setdefault(a["cat"], []).append(a)
    for a in arts:
        siblings = by_cat[a["cat"]]
        i = siblings.index(a)
        rest = [x for x in (siblings[i + 1:] + siblings[:i]) if x["slug"] != a["slug"]]
        related = rest[:3]
        d = OUT / a["slug"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(render_article(a, related), encoding="utf-8")
    # OG画像（site/og/*.jpg|png|webp）を公開ディレクトリへコピー
    if OG_SRC.exists():
        dst = OUT / "og"
        dst.mkdir(parents=True, exist_ok=True)
        n = 0
        for f in OG_SRC.iterdir():
            if f.suffix.lower() in OG_EXTS:
                shutil.copy2(f, dst / f.name); n += 1
        if n:
            print(f"copied {n} OG image(s) → /og/")
    # sitemap / robots
    (OUT / "sitemap.xml").write_text(render_sitemap(arts), encoding="utf-8")
    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n", encoding="utf-8")
    # .nojekyll（GitHub PagesでJekyll処理を無効化）
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    # 既存の tavern.html を /tavern/ に退避して共存（オーナー指示：英語=トップ／tavern=/tavern）
    tavern = ROOT / "tavern.html"
    if tavern.exists():
        td = OUT / "tavern"
        td.mkdir(parents=True, exist_ok=True)
        (td / "index.html").write_text(tavern.read_text(encoding="utf-8"), encoding="utf-8")
        print("preserved tavern.html → /tavern/")
    print(f"built {len(arts)} pages → {OUT}")
    print(f"BASE_URL = {BASE_URL}（独自ドメインは SITE_BASE_URL で上書き）")


if __name__ == "__main__":
    main()
