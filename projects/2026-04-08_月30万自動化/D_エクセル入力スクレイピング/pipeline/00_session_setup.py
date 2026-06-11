"""
00_session_setup.py — 初回ログイン設定（一度だけ実行）
ブラウザを起動してログイン後、セッションを保存する。
次回以降はこのセッションを使って自動で案件検索できる。

実行方法:
  pip install playwright
  playwright install chromium
  python 00_session_setup.py
"""

import json
import sys
from pathlib import Path

SESSION_DIR = Path(__file__).parent.parent / ".sessions"
SESSION_DIR.mkdir(exist_ok=True)

PLATFORMS = {
    "crowdworks": {
        "url": "https://crowdworks.jp/login",
        "session_file": SESSION_DIR / "crowdworks_session.json",
        "check_selector": ".header__username, .header-user__name",  # ログイン済み確認
    },
    "lancers": {
        "url": "https://www.lancers.jp/user/login",
        "session_file": SESSION_DIR / "lancers_session.json",
        "check_selector": ".header__user-name, .p-header__user",
    },
}


def setup_session(platform: str):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[ERROR] Playwright が未インストールです")
        print("  pip install playwright")
        print("  playwright install chromium")
        sys.exit(1)

    config = PLATFORMS[platform]
    print(f"\n[{platform}] ブラウザを起動します...")
    print("ログイン後、ブラウザを閉じてください（自動でセッションが保存されます）\n")

    with sync_playwright() as p:
        # インストール済みのChromeを使う（GoogleログインをPlaywright Chromiumでブロックされないため）
        try:
            browser = p.chromium.launch(channel="chrome", headless=False, slow_mo=100)
        except Exception:
            # Chromeがなければ通常のChromiumにフォールバック
            browser = p.chromium.launch(headless=False, slow_mo=100)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()
        page.goto(config["url"])

        print(f"ブラウザでログインしてください: {config['url']}")
        print("ログイン完了後、何かキーを押してください...")
        input()

        # ログイン確認
        try:
            page.wait_for_selector(config["check_selector"], timeout=5000)
            print(f"✅ ログイン確認済み")
        except Exception:
            print("⚠️  ログイン状態を確認できませんでした（セッションは保存します）")

        # セッション保存
        storage = context.storage_state()
        config["session_file"].write_text(
            json.dumps(storage, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"✅ セッション保存: {config['session_file']}")
        browser.close()


def check_sessions():
    """保存済みセッションの状態を確認"""
    print("\n[セッション状態]")
    for name, config in PLATFORMS.items():
        exists = config["session_file"].exists()
        status = "✅ 保存済み" if exists else "❌ 未設定"
        print(f"  {name}: {status}")


if __name__ == "__main__":
    check_sessions()
    print()

    targets = []
    if len(sys.argv) > 1:
        targets = [sys.argv[1]]
    else:
        for name in PLATFORMS:
            ans = input(f"{name} のセッションを設定しますか？ (y/N): ").strip().lower()
            if ans == "y":
                targets.append(name)

    for platform in targets:
        if platform in PLATFORMS:
            setup_session(platform)
        else:
            print(f"[ERROR] 未対応のプラットフォーム: {platform}")

    print("\n完了。01_search.py を実行して案件検索を開始できます。")
