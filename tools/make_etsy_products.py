# -*- coding: utf-8 -*-
"""Etsy商品の markdown(Print Content) → 実PDF＋表紙PNG を生成。
reportlab(PDF) + PIL(cover). 日本語フォント対応(フレーズ集)。A2準拠＝AI画像でなく確定レンダリング。"""
import os, re, glob, html
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image, ImageDraw, ImageFont

SRC = "CPO/outputs/etsy_japan"
PDF_DIR = f"{SRC}/pdf"
COVER_DIR = f"{SRC}/covers"
JP_FONT = "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"
os.makedirs(PDF_DIR, exist_ok=True); os.makedirs(COVER_DIR, exist_ok=True)

pdfmetrics.registerFont(TTFont("JP", JP_FONT))
pdfmetrics.registerFontFamily("JP", normal="JP", bold="JP", italic="JP", boldItalic="JP")

H1 = ParagraphStyle("H1", fontName="JP", fontSize=22, leading=27, textColor=colors.HexColor("#15705a"), spaceAfter=10)
H2 = ParagraphStyle("H2", fontName="JP", fontSize=14, leading=18, textColor=colors.HexColor("#1f6b58"), spaceBefore=10, spaceAfter=5)
BODY = ParagraphStyle("BODY", fontName="JP", fontSize=10.5, leading=15, textColor=colors.HexColor("#26302f"), spaceAfter=3)
BULLET = ParagraphStyle("BUL", parent=BODY, leftIndent=12)
CELL = ParagraphStyle("CELL", fontName="JP", fontSize=9, leading=12, textColor=colors.HexColor("#26302f"))

def esc(s):
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return s

def get_print_content(md):
    # "## Print Content" 以降を取る
    i = md.find("## Print Content")
    return md[i:] if i >= 0 else md

