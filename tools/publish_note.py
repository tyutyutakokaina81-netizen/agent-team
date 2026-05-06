"""GitHub Actions から呼ばれる note 自動公開（規約上グレー・BANリスクあり）。

事前準備:
  1. mac で `python3 tools/extract_note_state.py` を実行して手動ログイン
  2. 出力された note_state.b64 の内容を GitHub Secret NOTE_STORAGE_STATE に登録
  3. ワークフロー側で base64 デコードして Playwright に渡す

DRY_RUN=1 の場合は対象ファイルの確認のみ。
storageState は数日〜数週間で失効するため、失敗時は再取得が必要。
"""
from __future__ import annotations

import base64
import os
import random
import re
import sys
import time
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TODAY = date.today().isoformat()
TARGET = REPO / "daily" / TODAY / "note_draft.md"
STATE_FILE = Path("/tmp/note_state.json")

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def _parse(text: str) -> tuple[str, str]:
    m = re.match(r"#\s+(.+?)\n(.*)", text, flags=re.DOTALL)
    if not m:
        return "本日の記事", text.strip()
    return m.group(1).strip(), m.group(2).strip()


def _restore_state() -> bool:
    b64 = os.environ.get("NOTE_STORAGE_STATE")
    if not b64:
        print("ERROR: NOTE_STORAGE_STATE 未設定", file=sys.stderr)
        return False
    try:
        STATE_FILE.write_bytes(base64.b64decode(b64))
        return True
    except Exception as e:
        print(f"ERROR: storageState 復元失敗: {e}", file=sys.stderr)
        return False


def _human_sleep(a: float, b: float) -> None:
    time.sleep(random.uniform(a, b))


def main() -> int:
    if not TARGET.exists():
        print(f"対象ファイルなし: {TARGET}")
        return 0

    title, body = _parse(TARGET.read_text(encoding="utf-8"))

    if os.environ.get("DRY_RUN", "1") == "1":
        print(f"DRY_RUN: would publish '{title[:60]}...' to note ({len(body)}字)")
        return 0

    if not _restore_state():
        return 1

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright 未インストール", file=sys.stderr)
        return 1

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        ctx = browser.new_context(
            storage_state=str(STATE_FILE),
            user_agent=USER_AGENT,
            viewport={"width": 1366, "height": 850},
            locale="ja-JP",
            timezone_id="Asia/Tokyo",
        )
        page = ctx.new_page()
        page.goto("https://note.com/notes/new", wait_until="domcontentloaded", timeout=30000)
        _human_sleep(2.5, 4.5)

        if "/login" in page.url:
            print("ERROR: 未ログイン（storageState 失効の可能性）", file=sys.stderr)
            print(f"再取得手順: tools/extract_note_state.py を mac で実行", file=sys.stderr)
            browser.close()
            return 1

        try:
            page.click("input[placeholder*='記事タイトル']", timeout=10000)
            _human_sleep(0.4, 1.2)
            page.keyboard.type(title, delay=random.randint(50, 110))
            _human_sleep(1.0, 2.2)

            page.click("div[contenteditable='true']")
            _human_sleep(0.4, 1.2)
            page.keyboard.type(body, delay=random.randint(20, 70))
            _human_sleep(2.5, 4.5)

            page.click("button:has-text('公開設定')")
            _human_sleep(1.5, 3.0)
            page.click("button:has-text('投稿')")
            _human_sleep(4.0, 7.0)

            url = page.url
            print(f"posted: {url}")
        except Exception as e:
            print(f"ERROR: 投稿フロー失敗: {type(e).__name__}: {e}", file=sys.stderr)
            browser.close()
            return 1

        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
