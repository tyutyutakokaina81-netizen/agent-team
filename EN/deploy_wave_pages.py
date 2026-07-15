#!/usr/bin/env python3
"""検証合格した wave の Markdown を、toyama-guide のサイトHTMLテンプレートに変換して配置する。
出力: apps/toyama-guide/en-<slug>.html （pages.yml が /toyama/ で世界公開）
- 既存ページと同じ head/構造/CSS/affiliates.js を踏襲（2出口: アフィリjs + 電子書籍CTA）。
- Markdownの見出し/段落/箇条書き/太字/リンクを最小変換。Fact-check note は枠で表示。
使い方: python3 EN/deploy_wave_pages.py <wave_dir> <slug1> <slug2> ...
"""
import re, sys, html
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GUIDE = REPO / "apps" / "toyama-guide"
BASE = "https://tyutyutakokaina81-netizen.github.io/agent-team/toyama"

HEAD = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} | Toyama Local Guide</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="article">
<meta property="og:url" content="{base}/en-{slug}.html">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">
<meta property="og:site_name" content="Toyama Local Guide">
<meta property="og:locale" content="en_US">
<link rel="canonical" href="{base}/en-{slug}.html">
<link rel="alternate" hreflang="en" href="{base}/en-{slug}.html">
<link rel="alternate" hreflang="ja" href="{base}/index.html">
<link rel="alternate" hreflang="x-default" href="{base}/en-{slug}.html">
<meta name="twitter:card" content="summary_large_image">
<style>
  body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:#1d2a2a;line-height:1.85;max-width:740px;margin:0 auto;padding:32px 20px 70px}}
  h1{{font-size:27px;line-height:1.35}}h2{{font-size:20px;margin-top:30px;color:#1f6b58}}
  p,li{{color:#33403f;font-size:16px}}a{{color:#1f8a70}}
  .pr{{font-size:12.5px;color:#5b6a6a;background:#fffbe6;border:1px solid #f0e6b0;border-radius:8px;padding:8px 12px;margin:14px 0}}
  .fc{{font-size:14.5px;color:#33403f;background:#f2f8f5;border:1px solid #cfe6dc;border-radius:8px;padding:10px 14px;margin:18px 0}}
  .ebook{{display:block;background:#0f3d2e;color:#fff;text-decoration:none;font-weight:700;padding:13px 18px;border-radius:10px;margin:20px 0;font-size:15px}}
  .muted{{color:#5b6a6a;font-size:14px}}.tag{{color:#5b6a6a;font-size:13px}}.lang{{font-size:13px}}
</style>
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"Article","headline":"{title}","inLanguage":"en","url":"{base}/en-{slug}.html","publisher":{{"@type":"Organization","name":"Toyama Local Guide"}}}}</script>
<script defer src="/agent-team/analytics.js"></script>
</head>
<body>
<p class="lang"><a href="index.html">日本語トップ</a> · <a href="en.html">English guide</a></p>
<p class="tag">Travel · Toyama · A local's guide</p>
'''

FOOT = '''<p class="tag"><a href="en.html">Toyama Local Guide home →</a> · <a href="en-itinerary.html">Itineraries →</a> · <a href="en-things-to-do.html">Things to do →</a></p>
<script defer src="/agent-team/toyama/affiliates.js"></script>
<!-- reader-follow-block -->
<p class="muted" style="margin-top:26px">Written by a local. Conditions change — always confirm current prices, times and access on official sources before you travel. No specific private addresses are listed.</p>
</body>
</html>
'''


def inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    return s


def md_to_html(body: str, slug: str):
    lines = body.split("\n")
    out, i, in_ul = [], 0, False
    ebook_done = False
    def close_ul():
        nonlocal in_ul
        if in_ul: out.append("</ul>"); in_ul=False
    for raw in lines:
        ln = raw.rstrip()
        if not ln.strip():
            close_ul(); continue
        # Fact-check note block
        if re.match(r"#{1,4}\s*Fact.?check", ln, re.I) or ln.strip().lower().startswith("fact-check note"):
            close_ul(); out.append('<div class="fc"><strong>Fact-check note</strong><br>');
            out.append("<!--FC-->"); continue
        m = re.match(r"^(#{2,4})\s+(.*)", ln)
        if m:
            close_ul(); out.append(f"<h2>{inline(m.group(2))}</h2>"); continue
        if re.match(r"^\s*[-*]\s+", ln):
            if not in_ul: out.append("<ul>"); in_ul=True
            item = re.sub(r"^\s*[-*]\s+", "", ln)
            out.append(f"<li>{inline(item)}</li>"); continue
        close_ul()
        # ebook CTA line → styled button
        if re.search(r"Kindle|Uncrowded Coast|whole guide", ln, re.I) and not ebook_done:
            out.append(f'<a class="ebook" href="#get-the-book">📘 {inline(ln.strip())}</a>')
            ebook_done=True; continue
        out.append(f"<p>{inline(ln.strip())}</p>")
    close_ul()
    h = "\n".join(out)
    # Fact-check: 開いたdivを閉じる（次のh2/末尾で）
    h = h.replace("<!--FC-->", "")
    if '<div class="fc">' in h and h.count("</div>") < h.count('<div class="fc">'):
        h += "</div>"
    return h


def convert(wave_dir: Path, slug: str):
    md = (wave_dir / f"{slug}.md").read_text(encoding="utf-8")
    m = re.match(r"^#\s+(.*)", md.strip())
    title = (m.group(1).strip() if m else slug.replace("-", " ").title())
    body = md.strip()
    if m: body = body[body.index("\n"):] if "\n" in body else ""
    # description = 最初の実段落
    firstp = ""
    for ln in body.split("\n"):
        t = ln.strip()
        if t and not t.startswith("#") and not t.startswith("-"):
            firstp = re.sub(r"[*\[\]]", "", t); break
    desc = html.escape(firstp[:155], quote=True)
    tt = html.escape(title, quote=True)
    page = HEAD.format(title=tt, desc=desc, slug=slug, base=BASE) + \
        f"<h1>{html.escape(title, quote=False)}</h1>\n" + md_to_html(body, slug) + "\n" + FOOT
    (GUIDE / f"en-{slug}.html").write_text(page, encoding="utf-8")
    return f"en-{slug}.html"


def _topic_tokens(title: str) -> set:
    """題材トークン抽出（重複ゲート用・日英対応）"""
    stop = {"富山","高岡","氷見","富山県","富山市","高岡市","氷見市","富山湾","北陸","保存版","ガイド",
            "toyama","takaoka","himi","japan","guide","travel","the","and","for","with","how","best","your",
            "worth","stop","season","day","days","tips","near","from","food","eat","see","visit","trip","area",
            "place","spot","cost","price","time","way","get","when","where","what","which","around","local",
            "honest","actually","really","things","that","this","you","are","was","its","not","but","real"}
    toks = set()
    for seg in re.split(r"[、。，．,\.\s・「」『』【】\[\]（）()＝=＋+\-—–~〜…!！?？:：;；|｜/／']+", title or ""):
        seg = seg.strip().lower()
        if len(seg) < 3 or seg in stop:
            continue
        if re.search(r"[一-鿿ァ-ヶ]", seg) or (seg.isalpha() and len(seg) >= 4):
            toks.add(seg)
    return toks


def _existing_index(exclude):
    files, tokens = set(), set()
    for p in GUIDE.glob("en-*.html"):
        stem = p.stem[3:]
        if stem in exclude:
            continue
        files.add(stem)
        m = re.search(r"<h1>(.*?)</h1>", p.read_text(encoding="utf-8"), re.S)
        if m:
            tokens |= _topic_tokens(re.sub("<[^>]+>", "", m.group(1)))
    return files, tokens


def main():
    wave_dir = Path(sys.argv[1])
    slugs = sys.argv[2:]
    # ★必須の重複ゲート（2026-07-07 再発防止）: 既存全ページとファイル名/題材トークンで照合、衝突は公開しない
    ex_files, ex_tokens = _existing_index(set(slugs))
    seen = set(ex_tokens)
    made, skipped = [], []
    for s in slugs:
        md = wave_dir / f"{s}.md"
        if not md.exists():
            skipped.append((s, "md無")); continue
        if s in ex_files:
            skipped.append((s, "ファイル名衝突")); continue
        m = re.match(r"^#\s+(.*)", md.read_text(encoding="utf-8").strip())
        tok = _topic_tokens(m.group(1) if m else s)
        if tok & seen:
            skipped.append((s, "題材重複:" + "・".join(sorted(tok & seen))[:30])); continue
        try:
            made.append(convert(wave_dir, s)); seen |= tok
        except Exception as e:
            skipped.append((s, str(e)[:80]))
    print(f"生成 {len(made)}ページ（重複ゲート通過のみ）→ apps/toyama-guide/")
    for f in made: print("  ", f)
    if skipped:
        print(f"スキップ {len(skipped)}件（重複/欠損）:")
        for s, r in skipped: print(f"   ✗ {s}: {r}")


if __name__ == "__main__":
    main()
