#!/usr/bin/env python3
"""
A. Reddit投稿テンプレ生成

各記事から、複数のサブレディット向け投稿テンプレを生成する。
オーナーはMacで実行 → 出力テキストをコピペしてRedditに投稿。

使い方:
    python3 gen_reddit_post.py                                # 最新記事
    python3 gen_reddit_post.py --article CMO/outputs/xxx.md   # 指定
    python3 gen_reddit_post.py --copy                         # 結果を pbcopy へ
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

from _common import parse_article, find_article, REPO_ROOT

OUT_DIR = REPO_ROOT / "EN" / "outputs" / "reddit"

# サブレディット候補：カテゴリ別
SUBREDDIT_MAP = {
    "food": [
        ("r/JapaneseFood", "Anyone who loves Japanese cuisine"),
        ("r/AskCulinary", "If your post discusses technique/history of preparation"),
        ("r/japan", "General Japan-related (use sparingly)"),
        ("r/JapanTravel", "If you tied the food to a place worth visiting"),
        ("r/hokuriku", "Small but on-topic for 北陸 content"),
    ],
    "travel": [
        ("r/JapanTravel", "Anyone planning a Japan trip"),
        ("r/JapanTravelTips", "Practical tips on visiting"),
        ("r/HiddenJapan", "Off-the-beaten-path locations"),
        ("r/japanpics", "If you have a great photo"),
        ("r/hokuriku", "Hokuriku-region content"),
    ],
    "culture": [
        ("r/japan", "General Japan culture"),
        ("r/JapaneseHistory", "Historical context"),
        ("r/manga", "If Doraemon/anime/manga related"),
        ("r/Buddhism", "If temple/Zen content"),
    ],
    "business": [
        ("r/freelance", "Solo work and freelancing"),
        ("r/Entrepreneur", "Building solo businesses"),
        ("r/digitalnomad", "Remote/solo work content"),
        ("r/sideproject", "Build-in-public content"),
    ],
    "ai": [
        ("r/ArtificialIntelligence", "General AI discussion"),
        ("r/ChatGPT", "If ChatGPT-related"),
        ("r/ClaudeAI", "If Claude-related"),
        ("r/Productivity", "AI for productivity"),
    ],
}


def detect_category(article: dict) -> str:
    """記事内容からカテゴリを推定（雑だがOK）。"""
    text = (article["title_ja"] + " " + article["body_ja"][:500]).lower()
    if any(k in text for k in ["食", "ラーメン", "寿司", "豆腐", "丼", "発酵", "酒", "和菓子", "コロッケ"]):
        return "food"
    if any(k in text for k in ["駅", "観光", "海岸", "滝", "公園", "町", "訪", "旅"]):
        return "travel"
    if any(k in text for k in ["国宝", "寺", "大仏", "歴史", "万葉", "ドラえもん", "藤子"]):
        return "culture"
    if any(k in text for k in ["フリーランス", "ひとり", "個人事業", "起業", "営業", "顧客", "請求"]):
        return "business"
    if any(k in text for k in ["AI", "ChatGPT", "Claude", "プロンプト", "自動化"]):
        return "ai"
    return "business"


def make_reddit_post(article: dict, subreddit: str, hint: str) -> dict:
    """1つのサブレディット向けに投稿テンプレを作る。"""
    title_ja = article["title_ja"]
    en_summary = article["en_summary"] or "(no English summary found in this article)"

    # タイトル：英語要約の最初の文を使い、なければ翻訳プレースホルダ
    first_sentence = re.split(r"(?<=[.!?])\s+", en_summary.strip())[0] if en_summary else "[Title in English]"
    title_en = first_sentence[:280].rstrip(",.;:") + "."
    if "→" not in title_en and len(title_en) > 100:
        title_en = title_en[:97] + "..."

    body = f"""{en_summary}

---

(Original Japanese article: *{title_ja}* — published on note.com)

I write from Takaoka, Toyama, in central Japan. If anything here
catches your interest, ask away — happy to share more from on the
ground.
"""

    return {
        "subreddit": subreddit,
        "hint": hint,
        "title": title_en,
        "body": body,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--article", default=None)
    ap.add_argument("--copy", action="store_true", help="最初のサブレディット投稿を pbcopy へ")
    args = ap.parse_args()

    md = find_article(args.article)
    article = parse_article(md)
    category = detect_category(article)
    subreddits = SUBREDDIT_MAP.get(category, SUBREDDIT_MAP["business"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base = OUT_DIR / f"{article['date']}_reddit_{md.stem}.md"

    lines = [f"# Reddit cross-post templates", "",
             f"- Article: `{md.name}`",
             f"- Detected category: **{category}**",
             "",
             "---", ""]

    for sub, hint in subreddits:
        post = make_reddit_post(article, sub, hint)
        lines += [
            f"## {post['subreddit']}",
            f"_({hint})_", "",
            "**Title**:", "```", post["title"], "```", "",
            "**Body**:", "```", post["body"].rstrip(), "```", "",
            "---", "",
        ]

    base.write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ {base}")

    if args.copy:
        first = make_reddit_post(article, *subreddits[0])
        clip = f"TITLE:\n{first['title']}\n\nBODY:\n{first['body']}"
        subprocess.run(["pbcopy"], input=clip.encode("utf-8"), check=False)
        print(f"📋 最初の候補 {subreddits[0][0]} をクリップボードへコピーしました")


if __name__ == "__main__":
    main()
