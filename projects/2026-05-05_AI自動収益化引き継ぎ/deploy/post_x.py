"""X (Twitter) 自動投稿（Playwright）。

X API 無料枠は読み取り専用のため Web 自動化のみ。
セッションは ~/ai-auto/.browser_profile/ を再利用（初回のみ手動ログイン）。
"""
from __future__ import annotations

import csv
from collections import deque
from pathlib import Path

import _browser
import _note
import _scheduler
import published

CSV_PATH = Path.home() / "ai-auto" / "published.csv"
RECENT_LIMIT = 200


def _latest_note_url() -> tuple[str | None, str | None]:
    if not CSV_PATH.exists():
        return None, None
    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        recent_lines = deque(f, maxlen=RECENT_LIMIT)
    rows = list(csv.DictReader(recent_lines))
    for r in reversed(rows):
        if r.get("kind") in ("note", "paid_note"):
            return r["url_or_id"], r["title"]
    return None, None


def _first_body_line(body: str) -> str:
    for line in body.split("\n"):
        line = line.strip()
        if line and not line.startswith("#"):
            return line[:90]
    return ""


def _build_post_text() -> str:
    parsed = _note.latest_title_and_body()
    if parsed is None:
        return "今日のnoteを公開しました。"
    title, body = parsed
    snippet = _first_body_line(body) or title

    url, prev_title = _latest_note_url()
    if url and prev_title:
        return f"{snippet}\n\n→ {prev_title}\n{url}"
    return f"{snippet}\n\n#地方暮らし #AI副業"


def run() -> tuple[bool, str]:
    text = _build_post_text()
    if len(text) > 280:
        text = text[:277] + "..."

    if _browser.is_dry():
        return True, f"DRY_RUN: would tweet '{text[:60]}...'"

    with _browser.open_browser(headless=False) as ctx:
        page = ctx.new_page()
        page.goto("https://x.com/home")
        _browser.human_sleep(3, 5)

        if "/login" in page.url or "/i/flow" in page.url:
            return False, _browser.NOT_LOGGED_IN

        _browser.human_move(page)
        page.click("a[href='/compose/post'], a[data-testid='SideNav_NewTweet_Button']")
        _browser.human_sleep(2, 4)

        _browser.human_type(page, "div[role='textbox']", text)
        _browser.human_sleep(2, 4)

        page.click("button[data-testid='tweetButton']")
        _browser.human_sleep(3, 6)

        published.append("x", page.url, text[:60], 0)
        _scheduler.log("x posted")
        return True, "tweeted"


if __name__ == "__main__":
    ok, msg = run()
    print(("OK: " if ok else "FAIL: ") + msg)
