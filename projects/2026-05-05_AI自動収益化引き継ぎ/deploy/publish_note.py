"""note 自動公開（Playwright）。

初回手動セットアップ:
    with _browser.open_browser(headless=False) as ctx:
        page = ctx.new_page()
        page.goto("https://note.com/login")
        input("ログインしたら Enter")
    Cookie/セッションが ~/ai-auto/.browser_profile/ に保存され、以降は自動再利用。
"""
from __future__ import annotations

import _browser
import _note
import _scheduler
import published


def run() -> tuple[bool, str]:
    parsed = _note.latest_title_and_body()
    if parsed is None:
        return False, "outputs に note_draft が見つからない"
    title, body = parsed

    if _browser.is_dry():
        return True, f"DRY_RUN: would publish '{title[:40]}...' to note"

    with _browser.open_browser(headless=False) as ctx:
        page = ctx.new_page()
        page.goto("https://note.com/notes/new")
        _browser.human_sleep(2, 4)

        if "/login" in page.url:
            return False, _browser.NOT_LOGGED_IN

        _browser.human_move(page)
        _browser.human_type(page, "input[placeholder*='記事タイトル']", title)
        _browser.human_sleep(1, 2)
        _browser.human_type(page, "div[contenteditable='true']", body)
        _browser.human_sleep(2, 4)
        _browser.human_move(page)

        page.click("button:has-text('公開設定')")
        _browser.human_sleep(1, 3)
        page.click("button:has-text('投稿')")
        _browser.human_sleep(3, 6)

        url = page.url
        published.append("note", url, title, 0)
        _scheduler.log(f"note published: {url}")
        return True, url


if __name__ == "__main__":
    ok, msg = run()
    print(("OK: " if ok else "FAIL: ") + msg)
