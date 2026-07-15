#!/usr/bin/env python3
"""AIツール記事(_drafts/*.md)を /ai-tools/ 用サイトHTMLに変換して配置。
アフィリ開示は本文に既存。CTAは data-aff（aff-links.jsがURL設定時のみ表示・未設定は非表示）。
使い方: python3 apps/ai-tools-guide/deploy_ai_pages.py <slug1> <slug2> ...
"""
import re, sys, html
from pathlib import Path
from datetime import date as _date

HERE = Path(__file__).resolve().parent
DRAFTS = HERE / "_drafts"
BASE = "https://tyutyutakokaina81-netizen.github.io/agent-team/ai-tools"

# slug内キーワード → aff-links.js の LINKS キー
TOOLS = {
    "jasper":"jasper","copy-ai":"copyai","copyai":"copyai","writesonic":"writesonic","pictory":"pictory",
    "speechify":"speechify","elevenlabs":"elevenlabs","tubebuddy":"tubebuddy","getresponse":"getresponse",
    "koala":"koala","semrush":"semrush","hostinger":"hostinger","nordvpn":"nordvpn","surfshark":"surfshark",
    "hubspot":"hubspot","notion":"notionai","descript":"descript","murf":"murf","synthesia":"synthesia",
    "grammarly":"grammarly","perplexity":"perplexity","crm":"hubspot","hosting":"hostinger","vpn":"nordvpn",
}

HEAD = '''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} | AI Tools Guide</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{title}"><meta property="og:description" content="{desc}">
<meta property="og:type" content="article"><meta property="og:url" content="{base}/{slug}.html">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">
<link rel="canonical" href="{base}/{slug}.html">
<style>
  body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:#1d2a2a;line-height:1.85;max-width:740px;margin:0 auto;padding:32px 20px 70px}}
  h1{{font-size:27px;line-height:1.35}}h2{{font-size:20px;margin-top:30px;color:#1f6b58}}
  p,li{{color:#33403f;font-size:16px}}a{{color:#1f8a70}}
  .pr{{font-size:12.5px;color:#5b6a6a;background:#fffbe6;border:1px solid #f0e6b0;border-radius:8px;padding:8px 12px;margin:14px 0}}
  .cta{{display:inline-block;background:#0f3d2e;color:#fff;text-decoration:none;font-weight:700;padding:12px 18px;border-radius:10px;margin:16px 0;font-size:15px}}
  .aff{{font-weight:700}}
  .muted{{color:#5b6a6a;font-size:14px}}.tag{{color:#5b6a6a;font-size:13px}}
</style>
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"Article","headline":"{title}","inLanguage":"en","url":"{base}/{slug}.html","publisher":{{"@type":"Organization","name":"AI Tools Guide"}}}}</script>
<script defer src="/agent-team/analytics.js"></script></head><body>
<p class="tag"><a href="index.html">AI Tools Guide</a> · Reviewed by an AI-operated company</p>
'''

FOOT = '''<p class="tag"><a href="index.html">More AI tool guides →</a></p>
<script defer src="/agent-team/ai-tools/aff-links.js"></script>
<p class="muted" style="margin-top:24px">We are an AI-operated company. We don't fake hands-on tests we didn't run. Prices and features change — verify on the official site before buying.</p>
</body></html>
'''


def aff_key_for(label):
    """CTAラベル文中のツール名から aff-links.js の LINKS キーを推定（slugより正確・複数ツール対応）。"""
    low = label.lower()
    for k, v in TOOLS.items():
        if k in low:
            return v
    return None


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    # アフィリCTAプレースホルダ [label](#aff) → data-aff付きリンク（aff-links.jsがURL設定時のみ有効化）。
    # ※本文段落を丸ごとボタン化していた旧ヒューリスティックの根本修正。CTAはこの明示マーカーだけが対象。
    def _aff(m):
        label = m.group(1)
        key = aff_key_for(label)
        da = f' data-aff="{key}"' if key else ''
        return f'<a class="aff"{da} href="#" rel="nofollow sponsored">{label}</a>'
    s = re.sub(r"\[([^\]]+)\]\(#aff\)", _aff, s)
    # 通常のマークダウンリンク
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    return s


def tool_for(slug):
    for k, v in TOOLS.items():
        if k in slug:
            return v
    return None


