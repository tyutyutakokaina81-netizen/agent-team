"""
00_session_setup.py — note と X のログインを永続プロファイルに保存

実行方法:
  python3 00_session_setup.py

システム Chrome を永続プロファイル付きで開き、note と X にログインする。
Google ログインも通る（自動化検知を緩和した起動方式）。
セッションは .profiles/main/ に保存され、以降の publish_note / post_x で再利用される。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _browser import open_browser, PROFILE_DIR  # noqa: E402


PLATFORMS = [
    ("note", "https://note.com/login"),
    ("x", "https://x.com/login"),
]


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[ERROR] pip install playwright && playwright install chromium")
        sys.exit(1)

    print(f"プロファイル保存先: {PROFILE_DIR}")
    print()

    with sync_playwright() as p:
        ctx = open_browser(p)
        page = ctx.new_page()

        for name, url in PLATFORMS:
            print(f"\n[{name}] ブラウザでログインしてください")
            print(f"  URL: {url}")
            page.goto(url)
            print("  ログイン完了したらターミナルで Enter を押してください...")
            input()
            print(f"  ✅ {name} ログイン状態を保存しました（永続プロファイル）")

        ctx.close()

    print("\n完了。次のコマンドで公開できます：")
    print("  bash go all")


if __name__ == "__main__":
    main()
