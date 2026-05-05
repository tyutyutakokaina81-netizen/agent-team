"""ブラウザプロファイル初期化（X/note/CrowdWorks の手動ログインを順次案内）。

初回1回だけ実行。Cookie/セッションが ~/ai-auto/.browser_profile/ に保存され、
以降の自動投稿スクリプトはこれを再利用する（再ログイン不要）。

例:
    python3 init_login.py            # 全サービス順番に
    python3 init_login.py x note     # 指定サービスのみ
"""
from __future__ import annotations

import sys
from pathlib import Path

import _browser

SERVICES = {
    "x":          ("X (Twitter)",  "https://x.com/login"),
    "note":       ("note",         "https://note.com/login"),
    "crowdworks": ("CrowdWorks",   "https://crowdworks.jp/login"),
    "reddit":     ("Reddit",       "https://www.reddit.com/login"),
}


def main() -> None:
    requested = sys.argv[1:] or list(SERVICES.keys())
    invalid = [s for s in requested if s not in SERVICES]
    if invalid:
        print(f"未知のサービス: {invalid}（有効: {list(SERVICES.keys())}）")
        sys.exit(1)

    print("=" * 60)
    print("  ブラウザプロファイル初期化")
    print(f"  保存先: {_browser.USER_DATA_DIR}")
    print("=" * 60)

    if _browser.is_dry():
        print("\n環境変数 DRY_RUN を 0 にしてから実行してください：")
        print("    DRY_RUN=0 python3 init_login.py")
        sys.exit(1)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright 未インストール。先に: pip install -r requirements.txt && playwright install chromium")
        sys.exit(1)

    _browser.USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(_browser.USER_DATA_DIR),
            headless=False,
            viewport={"width": 1366, "height": 850},
        )
        page = ctx.new_page()

        for key in requested:
            label, url = SERVICES[key]
            print(f"\n→ {label}: ブラウザを {url} に移動します")
            page.goto(url)
            input(f"  {label} にログインを完了したら Enter キー: ")
            print(f"  ✓ {label} のセッションを保存しました")

        ctx.close()

    print("\n" + "=" * 60)
    print("  ✓ 全ログイン完了。以降は自動投稿スクリプトが Cookie を再利用します")
    print("=" * 60)


if __name__ == "__main__":
    main()
