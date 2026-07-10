#!/usr/bin/env python3
"""依存ゼロ(標準ライブラリのみ)で Markdown原稿 → 有効なEPUB を生成する。
外国人収益化の中核=英語KDP本。pandoc/calibre不要(このコンテナに無いため自作)。

使い方:
  python3 EN/build_epub.py \
    --md EN/outputs/kindle/Toyama_Uncrowded_Coast_manuscript.md \
    --out EN/outputs/kindle/Toyama_Uncrowded_Coast.epub \
    --title "Toyama: Japan's Uncrowded Coast" \
    --author "Tetsu, a Toyama local" --lang en

EPUBはmimetype+META-INF/container.xml+OEBPS(content.opf/toc.ncx/xhtml)のZIP。
Markdownは # 見出しで章分割し、段落/太字/斜体/箇条書き/水平線を最小変換する。
"""
import argparse, html, re, zipfile
from pathlib import Path


def md_inline(text: str) -> str:
    """行内Markdown → XHTML(エスケープしてから太字/斜体を復元)。"""
    t = html.escape(text)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", t)
    return t


def md_block_to_xhtml(md: str) -> str:
    """1章分のMarkdown本文 → XHTML本体(見出し/段落/リスト/hr)。"""
    out = []
    lines = md.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            i += 1
            continue
        # 見出し
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{md_inline(m.group(2))}</h{lvl}>")
            i += 1
            continue
        # 水平線
        if re.match(r"^-{3,}$", line):
            out.append("<hr/>")
            i += 1
            continue
        # 箇条書き(- / * / 数字.)
        if re.match(r"^\s*([-*]|\d+\.)\s+", line):
            ordered = bool(re.match(r"^\s*\d+\.\s+", line))
            tag = "ol" if ordered else "ul"
            items = []
            while i < len(lines) and re.match(r"^\s*([-*]|\d+\.)\s+", lines[i]):
                item = re.sub(r"^\s*([-*]|\d+\.)\s+", "", lines[i].rstrip())
                items.append(f"<li>{md_inline(item)}</li>")
                i += 1
            out.append(f"<{tag}>" + "".join(items) + f"</{tag}>")
            continue
        # 引用
        if line.startswith(">"):
            quote = []
            while i < len(lines) and lines[i].startswith(">"):
                quote.append(md_inline(lines[i].lstrip(">").strip()))
                i += 1
            out.append("<blockquote><p>" + "<br/>".join(quote) + "</p></blockquote>")
            continue
        # 段落(空行まで連結)
        para = []
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,6}\s|-{3,}$|\s*([-*]|\d+\.)\s+|>)", lines[i]):
            para.append(lines[i].strip())
            i += 1
        out.append("<p>" + md_inline(" ".join(para)) + "</p>")
    return "\n".join(out)


def split_chapters(md: str):
    """# (H1) ごとに章分割。最初のH1前の前付けは第0章に含める。返り値=[(title, body_md)]。"""
    lines = md.split("\n")
    chapters = []
    cur_title = "Front Matter"
    cur = []
    started = False
    for line in lines:
        m = re.match(r"^#\s+(.*)$", line)  # H1のみ(##は章内)
        if m:
            if cur:
                chapters.append((cur_title, "\n".join(cur)))
            cur_title = m.group(1).strip()
            cur = [line]
            started = True
        else:
            cur.append(line)
    if cur:
        chapters.append((cur_title, "\n".join(cur)))
    return chapters


XHTML_TMPL = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{lang}"><head>
<meta charset="utf-8"/><title>{title}</title>
<style>body{{font-family:Georgia,serif;line-height:1.6;margin:1.2em}}h1{{font-size:1.5em}}h2{{font-size:1.2em}}blockquote{{border-left:3px solid #ccc;padding-left:1em;color:#444}}</style>
</head><body>
{body}
</body></html>"""


def build(md_path: Path, out_path: Path, title: str, author: str, lang: str):
    md = md_path.read_text(encoding="utf-8")
    chapters = split_chapters(md)
    book_id = "urn:uuid:toyama-uncrowded-coast-2026"

    files = {}  # arcname -> bytes
    # 章XHTML
    manifest_items, spine_items, nav_points = [], [], []
    for idx, (ctitle, body_md) in enumerate(chapters):
        fname = f"chap{idx:02d}.xhtml"
        xhtml = XHTML_TMPL.format(lang=lang, title=html.escape(ctitle),
                                  body=md_block_to_xhtml(body_md))
        files[f"OEBPS/{fname}"] = xhtml.encode("utf-8")
        manifest_items.append(f'<item id="c{idx}" href="{fname}" media-type="application/xhtml+xml"/>')
        spine_items.append(f'<itemref idref="c{idx}"/>')
        nav_points.append(
            f'<navPoint id="n{idx}" playOrder="{idx+1}"><navLabel><text>{html.escape(ctitle)}</text></navLabel><content src="{fname}"/></navPoint>')

    # content.opf
    opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid" version="2.0">
 <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
  <dc:identifier id="bookid">{book_id}</dc:identifier>
  <dc:title>{html.escape(title)}</dc:title>
  <dc:creator opf:role="aut">{html.escape(author)}</dc:creator>
  <dc:language>{lang}</dc:language>
  <dc:rights>© 2026</dc:rights>
 </metadata>
 <manifest>
  <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
  {chr(10).join('  '+m for m in manifest_items)}
 </manifest>
 <spine toc="ncx">
  {chr(10).join('  '+s for s in spine_items)}
 </spine>
</package>"""
    files["OEBPS/content.opf"] = opf.encode("utf-8")

    # toc.ncx
    ncx = f"""<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
 <head><meta name="dtb:uid" content="{book_id}"/></head>
 <docTitle><text>{html.escape(title)}</text></docTitle>
 <navMap>
  {chr(10).join('  '+n for n in nav_points)}
 </navMap>
</ncx>"""
    files["OEBPS/toc.ncx"] = ncx.encode("utf-8")

    # container.xml
    files["META-INF/container.xml"] = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
        ' <rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>\n'
        '</container>').encode("utf-8")

    # ZIP(mimetypeは非圧縮で先頭に)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w") as z:
        zi = zipfile.ZipInfo("mimetype")
        zi.compress_type = zipfile.ZIP_STORED
        z.writestr(zi, "application/epub+zip")
        for arc, data in files.items():
            z.writestr(arc, data, zipfile.ZIP_DEFLATED)
    return len(chapters)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--author", default="Tetsu, a Toyama local")
    ap.add_argument("--lang", default="en")
    a = ap.parse_args()
    n = build(Path(a.md), Path(a.out), a.title, a.author, a.lang)
    print(f"✅ EPUB生成: {a.out}  ({n}章)")
