#!/usr/bin/env python3
"""
C. 英語独立記事（Substack/Medium向け）の下地生成

記事mdから「英語版独立記事を書くためのプロンプト」を生成する。
オーナーはMacで実行 → 出力プロンプトを Claude/ChatGPT に貼って完成英語記事を得る
→ EN/outputs/ に保存して Substack/Medium へ転載。

使い方:
    python3 gen_en_article.py
    python3 gen_en_article.py --article CMO/outputs/xxx.md
    python3 gen_en_article.py --copy        # プロンプトを pbcopy
"""
import argparse
import re
import subprocess
from pathlib import Path

from _common import parse_article, find_article, REPO_ROOT

OUT_DIR = REPO_ROOT / "EN" / "research"


def extract_jp_section_titles(body: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^■\s*(.+)$", body, re.M)]


def build_prompt(article: dict) -> str:
    sections = extract_jp_section_titles(article["body_ja"])
    sections_block = "\n".join(f"- {s}" for s in sections) or "- (no section headings detected)"
    return f"""You are a writer for an English-language Substack about Japan from a
resident's point of view — quiet, honest, never touristy. Adapt the
attached Japanese note article into a standalone English Substack-style
post (800–1200 words).

Constraints:
- First-person voice. The author lives in Takaoka, Toyama.
- Never use the phrases "If you make things…" or "ordinary greatness."
- Avoid superlative overclaims ("the only one in the world", "Japan's #1").
  Use careful, accurate language with concrete numbers where useful.
- Use authentic Japanese terms (e.g., "umami", "kombu", "kamaboko",
  "kombu-jime") without italicizing.
- Add one Travel/Visit paragraph near the end: how to get there from
  Tokyo via Hokuriku Shinkansen, what to look for, season-specific notes.
- End with a single quiet line that earns its place. No clichés.

Title (Japanese, for reference): {article['title_ja']}

Source article sections (Japanese headings):
{sections_block}

Existing English summary (use as anchor, expand significantly):
---
{article['en_summary'] or '(no English summary section found)'}
---

Full Japanese body (translate liberally, do not be literal):
---
{article['body_ja']}
---

Output: Markdown only. Start with an H1 (English title), then the article.
No commentary, no preamble.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--article", default=None)
    ap.add_argument("--copy", action="store_true")
    args = ap.parse_args()

    md = find_article(args.article)
    article = parse_article(md)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{article['date']}_enprompt_{md.stem}.md"

    prompt = build_prompt(article)
    body = f"""# Prompt: standalone English article

- Source: `{md.name}`
- JP title: {article['title_ja']}
- Use with: Claude / ChatGPT (large context)
- After completion: save the English article into `EN/outputs/{article['date']}_en_{md.stem}.md`

---

{prompt}
"""
    out.write_text(body, encoding="utf-8")
    print(f"✅ {out}")

    if args.copy:
        subprocess.run(["pbcopy"], input=prompt.encode("utf-8"), check=False)
        print("📋 プロンプトをクリップボードへコピーしました")


if __name__ == "__main__":
    main()
