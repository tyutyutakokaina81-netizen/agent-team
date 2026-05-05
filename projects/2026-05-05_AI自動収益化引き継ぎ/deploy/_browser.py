"""Playwright共通ヘルパ。

DRY_RUN=1 の場合、ブラウザを起動しない（呼び出し側で is_dry() ガード必須）。
"""
from __future__ import annotations

import os
import random
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

BASE = Path.home() / "ai-auto"
USER_DATA_DIR = BASE / ".browser_profile"
DRY_RUN = os.environ.get("DRY_RUN", "1") == "1"

NOT_LOGGED_IN = "未ログイン状態：~/ai-auto/.browser_profile に手動ログインしてください"


def is_dry() -> bool:
    return DRY_RUN


def human_sleep(min_sec: float = 0.8, max_sec: float = 3.5) -> None:
    if DRY_RUN:
        return
    time.sleep(random.uniform(min_sec, max_sec))


def human_type(page, selector: str, text: str) -> None:
    if DRY_RUN:
        return
    page.click(selector)
    human_sleep(0.3, 1.0)
    for ch in text:
        page.keyboard.type(ch, delay=random.randint(40, 130))
    human_sleep(0.5, 1.5)


def human_move(page) -> None:
    if DRY_RUN:
        return
    for _ in range(random.randint(2, 5)):
        x = random.randint(100, 1200)
        y = random.randint(100, 700)
        page.mouse.move(x, y, steps=random.randint(10, 25))
        time.sleep(random.uniform(0.1, 0.4))


@contextmanager
def open_browser(headless: bool = False) -> Iterator:
    if DRY_RUN:
        raise RuntimeError("open_browser called while DRY_RUN=1")
    from playwright.sync_api import sync_playwright
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(USER_DATA_DIR),
            headless=headless,
            viewport={"width": 1366, "height": 850},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            yield ctx
        finally:
            ctx.close()
