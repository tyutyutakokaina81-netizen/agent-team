#!/usr/bin/env python3
"""
make_epub.py — Markdown原稿(.md)を KDP にアップできる EPUB に変換する（依存ゼロ・標準ライブラリのみ）。

KDPは .md を受け付けないが .epub はOK。原稿を自動でEPUB化し、入稿はcowork/オーナーが
ファイルを上げるだけにする＝「ここ（出版作業）」の自動化。画像・装丁は最小（文章主体の実用書向け）。

使い方:
  python3 tools/make_epub.py 原稿.md [出力.epub] --title "本のタイトル" --author "Kai Arata"
  python3 tools/make_epub.py 原稿.md            # 同フォルダに 原稿.epub を出力（titleは先頭#から）

仕様:
  - 先頭の "# 見出し" を書名に（--title 優先）。"## 見出し" ごとに章に分割し目次を自動生成。
  - 対応Markdown: #/##/###見出し, 段落(空行区切り), ```コードブロック```, - 箇条書き, **太字**。
  - EPUB3(nav)+EPUB2(ncx)両対応の最小構成。HTMLは安全にエスケープ。
"""
import sys, re, html, zipfile, uuid, datetime, argparse
from pathlib import Path


def md_to_xhtml_body(md: str) -> str:
    """簡易Markdown→XHTML本文（見出し/段落/コード/箇条書き/太字）。"""
    out = []
    lines = md.split("\n")
    i = 0
    in_code = False
    code_buf = []
    list_buf = []

    def flush_list():
        if list_buf:
            out.append("<ul>")
            for it in list_buf:
                out.append(f"<li>{inline(it)}</li>")
            out.append("</ul>")
            list_buf.clear()

    def inline(s: str) -> str:
        s = html.escape(s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        return s

    para = []

    def flush_para():
        if para:
            text = " ".join(p.strip() for p in para if p.strip())
            if text:
                out.append(f"<p>{inline(text)}</p>")
            para.clear()

    while i < len(lines):
        ln = lines[i]
        if ln.strip().startswith("```"):
            if not in_code:
                flush_para(); flush_list()
                in_code = True; code_buf = []
            else:
                out.append("<pre><code>" + html.escape("\n".join(code_buf)) + "</code></pre>")
                in_code = False
            i += 1
            continue
        if in_code:
            code_buf.append(ln); i += 1; continue

        m = re.match(r"^(#{1,4})\s+(.*)$", ln)
        if m:
            flush_para(); flush_list()
            lvl = len(m.group(1))
            tag = {1: "h1", 2: "h2", 3: "h3", 4: "h4"}[lvl]
            out.append(f"<{tag}>{inline(m.group(2).strip())}</{tag}>")
            i += 1; continue

        if re.match(r"^\s*[-*]\s+", ln):
            flush_para()
            list_buf.append(re.sub(r"^\s*[-*]\s+", "", ln))
            i += 1; continue
        else:
            flush_list()

        if ln.strip() == "":
            flush_para()
        else:
            para.append(ln)
        i += 1

    flush_para(); flush_list()
    if in_code:
        out.append("<pre><code>" + html.escape("\n".join(code_buf)) + "</code></pre>")
    return "\n".join(out)


def split_chapters(md: str):
    """先頭#をタイトル、## ごとに章分割。最初の##前の内容は『はじめに』章に。"""
    lines = md.split("\n")
    title = None
    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip()
        lines = lines[1:]
    body = "\n".join(lines)
    parts = re.split(r"(?m)^(##\s+.*)$", body)
    chapters = []
    # parts: [pre, "## h", content, "## h", content, ...]
    pre = parts[0].strip()
    if pre:
        chapters.append(("はじめに", pre))
    for j in range(1, len(parts), 2):
        head = parts[j][2:].strip().lstrip("#").strip()
        content = parts[j + 1] if j + 1 < len(parts) else ""
        chapters.append((head, parts[j] + "\n" + content))
    if not chapters:
        chapters.append((title or "本文", body))
    return title, chapters


def build_epub(md_path: Path, out_path: Path, title=None, author="Kai Arata", lang="ja"):
    raw = md_path.read_text(encoding="utf-8")
    auto_title, chapters = split_chapters(raw)
    title = title or auto_title or md_path.stem
    book_id = "urn:uuid:" + str(uuid.uuid4())
    now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    chap_files = []
    for idx, (chap_title, chap_md) in enumerate(chapters, 1):
        fn = f"chap{idx:03d}.xhtml"
        body = md_to_xhtml_body(chap_md)
        xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{lang}" lang="{lang}">
<head><meta charset="utf-8"/><title>{html.escape(chap_title)}</title></head>
<body>{body}</body></html>"""
        chap_files.append((fn, chap_title, xhtml))

    # nav.xhtml (EPUB3)
    nav_items = "\n".join(
        f'<li><a href="{fn}">{html.escape(t)}</a></li>' for fn, t, _ in chap_files
    )
    nav = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="{lang}">
<head><meta charset="utf-8"/><title>{html.escape(title)}</title></head>
<body><nav epub:type="toc" id="toc"><h1>目次</h1><ol>{nav_items}</ol></nav></body></html>"""

    # toc.ncx (EPUB2 compat)
    navpoints = "\n".join(
        f'<navPoint id="n{i}" playOrder="{i}"><navLabel><text>{html.escape(t)}</text></navLabel>'
        f'<content src="{fn}"/></navPoint>'
        for i, (fn, t, _) in enumerate(chap_files, 1)
    )
    ncx = f"""<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
<head><meta name="dtb:uid" content="{book_id}"/></head>
<docTitle><text>{html.escape(title)}</text></docTitle>
<navMap>{navpoints}</navMap></ncx>"""

    manifest = '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>\n'
    manifest += '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>\n'
    spine = ""
    for i, (fn, t, _) in enumerate(chap_files, 1):
        manifest += f'<item id="c{i}" href="{fn}" media-type="application/xhtml+xml"/>\n'
        spine += f'<itemref idref="c{i}"/>\n'

    opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:identifier id="bookid">{book_id}</dc:identifier>
<dc:title>{html.escape(title)}</dc:title>
<dc:creator>{html.escape(author)}</dc:creator>
<dc:language>{lang}</dc:language>
<meta property="dcterms:modified">{now}</meta>
</metadata>
<manifest>{manifest}</manifest>
<spine toc="ncx">{spine}</spine>
</package>"""

    container = """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>"""

    with zipfile.ZipFile(out_path, "w") as z:
        # mimetype は最初・無圧縮
        z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", container, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/content.opf", opf, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/nav.xhtml", nav, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/toc.ncx", ncx, compress_type=zipfile.ZIP_DEFLATED)
        for fn, t, xhtml in chap_files:
            z.writestr(f"OEBPS/{fn}", xhtml, compress_type=zipfile.ZIP_DEFLATED)
    return title, len(chap_files)


def main(argv):
    ap = argparse.ArgumentParser(description="Markdown原稿→EPUB（KDP入稿用）")
    ap.add_argument("md")
    ap.add_argument("out", nargs="?", default=None)
    ap.add_argument("--title", default=None)
    ap.add_argument("--author", default="Kai Arata")
    ap.add_argument("--lang", default="ja")
    a = ap.parse_args(argv)
    md_path = Path(a.md)
    if not md_path.exists():
        sys.exit(f"原稿が見つかりません: {md_path}")
    out_path = Path(a.out) if a.out else md_path.with_suffix(".epub")
    title, n = build_epub(md_path, out_path, title=a.title, author=a.author, lang=a.lang)
    print(f"✅ EPUB生成: {out_path}  （書名「{title}」/ {n}章）")


if __name__ == "__main__":
    main(sys.argv[1:])
