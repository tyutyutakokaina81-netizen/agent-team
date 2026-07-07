#!/usr/bin/env python3
"""AIツール記事(_drafts/*.md)を /ai-tools/ 用サイトHTMLに変換して配置。
アフィリ開示は本文に既存。CTAは data-aff（aff-links.jsがURL設定時のみ表示・未設定は非表示）。
使い方: python3 apps/ai-tools-guide/deploy_ai_pages.py <slug1> <slug2> ...
"""
import re, sys, html
from pathlib import Path

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


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    return s


def tool_for(slug):
    for k, v in TOOLS.items():
        if k in slug:
            return v
    return None


def md_to_html(body, tool):
    out, in_ul, cta_done = [], False, False
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
        # CTA line (#aff placeholder等) → data-aff button（未設定なら非表示）
        if not cta_done and ("#aff" in ln or re.search(r"try |get started|check .*price|visit ", low)):
            label = re.sub(r"\(#aff\)|\[|\]|\(|\)", "", ln).strip() or "Check the latest plans"
            da = f' data-aff="{tool}"' if tool else ''
            out.append(f'<a class="cta"{da} href="#">{inline(label)}</a>')
            cta_done = True; continue
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


if __name__ == "__main__":
    made = [convert(s) for s in sys.argv[1:]]
    print(f"生成 {len(made)}ページ → apps/ai-tools-guide/")