def build_pdf(slug, title, content):
    flow = []
    lines = content.splitlines()
    n = len(lines); i = 0
    first_page = True
    while i < n:
        ln = lines[i].rstrip()
        # テーブル検出
        if ln.strip().startswith("|") and "|" in ln.strip()[1:]:
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not re.match(r"^[\s:\-|]+$", lines[i].strip()):  # 区切り行除外
                    rows.append(cells)
                i += 1
            if rows:
                ncol = max(len(r) for r in rows)
                data = [[Paragraph(esc(c), CELL) for c in (r + [""]*(ncol-len(r)))] for r in rows]
                tw = A4[0] - 36*mm
                t = Table(data, colWidths=[tw/ncol]*ncol)
                t.setStyle(TableStyle([
                    ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#cfe0db")),
                    ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#e8f3ef")),
                    ("VALIGN",(0,0),(-1,-1),"TOP"),
                    ("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),
                    ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
                ]))
                flow.append(t); flow.append(Spacer(1,6))
            continue
        i += 1
        if not ln.strip():
            flow.append(Spacer(1,4)); continue
        m = re.match(r"^(Page\s+\d+\b.*)$", ln.strip())
        if m:
            if not first_page: flow.append(PageBreak())
            first_page = False
            flow.append(Paragraph(esc(m.group(1)), H1)); continue
        if ln.startswith("## "):
            flow.append(Paragraph(esc(ln[3:]), H2)); continue
        if ln.startswith("### "):
            flow.append(Paragraph(esc(ln[4:]), H2)); continue
        if ln.startswith("# "):
            flow.append(Paragraph(esc(ln[2:]), H1)); continue
        if re.match(r"^\s*-\s*\[\s*\]\s*", ln):
            flow.append(Paragraph("☐ " + esc(re.sub(r"^\s*-\s*\[\s*\]\s*","",ln)), BULLET)); continue
        if re.match(r"^\s*[-*]\s+", ln):
            flow.append(Paragraph("• " + esc(re.sub(r"^\s*[-*]\s+","",ln)), BULLET)); continue
        flow.append(Paragraph(esc(ln), BODY))
    out = f"{PDF_DIR}/{slug}.pdf"
    SimpleDocTemplate(out, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm,
                      topMargin=16*mm, bottomMargin=16*mm, title=title).build(flow)
    return out

def jpfont(sz): return ImageFont.truetype(JP_FONT, sz)

def wrap(draw, text, font, maxw):
    words = text.split(); lines=[]; cur=""
    for w in words:
        t=(cur+" "+w).strip()
        if draw.textlength(t,font=font)<=maxw: cur=t
        else:
            if cur: lines.append(cur)
            cur=w
    if cur: lines.append(cur)
    return lines

def build_cover(slug, title, subtitle):
    W,H=1600,2000
    img=Image.new("RGB",(W,H)); px=img.load()
    top=(31,138,112); bot=(21,80,74)
    for y in range(H):
        t=y/(H-1); row=tuple(int(top[k]+(bot[k]-top[k])*t) for k in range(3))
        for x in range(W): px[x,y]=row
    d=ImageDraw.Draw(img)
    d.rectangle([60,60,W-60,H-60],outline=(255,255,255),width=4)
    d.text((W/2,250),"JAPAN",font=jpfont(70),fill=(190,230,218),anchor="mm")
    d.text((W/2,330),"TRAVEL • PRINTABLE",font=jpfont(34),fill=(190,230,218),anchor="mm")
    # title (wrap)
    tf=jpfont(96); lines=wrap(d,title,tf,W-260)
    y=560
    for ln in lines[:5]:
        d.text((W/2,y),ln,font=tf,fill=(255,255,255),anchor="mm"); y+=120
    d.text((W/2,y+40),subtitle,font=jpfont(40),fill=(225,240,235),anchor="mm")
    # bottom badge
    d.rectangle([W/2-360,H-360,W/2+360,H-240],fill=(255,255,255))
    d.text((W/2,H-300),"INSTANT DOWNLOAD",font=jpfont(40),fill=(21,80,74),anchor="mm")
    d.text((W/2,H-160),"Print at home • A4 / US Letter",font=jpfont(34),fill=(225,240,235),anchor="mm")
    out=f"{COVER_DIR}/{slug}.png"; img.save(out,"PNG"); return out

# 商品名/サブの簡易抽出
def meta(md, slug):
    title = re.search(r"^#\s+(.+)$", md, re.M)
    title = title.group(1).strip() if title else slug
    # 表紙用の短いタイトル＝ファイル先頭H1から "(Printable)"等除去
    short = re.sub(r"\(.*?\)","",title).strip()
    return title, short

SUB = {
 "01_japan-trip-planner":"Itinerary • Budget • Packing • Phrases",
 "02_tokyo-itinerary-planner":"A 5-day Tokyo itinerary & planner",
 "03_kyoto-osaka-itinerary-planner":"Kyoto & Osaka 5-day Kansai planner",
 "04_hidden-japan-hokuriku-planner":"Hokuriku • Toyama • off the beaten path",
 "05_japan-packing-checklist":"Four-season packing checklist",
 "06_japan-budget-tracker":"Daily spending & currency tracker",
 "07_japan-phrases-cheat-sheet":"English → Japanese with romaji",
 "08_japan-food-bucket-list":"120+ dishes to try in Japan",
 "09_japan-blank-itinerary-template":"Blank fill-in daily planner",
 "10_japan-first-timer-survival-guide":"Transport • money • etiquette • eSIM",
 "11_osaka-itinerary-planner":"Osaka day-by-day itinerary & food",
 "12_hokkaido-travel-planner":"Sapporo • Otaru • Furano • seasons",
 "13_okinawa-travel-planner":"Islands, beaches & seasonal guide",
 "14_japan-cherry-blossom-planner":"Sakura season & hanami planner",
 "15_japan-budget-travel-planner":"See Japan for less — budget guide",
 "16_japan-family-kids-planner":"Japan with kids — family planner",
 "17_japan-rail-trip-planner":"JR Pass & Shinkansen route planner",
 "18_hiroshima-miyajima-itinerary":"Peace Memorial & Miyajima Island",
 "19_japan-solo-travel-planner":"Solo trip — safety & planning",
 "20_japan-2-week-itinerary-planner":"14-day Japan route & fill-in plan",
}
import sys
targets = sys.argv[1:] or [os.path.basename(f) for f in sorted(glob.glob(f"{SRC}/[0-9]*.md"))]
for fn in targets:
    path=f"{SRC}/{fn}" if not fn.startswith(SRC) else fn
    slug=os.path.splitext(os.path.basename(path))[0]
    md=open(path,encoding="utf-8").read()
    title,short=meta(md,slug)
    content=get_print_content(md)
    p=build_pdf(slug,title,content)
    c=build_cover(slug,short,SUB.get(slug,"A printable Japan travel planner"))
    print(f"OK {slug}: {os.path.getsize(p)//1024}KB pdf / {os.path.getsize(c)//1024}KB cover")