def md_to_html(body, tool):
    out, in_ul = [], False
    def close():
        nonlocal in_ul
        if in_ul: out.append("</ul>"); in_ul=False
    for raw in body.split("\n"):
        ln = raw.rstrip()
        if not ln.strip():
            close(); continue
        m = re.match(r"^(#{2,4})\s+(.*)", ln)
        if m:
            close(); out.append(f"<h2>{inline(m.group(2))}</h2>"); continue
        if re.match(r"^\s*[-*]\s+", ln):
            if not in_ul: out.append("<ul>"); in_ul=True
            item = re.sub(r"^\s*[-*]\s+", "", ln)
            out.append(f"<li>{inline(item)}</li>"); continue
        close()
        low = ln.lower()
        # affiliate disclosure → PR box
        if "affiliate" in low and ("commission" in low or "disclosure" in low):
            out.append(f'<p class="pr">{inline(ln.strip())}</p>'); continue
        # CTA は本文段落内の明示マーカー [label](#aff) だけが対象（inline() が data-aff リンク化）。
        # 旧: 本文中の "try/check price/visit" 等の語で行全体をボタン化＝段落がデッドボタン/非表示になる不具合 → 撤去。
        out.append(f"<p>{inline(ln.strip())}</p>")
    close()
    return "\n".join(out)


def convert(slug):
    md = (DRAFTS / f"{slug}.md").read_text(encoding="utf-8")
    m = re.match(r"^#\s+(.*)", md.strip())
    title = m.group(1).strip() if m else slug.replace("-", " ").title()
    body = md.strip()
    if m: body = body[body.index("\n"):]
    firstp = next((re.sub(r"[*\[\]]", "", l.strip()) for l in body.split("\n")
                   if l.strip() and not l.startswith("#") and not l.startswith("-")), "")
    desc = html.escape(firstp[:155], quote=True)
    page = HEAD.format(title=html.escape(title, quote=True), desc=desc, slug=slug, base=BASE) + \
        f"<h1>{html.escape(title, quote=False)}</h1>\n" + md_to_html(body, tool_for(slug)) + "\n" + FOOT
    (HERE / f"{slug}.html").write_text(page, encoding="utf-8")
    return f"{slug}.html"


def _page_title(p):
    h = p.read_text(encoding="utf-8")
    m = re.search(r"<h1>(.*?)</h1>", h, re.S)
    return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else p.stem


def rebuild_index():
    """index.html の記事一覧(<p id="index">)を全ページから再構築＝ハブから全記事に導通（発見性/内部SEO）。"""
    idx = HERE / "index.html"
    if not idx.exists():
        return 0
    pages = sorted(p for p in HERE.glob("*.html") if p.name != "index.html")
    items = "\n".join(f'<li><a href="{p.name}">{html.escape(_page_title(p))}</a></li>' for p in pages)
    ul = f'<ul id="index">\n{items}\n</ul>'
    h = idx.read_text(encoding="utf-8")
    new = re.sub(r'<(p|ul) id="index">.*?</\1>', ul, h, flags=re.S)
    idx.write_text(new, encoding="utf-8")
    return len(pages)


def sync_sitemap():
    """全 ai-tools ページを sitemap.xml に登録＝Google が発見できるように（未登録=クロール不能の穴を塞ぐ）。"""
    sm = HERE.parent / "ai-agency-hp" / "sitemap.xml"
    if not sm.exists():
        return 0
    txt = sm.read_text(encoding="utf-8")
    existing = set(re.findall(r"/ai-tools/([^<]+\.html)", txt))
    today = _date.today().isoformat()
    add = [p.name for p in sorted(HERE.glob("*.html")) if p.name not in existing]
    if add:
        lines = "".join(
            f"  <url><loc>{BASE}/{n}</loc><lastmod>{today}</lastmod><priority>0.7</priority></url>\n"
            for n in add)
        sm.write_text(txt.replace("</urlset>", lines + "</urlset>"), encoding="utf-8")
    return len(add)


if __name__ == "__main__":
    made = [convert(s) for s in sys.argv[1:]]
    n_idx = rebuild_index()
    n_sm = sync_sitemap()
    print(f"生成 {len(made)}ページ → apps/ai-tools-guide/｜index一覧={n_idx}本 更新｜sitemap新規登録={n_sm}件")
