"""GitHub Actions から呼ばれる Reddit 自動公開（公式API・PRAW）。

daily/<TODAY>/reddit_post.md をパースして Reddit に投稿する。
GitHub Secrets で REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET / REDDIT_USER_AGENT /
REDDIT_USERNAME / REDDIT_PASSWORD / REDDIT_SUBREDDIT を設定すること。

DRY_RUN=1（既定）の場合、認証もスキップして対象ファイルの存在確認のみ。
本番化は GitHub Actions の env で DRY_RUN=0 を明示的に設定する。
"""
from __future__ import annotations

import os
import re
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TODAY = date.today().isoformat()
TARGET = REPO / "daily" / TODAY / "reddit_post.md"


def _parse(text: str) -> tuple[str, str]:
    title_m = re.search(r"Title:\s*\n(.+)", text)
    body_m = re.search(r"Body:\s*\n(.+?)(?=\n\nSubreddit|\Z)", text, re.DOTALL)
    if not title_m or not body_m:
        raise ValueError("reddit_post.md のフォーマット不正")
    return title_m.group(1).strip(), body_m.group(1).strip()


def main() -> int:
    if not TARGET.exists():
        print(f"対象ファイルなし: {TARGET}")
        return 0

    title, body = _parse(TARGET.read_text(encoding="utf-8"))
    sub = os.environ.get("REDDIT_SUBREDDIT", "SlowLiving")

    if os.environ.get("DRY_RUN", "1") == "1":
        print(f"DRY_RUN: would post '{title[:60]}...' to r/{sub}")
        return 0

    try:
        import praw
    except ImportError:
        print("ERROR: praw 未インストール")
        return 1

    required = ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT",
                "REDDIT_USERNAME", "REDDIT_PASSWORD"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f"ERROR: 環境変数未設定: {missing}")
        return 1

    reddit = praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        user_agent=os.environ["REDDIT_USER_AGENT"],
        username=os.environ["REDDIT_USERNAME"],
        password=os.environ["REDDIT_PASSWORD"],
    )
    submission = reddit.subreddit(sub).submit(title, selftext=body)
    url = f"https://www.reddit.com{submission.permalink}"
    print(f"posted: {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
