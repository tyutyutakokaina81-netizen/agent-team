"""
_browser.py — システム Chrome＋専用プロファイルでブラウザを起動

Chrome は Default プロファイルに対して remote-debugging を許可しないため、
専用プロファイル（automation/.profiles/chrome/）を作り、初回 1 回だけ
そこに note と X をログインして永続化する。

Playwright バンドル Chromium ではなくシステム Chrome（channel="chrome"）を
使用するため、Google OAuth も通る。

⚠️ 実行前に Chrome を完全終了する必要は **ありません**（プロファイルが分離されているため）
"""

import platform
import sys
from pathlib import Path

PROFILE_DIR = Path(__file__).parent / ".profiles" / "chrome"
PROFILE_DIR.mkdir(parents=True, exist_ok=True)


def _check_chrome_not_running():
    """互換のためのスタブ（専用プロファイル方式では不要）"""
    return  # 専用プロファイルなので Chrome 起動中でも問題ない


def open_browser(p, headless: bool = False):
    """専用プロファイルで Chrome を起動。

    初回はログイン画面が出るので、ターミナルからの指示に従ってログインする。
    2 回目以降は cookie が保持されているのでログイン不要。
    """
    print(f"[ブラウザ] 専用プロファイル: {PROFILE_DIR}")

    return p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        channel="chrome",
        headless=headless,
        viewport={"width": 1280, "height": 900},
        slow_mo=80,
        args=[
            "--disable-blink-features=AutomationControlled",
        ],
    )
