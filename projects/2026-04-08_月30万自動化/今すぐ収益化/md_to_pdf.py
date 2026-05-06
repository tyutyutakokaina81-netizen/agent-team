#!/usr/bin/env python3
"""
md ベースのテンプレ（Vol.3/7/8/9）を販売用 PDF に変換。
日本語フォント（IPAexGothic 等）を使う。
"""

import re
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors

ROOT = Path(__file__).parent.parent / "C_テンプレ販売"
DIST = ROOT / "dist"
DIST.mkdir(exist_ok=True)

# 日本語フォント（システムにあれば登録）
JP_FONT = "Helvetica"
for candidate in [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
    "/usr/share/fonts/truetype/ipafont-gothic/ipag.ttf",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
]:
    p = Path(candidate)
    if p.exists():
        try:
            pdfmetrics.registerFont(TTFont("JP", str(p)))
            JP_FONT = "JP"
            print(f"[INFO] 日本語フォント登録: {p}")
            break
        except Exception as e:
            print(f"[WARN] フォント登録失敗 {p}: {e}")

if JP_FONT == "Helvetica":
    print("[WARN] 日本語フォントなし。PDF が文字化けする可能性あり。")


def md_to_pdf(md_path: Path, out_path: Path, title: str):
    text = md_path.read_text(encoding="utf-8")
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm,
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontName=JP_FONT, fontSize=20, spaceAfter=12, textColor=colors.HexColor("#1a3a6e"))
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName=JP_FONT, fontSize=15, spaceAfter=8, textColor=colors.HexColor("#2a5a9e"))
    h3 = ParagraphStyle("H3", parent=styles["Heading3"], fontName=JP_FONT, fontSize=12, spaceAfter=6, textColor=colors.HexColor("#3a6abf"))
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontName=JP_FONT, fontSize=10, leading=15, alignment=TA_LEFT)
    code = ParagraphStyle("Code", parent=styles["Code"], fontName=JP_FONT, fontSize=9, leading=12, leftIndent=12, backColor=colors.HexColor("#f5f5f5"), borderColor=colors.HexColor("#cccccc"), borderWidth=0.5, borderPadding=4, spaceAfter=6)

    story = []
    in_code_block = False
    code_buffer = []
    for line in text.split("\n"):
        # コードブロックの開始・終了
        if line.strip().startswith("```"):
            if in_code_block:
                # 終了 → flush
                if code_buffer:
                    code_text = "<br/>".join(escape(l) for l in code_buffer)
                    story.append(Paragraph(code_text, code))
                    code_buffer = []
                in_code_block = False
            else:
                in_code_block = True
            continue

        if in_code_block:
            code_buffer.append(line)
            continue

        # 見出し
        m = re.match(r"^(#{1,3})\s+(.+)$", line)
        if m:
            level = len(m.group(1))
            heading = escape(m.group(2))
            if level == 1:
                story.append(Paragraph(heading, h1))
            elif level == 2:
                story.append(Paragraph(heading, h2))
            else:
                story.append(Paragraph(heading, h3))
            continue

        # 区切り
        if line.strip() == "---":
            story.append(Spacer(1, 6))
            continue

        # 空行
        if not line.strip():
            story.append(Spacer(1, 4))
            continue

        # リスト・本文
        story.append(Paragraph(escape(line), body))

    doc.build(story)
    print(f"[OK] {out_path}")


def escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ─────────────────────────────────
# 変換実行
# ─────────────────────────────────
TARGETS = [
    ("vol3_prompt_collection_restaurant.md", "Vol3_飲食店プロンプト集.pdf", "飲食店向けSNS投稿プロンプト集 20選"),
    ("vol7_weekly_review.md", "Vol7_週次レビューテンプレ.pdf", "フリーランス週次レビューテンプレ"),
    ("vol8_prompt_collection_shigyou.md", "Vol8_士業営業メール20選.pdf", "士業向け営業メール文例 20選"),
    ("vol9_prompt_collection_blog_structure.md", "Vol9_ブログ記事構成20選.pdf", "ブログ記事構成生成プロンプト 20選"),
]

for src, dst, title in TARGETS:
    src_path = ROOT / src
    if not src_path.exists():
        print(f"[SKIP] {src} not found")
        continue
    md_to_pdf(src_path, DIST / dst, title)

print()
print("=" * 60)
print(f"全 {len(TARGETS)} PDF を {DIST} に出力しました。")
