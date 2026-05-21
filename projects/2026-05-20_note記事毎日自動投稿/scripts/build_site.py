"""
build_site.py — CMO/outputs/*_note記事.md から日英2言語の静的サイトを生成

出力：
    site/
    ├── index.html          (日本語トップ：記事一覧)
    ├── articles/<slug>.html
    ├── en/index.html       (英語トップ)
    └── en/articles/<slug>.html

特徴：
- 依存なし（Python標準ライブラリのみ、Markdownパーサーは簡易自前）
- 各記事ページに hreflang リンクで言語切替（SEO最適化）
- OGP メタタグでSNSプレビュー対応
- サムネ画像があれば <img> として埋め込み
- DEEPL_API_KEY があれば英訳版も生成、なければ日本語のみ
"""

from __future__ import annotations

import html
import os
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CMO_OUTPUTS = REPO_ROOT / "CMO" / "outputs"
SITE_DIR = REPO_ROOT / "site"
EN_DIR = SITE_DIR / "en"

SITE_TITLE = "Takaoka, From the Inside"
SITE_TITLE_JA = "高岡から、内側の話"
SITE_DESC = "Daily essays from Takaoka, Toyama, Japan — by safe_canna441"
SITE_DESC_JA = "富山県高岡市の暮らしを綴る日々のエッセイ"
NOTE_PROFILE_URL = "https://note.com/safe_canna441"
SITE_BASE_URL = "https://tyutyutakokaina81-netizen.github.io/agent-team"


def parse_frontmatter_and_body(md_text: str) -> tuple[str, str, str]:
    """H1をタイトル、最初の段落をリードに、本文を残りに。"""
    lines = md_text.splitlines()
    title = ""
    lead = ""
    body_start = 0
    for i, line in enumerate(lines):
        if not title and line.startswith("# "):
            title = line[2:].strip()
            body_start = i + 1
            break
    body_lines = lines[body_start:]
    for line in body_lines:
        if line.strip() and not line.startswith("#"):
            lead = line.strip()[:160]
            break
    body = "\n".join(body_lines).strip()
    return title, lead, body


def md_to_html(md: str) -> str:
    """簡易Markdown→HTML 変換（ヘッダー、段落、強調、リンク、リスト、HR）。"""
    lines = md.splitlines()
    html_parts: list[str] = []
    in_list = False
    in_para: list[str] = []

    def flush_para():
        nonlocal in_para
        if in_para:
            text = " ".join(in_para)
            html_parts.append(f"<p>{inline(text)}</p>")
            in_para = []

    def flush_list():
        nonlocal in_list
        if in_list:
            html_parts.append("</ul>")
            in_list = False

    def inline(text: str) -> str:
        text = html.escape(text)
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
        text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', text)
        return text

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_para()
            flush_list()
            continue
        if stripped.startswith("# "):
            flush_para()
            flush_list()
            # H1は既にタイトルとしてレイアウト側で出すのでスキップ
            continue
        if stripped.startswith("## "):
            flush_para()
            flush_list()
            html_parts.append(f"<h2>{inline(stripped[3:])}</h2>")
            continue
        if stripped.startswith("### "):
            flush_para()
            flush_list()
            html_parts.append(f"<h3>{inline(stripped[4:])}</h3>")
            continue
        if stripped.startswith("---"):
            flush_para()
            flush_list()
            html_parts.append("<hr/>")
            continue
        if stripped.startswith("- "):
            flush_para()
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            html_parts.append(f"<li>{inline(stripped[2:])}</li>")
            continue
        in_para.append(stripped)
    flush_para()
    flush_list()
    return "\n".join(html_parts)


