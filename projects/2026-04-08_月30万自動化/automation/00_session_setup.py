"""
00_session_setup.py — note と X のログインを永続プロファイルに保存

実行方法:
  python3 00_session_setup.py            # note と X 両方
  python3 00_session_setup.py note       # note のみ
  python3 00_session_setup.py x          # X のみ

各プラットフォームを別々のブラウザセッションで起動する。
途中で片方のブラウザを閉じても他方は影響を受けない。
ログイン状態は .profiles/chrome/ に永続保存される。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _browser import open_browser, PROFILE_DIR  # noqa: E402


PLATFORMS = {
    "note": "https://note.com/login",
    "x": "https://x.com/login",
}


def login_platform(name: str, url: str):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[ERROR] pip install playwright && playwright install chromium")
        sys.exit(1)

    print(f"\n{'─' * 60}")
    print(f"  [{name}] ログイン")
    print(f"  URL: {url}")
    print("─" * 60)

    try:
        with sync_playwright() as p:
            ctx = open_browser(p)
            page = ctx.new_page()
            page.goto(url, timeout=30000)
            print("\n  ブラウザでログインしてください。")
            print("  完了したらターミナルで Enter を押してください...")
            input()
            print(f"  ✅ {name} ログイン状態を保存しました")
            try:
                ctx.close()
            except Exception:
                pass
    except Exception as e:
        print(f"  ⚠️  {name} の処理中にエラー: {type(e).__name__}: {e}")
        print(f"  この後 'bash go session-{name}' で {name} 単独でやり直せます")


def main():
    args = sys.argv[1:]
    if not args:
        targets = list(PLATFORMS.keys())
    else:
        targets = [a for a in args if a in PLATFORMS]
        if not targets:
            print(f"使い方: python3 00_session_setup.py [{'|'.join(PLATFORMS.keys())}]")
            sys.exit(1)

    print(f"プロファイル保存先: {PROFILE_DIR}")
    for name in targets:
        login_platform(name, PLATFORMS[name])

    print("\n完了。次のコマンドで本番実行できます：")
    print("  bash go all")


if __name__ == "__main__":
    main()
