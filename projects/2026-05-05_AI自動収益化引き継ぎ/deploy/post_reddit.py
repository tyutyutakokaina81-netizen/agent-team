"""Reddit 自動投稿（PRAW・公式API）。

.env に REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET / REDDIT_USER_AGENT /
REDDIT_USERNAME / REDDIT_PASSWORD / REDDIT_SUBREDDIT が必要。
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import _browser
import published

OUT = Path.home() / "ai-auto" / "outputs"


def _latest_reddit() -> Path | None:
    files = sorted(OUT.glob("*reddit_post*.md"), reverse=True)
    return files[0] if files else None


def _parse(text: str) -> tuple[str, str]:
    title_match = re.search(r"Title:\s*\n(.+)", text)
    body_match = re.search(r"Body:\s*\n(.+?)(?=\n\nSubreddit|\Z)", text, re.DOTALL)
    if not title_match or not body_match:
        raise ValueError("Reddit投稿のフォーマット不正")
    return title_match.group(1).strip(), body_match.group(1).strip()


def run() -> tuple[bool, str]:
    src = _latest_reddit()
    if not src:
        return False, "outputs に reddit_post が見つからない"
    title, body = _parse(src.read_text(encoding="utf-8"))

    if _browser.is_dry():
        sub = os.environ.get("REDDIT_SUBREDDIT", "SlowLiving")
        return True, f"DRY_RUN: would post '{title[:40]}...' to r/{sub}"

    try:
        import praw
    except ImportError:
        return False, "praw 未インストール（pip install praw）"

    required = ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT",
                "REDDIT_USERNAME", "REDDIT_PASSWORD", "REDDIT_SUBREDDIT"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        return False, f"環境変数未設定: {missing}"

    reddit = praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        user_agent=os.environ["REDDIT_USER_AGENT"],
        username=os.environ["REDDIT_USERNAME"],
        password=os.environ["REDDIT_PASSWORD"],
    )
    sub = reddit.subreddit(os.environ["REDDIT_SUBREDDIT"])
    submission = sub.submit(title, selftext=body)
    url = f"https://www.reddit.com{submission.permalink}"
    published.append("reddit", url, title, 0)
    return True, url


if __name__ == "__main__":
    ok, msg = run()
    print(("OK: " if ok else "FAIL: ") + msg)
