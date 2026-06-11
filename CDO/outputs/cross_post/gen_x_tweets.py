#!/usr/bin/env python3
"""
B. X(Twitter)英語ツイート生成

各記事から、X英語アカウント用の単発ツイート＋スレッドを生成する。

使い方:
    python3 gen_x_tweets.py
    python3 gen_x_tweets.py --article CMO/outputs/xxx.md
    python3 gen_x_tweets.py --copy        # 単発ツイートを pbcopy
"""
import argparse
import re
import subprocess
from pathlib import Path

from _common import parse_article, find_article, REPO_ROOT

OUT_DIR = REPO_ROOT / "EN" / "outputs" / "x_tweets"
LIMIT = 280


def trim_to(text: str, limit: int) -> str:
    """文末で切り詰める。"""
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(".", 1)
    if len(cut[0]) > limit * 0.6:
        return cut[0].strip() + "."
    return text[: limit - 1].rstrip() + "…"


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def make_single_tweet(article: dict) -> str:
    """1ツイート(280字)に収める。"""
    en = article["en_summary"] or ""
    sentences = split_sentences(en)
    if not sentences:
        return "[manual translation needed]"
    body = sentences[0]
    extras = []
    for s in sentences[1:]:
        if len(body) + 1 + len(s) <= 200:
            body += " " + s
        else:
            break
    tags = " ".join(article["tags_en"][:4]) if article["tags_en"] else "#Japan #JapaneseFood"
    candidate = f"{body}\n\n{tags}"
    return trim_to(candidate, LIMIT)


def make_thread(article: dict, n: int = 5) -> list[str]:
    """スレッド型（n本まで）に分割。"""
    en = article["en_summary"]
    if not en:
        return ["[no English summary available]"]
    sentences = split_sentences(en)
    if not sentences:
        return [en[:LIMIT]]
    # 文を貪欲に詰める
    tweets, cur = [], ""
    for s in sentences:
        if len(cur) + 1 + len(s) <= LIMIT - 8:
            cur = (cur + " " + s).strip()
        else:
            tweets.append(cur)
            cur = s
        if len(tweets) >= n - 1:
            break
    if cur:
        tweets.append(cur)
    # 番号付与＆最後にタグ
    out = []
    total = min(len(tweets), n)
    for i, t in enumerate(tweets[:total], 1):
        prefix = f"{i}/{total} "
        out.append(trim_to(prefix + t, LIMIT))
    tags = " ".join(article["tags_en"][:6]) if article["tags_en"] else "#Japan #JapaneseFood"
    last = out[-1] if out else ""
    if len(last) + 2 + len(tags) <= LIMIT:
        out[-1] = last + "\n\n" + tags
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--article", default=None)
    ap.add_argument("--copy", action="store_true")
    args = ap.parse_args()

    md = find_article(args.article)
    article = parse_article(md)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{article['date']}_x_{md.stem}.md"

    single = make_single_tweet(article)
    thread = make_thread(article, n=5)

    lines = [
        f"# X (Twitter) English tweet variants",
        f"- Article: `{md.name}`",
        f"- JP title: {article['title_ja']}",
        "",
        f"## A. Single tweet ({len(single)} chars)",
        "```",
        single,
        "```",
        "",
        f"## B. Thread ({len(thread)} tweets)",
    ]
    for i, t in enumerate(thread, 1):
        lines += [f"### Tweet {i}/{len(thread)} ({len(t)} chars)", "```", t, "```", ""]

    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ {out}")

    if args.copy:
        subprocess.run(["pbcopy"], input=single.encode("utf-8"), check=False)
        print("📋 単発ツイートをクリップボードへコピーしました")


if __name__ == "__main__":
    main()
