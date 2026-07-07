#!/usr/bin/env python3
"""英語49ページから Amazon KDP / Gumroad 用の電子書籍原稿(Markdown)を組み上げる。
世界向け"売れるスキーム"の中核商品。制作コスト¥0（既存資産の再パッケージ）。

出力: EN/outputs/kindle/Toyama_Uncrowded_Coast_manuscript.md
- ナビ/フッター/アフィリ/PR表記/免責の段落は除外し、読み物本文だけを抽出。
- ガイドブックの論理順（導入→行き方→季節→街→食→実用→行程）に並べ替え。
"""
import re
from pathlib import Path

GUIDE = Path(__file__).resolve().parent.parent / "apps" / "toyama-guide"
OUT = Path(__file__).resolve().parent / "outputs" / "kindle"
OUT.mkdir(parents=True, exist_ok=True)

# 章立て（curated order）: (章タイトル, [en-*.html のstem...])
CHAPTERS = [
    ("Why Toyama — Japan Beyond the Golden Route",
        ["en-worth-visiting", "en-off-beaten-path", "en-vs-kanazawa", "en-is-toyama-safe"]),
    ("Getting There & Around",
        ["en-access", "en-rail-pass", "en-getting-around", "en-car-rental"]),
    ("When to Go",
        ["en-when-to-go", "en-how-many-days", "en-spring", "en-summer", "en-autumn", "en-winter"]),
    ("Toyama City & the Coast",
        ["en-toyama-city", "en-glass-art", "en-amaharashi", "en-himi"]),
    ("Takaoka — Craft, Temples & Doraemon",
        ["en-takaoka", "en-zuiryuji", "en-doraemon", "en-manga-pilgrimage", "en-hattori"]),
    ("The Mountains — Alps, Gorges & Falls",
        ["en-alpine", "en-alpine-cost", "en-kurobe-gorge", "en-shomyo-falls", "en-gokayama", "en-shirakawa-go"]),
    ("Food of the Bay & Table",
        ["en-food", "en-crab", "en-shiroebi", "en-firefly-squid", "en-masuzushi",
         "en-toyama-black", "en-onigiri-kelp", "en-sake"]),
    ("Practical Matters",
        ["en-where-to-stay", "en-money", "en-sim-wifi", "en-what-to-wear",
         "en-budget", "en-with-kids", "en-onsen", "en-faq"]),
    ("Itineraries",
        ["en-itinerary", "en-days-2-3", "en-daytrip", "en-things-to-do"]),
]

SKIP_PARA = re.compile(
    r"日本語|English guide|affiliate|advertising|This page is reader|"
    r"No specific private addresses|is not professional|"
    r"Follow on note|Toyama Local Guide home|→</a>|class=\"pr\"|class=\"muted\"|class=\"tag\""
)


def clean(html_frag: str) -> str:
    s = re.sub(r"<a\b[^>]*>(.*?)</a>", r"\1", html_frag, flags=re.S)  # リンクはテキスト化
    s = re.sub(r"<[^>]+>", "", s)  # 残りタグ除去
    s = re.sub(r"&amp;", "&", s); s = re.sub(r"&nbsp;", " ", s)
    s = re.sub(r"&#8217;|&rsquo;", "'", s); s = re.sub(r"&#8212;|&mdash;", "—", s)
    return s.strip()


def extract(stem: str):
    p = GUIDE / f"{stem}.html"
    if not p.exists():
        return None
    t = p.read_text(encoding="utf-8")
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", t, re.S)
    heading = clean(h1.group(1)) if h1 else stem
    # 本文: <h2> と <p> を出現順に拾う（nav/footer/pr は除外）
    blocks = re.findall(r"<(h2|p)[^>]*>(.*?)</\1>", t, re.S)
    lines = []
    for tag, frag in blocks:
        raw = frag
        if SKIP_PARA.search(raw):
            continue
        txt = clean(raw)
        if not txt or len(txt) < 25 and tag == "p":
            continue
        lines.append(("## " + txt) if tag == "h2" else txt)
    return heading, lines


def main():
    md = [
        "# Toyama: Japan's Uncrowded Coast",
        "### A Local's Guide to Takaoka, Himi & the Sea-of-Japan Side of the Alps",
        "",
        "*Written by a resident. Fact-checked. For travelers going beyond Tokyo and Kyoto.*",
        "",
        "---", "",
    ]
    n_pages = 0
    for ch_title, stems in CHAPTERS:
        md.append(f"# {ch_title}\n")
        for stem in stems:
            r = extract(stem)
            if not r:
                continue
            heading, lines = r
            if not lines:
                continue
            n_pages += 1
            md.append(f"## {heading}\n")
            md.extend(l + "\n" for l in lines)
        md.append("\n---\n")
    body = "\n".join(md)
    out = OUT / "Toyama_Uncrowded_Coast_manuscript.md"
    out.write_text(body, encoding="utf-8")
    words = len(re.findall(r"\w+", body))
    print(f"原稿を書き出し: {out}")
    print(f"収録ページ {n_pages} / 章 {len(CHAPTERS)} / 約{words:,} words（英語）")


if __name__ == "__main__":
    main()