def page_layout(
    title: str,
    description: str,
    body_html: str,
    lang: str,
    canonical: str,
    alt_lang_url: str,
    thumb_url: str | None,
    nav_top_url: str,
) -> str:
    alt_lang = "en" if lang == "ja" else "ja"
    nav_label = "日本語" if lang == "en" else "English"
    site_title = SITE_TITLE_JA if lang == "ja" else SITE_TITLE
    site_desc = SITE_DESC_JA if lang == "ja" else SITE_DESC
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{html.escape(title)} | {html.escape(site_title)}</title>
<meta name="description" content="{html.escape(description)}" />
<link rel="canonical" href="{canonical}" />
<link rel="alternate" hreflang="{alt_lang}" href="{alt_lang_url}" />
<link rel="alternate" hreflang="x-default" href="{canonical}" />
<meta property="og:title" content="{html.escape(title)}" />
<meta property="og:description" content="{html.escape(description)}" />
<meta property="og:type" content="article" />
<meta property="og:url" content="{canonical}" />
{f'<meta property="og:image" content="{thumb_url}" />' if thumb_url else ''}
<meta name="twitter:card" content="summary_large_image" />
<style>
  :root {{ --fg:#222; --bg:#fafaf7; --muted:#666; --accent:#1a4d6b; --hr:#ddd; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", "Hiragino Sans", "Noto Sans JP", sans-serif;
         color: var(--fg); background: var(--bg); margin: 0; line-height: 1.75; }}
  header {{ border-bottom: 1px solid var(--hr); padding: 1.5em 1em; background: #fff; }}
  header .container {{ max-width: 800px; margin: 0 auto; display: flex; justify-content: space-between; align-items: baseline; }}
  header a.brand {{ color: var(--accent); font-weight: 600; text-decoration: none; font-size: 1.1em; }}
  header nav a {{ color: var(--muted); text-decoration: none; margin-left: 1em; font-size: 0.9em; }}
  main {{ max-width: 740px; margin: 2em auto 4em; padding: 0 1.2em; }}
  h1.article-title {{ font-size: 1.7em; line-height: 1.35; margin: 0.4em 0 0.2em; color: var(--accent); }}
  .meta {{ color: var(--muted); font-size: 0.85em; margin-bottom: 2em; }}
  .thumb {{ width: 100%; border-radius: 4px; margin: 1em 0 2em; }}
  article p {{ margin: 1.1em 0; }}
  article h2 {{ margin-top: 2em; font-size: 1.2em; }}
  article h3 {{ margin-top: 1.6em; font-size: 1.05em; color: var(--accent); }}
  article ul {{ padding-left: 1.5em; }}
  article hr {{ border: none; border-top: 1px solid var(--hr); margin: 2.5em 0; }}
  footer {{ border-top: 1px solid var(--hr); padding: 2em 1em; text-align: center; color: var(--muted); font-size: 0.85em; }}
  footer a {{ color: var(--accent); }}
  .index-list {{ list-style: none; padding: 0; }}
  .index-list li {{ padding: 1em 0; border-bottom: 1px solid var(--hr); }}
  .index-list h2 {{ margin: 0; font-size: 1.1em; }}
  .index-list a {{ color: var(--fg); text-decoration: none; }}
  .index-list a:hover h2 {{ color: var(--accent); }}
  .index-list .date {{ color: var(--muted); font-size: 0.85em; }}
</style>
</head>
<body>
<header>
  <div class="container">
    <a href="{nav_top_url}" class="brand">{html.escape(site_title)}</a>
    <nav>
      <a href="/{'' if lang == 'ja' else 'en/'}">{'Home' if lang == 'en' else 'ホーム'}</a>
      <a href="/{'en/' if lang == 'ja' else ''}">{nav_label}</a>
      <a href="{NOTE_PROFILE_URL}" target="_blank" rel="noopener">note</a>
    </nav>
  </div>
</header>
<main>
{body_html}
</main>
<footer>
  <p>{html.escape(site_desc)}</p>
  <p>© Takaoka, From the Inside · <a href="{NOTE_PROFILE_URL}" target="_blank" rel="noopener">note/safe_canna441</a></p>
</footer>
</body>
</html>"""


def slugify(stem: str) -> str:
    # 2026-05-20_xxx_note記事 → 2026-05-20-xxx
    s = stem.replace("_note記事", "")
    s = re.sub(r"[^a-zA-Z0-9_\-ぁ-んァ-ヶー一-龯]", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "article"


def gather_articles() -> list[dict]:
    articles: list[dict] = []
    for md_path in sorted(CMO_OUTPUTS.glob("*_note記事.md"), reverse=True):
        text = md_path.read_text(encoding="utf-8")
        title, lead, body = parse_frontmatter_and_body(text)
        # 日付（ファイル名先頭から抽出）
        m = re.match(r"(\d{4}-\d{2}-\d{2})", md_path.stem)
        date_str = m.group(1) if m else ""
        slug = slugify(md_path.stem)
        thumb_jpg = CMO_OUTPUTS / f"{md_path.stem.replace('_note記事', '')}_thumb.jpg"
        thumb_png = CMO_OUTPUTS / f"{md_path.stem.replace('_note記事', '')}_thumb.png"
        thumb_rel = None
        if thumb_jpg.exists():
            thumb_rel = thumb_jpg
        elif thumb_png.exists():
            thumb_rel = thumb_png
        articles.append({
            "path": md_path,
            "slug": slug,
            "date": date_str,
            "title": title,
            "lead": lead,
            "body_md": body,
            "thumb": thumb_rel,
        })
    return articles


def translate_or_keep(md_text: str) -> str:
    """DEEPL_API_KEYがあれば翻訳、なければそのまま返す。"""
    if not os.environ.get("DEEPL_API_KEY", "").strip():
        return md_text
    try:
        from translate import translate_markdown
        return translate_markdown(md_text, target_lang="EN")
    except Exception as e:
        print(f"[WARN] translation failed: {e}; falling back to original")
        return md_text


def build_article_pages(articles: list[dict], lang: str) -> None:
    out_dir = SITE_DIR if lang == "ja" else EN_DIR
    art_dir = out_dir / "articles"
    art_dir.mkdir(parents=True, exist_ok=True)

    for a in articles:
        if lang == "en":
            print(f"[INFO] translating: {a['title'][:30]}")
            body_md = translate_or_keep(a["body_md"])
            title_md = translate_or_keep("# " + a["title"]).lstrip("# ").strip()
            lead_md = translate_or_keep(a["lead"]).strip()
        else:
            body_md = a["body_md"]
            title_md = a["title"]
            lead_md = a["lead"]

        body_html = md_to_html(body_md)

        thumb_url = None
        if a["thumb"]:
            # サムネをsite/にコピーして相対URLを得る
            thumb_dest = SITE_DIR / "images" / a["thumb"].name
            thumb_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(a["thumb"], thumb_dest)
            thumb_url = f"{SITE_BASE_URL}/images/{a['thumb'].name}"

        canonical_path = (
            f"{SITE_BASE_URL}/articles/{a['slug']}.html"
            if lang == "ja"
            else f"{SITE_BASE_URL}/en/articles/{a['slug']}.html"
        )
        alt_lang_url = (
            f"{SITE_BASE_URL}/en/articles/{a['slug']}.html"
            if lang == "ja"
            else f"{SITE_BASE_URL}/articles/{a['slug']}.html"
        )
        nav_top_url = "/" if lang == "ja" else "/en/"

        # 記事本体HTML
        inner = (
            f'<h1 class="article-title">{html.escape(title_md)}</h1>'
            f'<p class="meta">{a["date"]}</p>'
            + (f'<img class="thumb" src="{thumb_url}" alt="{html.escape(title_md)}" />' if thumb_url else "")
            + f'<article>{body_html}</article>'
        )

        full = page_layout(
            title=title_md,
            description=lead_md or (SITE_DESC if lang == "en" else SITE_DESC_JA),
            body_html=inner,
            lang=lang,
            canonical=canonical_path,
            alt_lang_url=alt_lang_url,
            thumb_url=thumb_url,
            nav_top_url=nav_top_url,
        )
        out_path = art_dir / f"{a['slug']}.html"
        out_path.write_text(full, encoding="utf-8")
        print(f"[OK] {out_path.relative_to(REPO_ROOT)}")


def build_index_page(articles: list[dict], lang: str) -> None:
    out_dir = SITE_DIR if lang == "ja" else EN_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    items_html: list[str] = []
    for a in articles:
        title = a["title"]
        if lang == "en":
            title = translate_or_keep(title) if title else title
        href = (
            f"/articles/{a['slug']}.html"
            if lang == "ja"
            else f"/en/articles/{a['slug']}.html"
        )
        items_html.append(
            f'<li><a href="{href}">'
            f'<div class="date">{a["date"]}</div>'
            f'<h2>{html.escape(title)}</h2>'
            f'</a></li>'
        )

    inner = (
        f'<h1 class="article-title">{html.escape(SITE_TITLE if lang=="en" else SITE_TITLE_JA)}</h1>'
        f'<p class="meta">{html.escape(SITE_DESC if lang=="en" else SITE_DESC_JA)}</p>'
        + f'<ul class="index-list">{"".join(items_html)}</ul>'
    )

    canonical = f"{SITE_BASE_URL}/" if lang == "ja" else f"{SITE_BASE_URL}/en/"
    alt = f"{SITE_BASE_URL}/en/" if lang == "ja" else f"{SITE_BASE_URL}/"

    full = page_layout(
        title=SITE_TITLE if lang == "en" else SITE_TITLE_JA,
        description=SITE_DESC if lang == "en" else SITE_DESC_JA,
        body_html=inner,
        lang=lang,
        canonical=canonical,
        alt_lang_url=alt,
        thumb_url=None,
        nav_top_url="/" if lang == "ja" else "/en/",
    )
    (out_dir / "index.html").write_text(full, encoding="utf-8")
    print(f"[OK] {(out_dir / 'index.html').relative_to(REPO_ROOT)}")


def write_meta_files() -> None:
    """robots.txt, sitemap.xml, CNAME (none) など補助ファイル。"""
    (SITE_DIR / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE_URL}/sitemap.xml\n",
        encoding="utf-8",
    )
    (SITE_DIR / ".nojekyll").write_text("", encoding="utf-8")


def main() -> int:
    if SITE_DIR.exists():
        # 古いビルドを掃除
        for p in SITE_DIR.glob("**/*"):
            if p.is_file():
                p.unlink()
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    EN_DIR.mkdir(parents=True, exist_ok=True)

    articles = gather_articles()
    if not articles:
        print("[WARN] no articles found in CMO/outputs/")
        return 0

    print(f"[INFO] {len(articles)} articles found")

    # 日本語版
    build_article_pages(articles, "ja")
    build_index_page(articles, "ja")

    # 英訳版（DEEPL_API_KEY があれば翻訳、なければ原文を流す）
    if os.environ.get("DEEPL_API_KEY", "").strip():
        build_article_pages(articles, "en")
        build_index_page(articles, "en")
    else:
        print("[WARN] DEEPL_API_KEY 未設定、英語版は原文を流用してビルドします")
        build_article_pages(articles, "en")
        build_index_page(articles, "en")

    write_meta_files()
    print("[OK] site built at site/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
