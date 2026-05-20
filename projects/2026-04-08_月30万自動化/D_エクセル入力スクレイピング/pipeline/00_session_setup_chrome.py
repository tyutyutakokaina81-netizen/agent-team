"""
00_session_setup_chrome.py — 既存Chromeログインを流用するセッション設定（macOS版）

通常のGoogle Chromeでクラウドワークス・ランサーズにログイン済みの状態を
そのままPlaywright用セッションとして取り込む。

【前提条件】
  - macOSのデフォルトGoogle Chromeを使用していること
  - 対象サイト（クラウドワークス／ランサーズ）にChromeでログイン済みであること
  - **実行前に Google Chrome を完全に終了すること**
    （Chromeはプロファイルを排他ロックするため、起動中だと失敗する）

【使い方】
  1. ⌘+Q で Chrome を完全終了
  2. python3 00_session_setup_chrome.py
  3. 両方完了したら通常のパイプラインへ
"""

import json
import sys
import time
from pathlib import Path

SESSION_DIR = Path(__file__).parent.parent / ".sessions"
SESSION_DIR.mkdir(exist_ok=True)

# macOS デフォルトのChromeプロファイル
CHROME_USER_DATA_DIR = Path.home() / "Library/Application Support/Google/Chrome"

PLATFORMS = {
    "crowdworks": {
        "verify_url": "https://crowdworks.jp/mypage",
        "session_file": SESSION_DIR / "crowdworks_session.json",
        "login_marker": "login",  # URL に含まれていたらログインページ
    },
    "lancers": {
        "verify_url": "https://www.lancers.jp/mypage",
        "session_file": SESSION_DIR / "lancers_session.json",
        "login_marker": "login",
    },
}


def setup_session(platform: str):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[ERROR] pip3 install playwright && python3 -m playwright install chromium")
        sys.exit(1)

    if not CHROME_USER_DATA_DIR.exists():
        print(f"[ERROR] Chromeプロファイルが見つかりません: {CHROME_USER_DATA_DIR}")
        print("  Chromeをインストールしてからログインしてください")
        sys.exit(1)

    config = PLATFORMS[platform]
    print(f"\n━━━ [{platform}] ━━━")
    print("  既存Chromeのログイン状態を使ってセッションを取得します")

    with sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(CHROME_USER_DATA_DIR),
                channel="chrome",
                headless=False,
                viewport={"width": 1280, "height": 800},
            )
        except Exception as e:
            err = str(e)
            print(f"[ERROR] プロファイル起動失敗:\n  {err}")
            if "ProcessSingleton" in err or "lock" in err.lower():
                print("\n  ⚠️  Chromeが起動中です。⌘+Q で完全終了してから再実行してください。")
            sys.exit(1)

        page = context.pages[0] if context.pages else context.new_page()
        try:
            page.goto(config["verify_url"], timeout=20000)
        except Exception as e:
            print(f"[ERROR] ページ読込失敗: {e}")
            context.close()
            sys.exit(1)

        time.sleep(3)
        current_url = page.url
        is_logged_in = config["login_marker"] not in current_url.lower()

        if is_logged_in:
            print(f"  ✅ ログイン済み確認: {current_url}")
        else:
            print(f"  ⚠️  未ログイン状態です（URL: {current_url}）")
            print(f"  ブラウザでログインしてください...")
            input("  ログインが完了したら Enter を押してください: ")

        # セッション情報を保存（storage_state 形式）
        try:
            storage = context.storage_state()
            config["session_file"].write_text(
                json.dumps(storage, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            cookie_count = len(storage.get("cookies", []))
            print(f"  ✅ セッション保存: {config['session_file'].name}（Cookie {cookie_count}件）")
        except Exception as e:
            print(f"[ERROR] セッション保存失敗: {e}")

        context.close()


if __name__ == "__main__":
    print("━" * 60)
    print("  既存Chromeログインを流用するセッション設定")
    print("━" * 60)
    print("  実行前に Google Chrome を ⌘+Q で完全終了してください")
    print("  （Chromeはプロファイルを排他ロックするため、起動中だと失敗します）")
    print()
    input("Chrome を完全終了したら Enter を押してください: ")

    targets = []
    if len(sys.argv) > 1:
        targets = [sys.argv[1]]
    else:
        for name in PLATFORMS:
            ans = input(f"  {name} のセッションを取得しますか？ (y/N): ").strip().lower()
            if ans == "y":
                targets.append(name)

    if not targets:
        print("\n[終了] 対象が選択されませんでした")
        sys.exit(0)

    for platform in targets:
        if platform in PLATFORMS:
            setup_session(platform)

    print("\n" + "━" * 60)
    print("  完了。以下のコマンドで応募運用を開始できます:")
    print("  python3 run_pipeline.py search --category writing")
    print("━" * 60)
