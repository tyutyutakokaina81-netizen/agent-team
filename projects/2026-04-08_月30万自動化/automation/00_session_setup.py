"""
00_session_setup.py — note と X のセッションを保存する（初回 1 回のみ）

実行方法:
  pip install playwright && playwright install chromium  # 未実行なら
  python3 00_session_setup.py

ブラウザが開くので、note と X にログインしてセッションを保存する。
保存先: .sessions/{note,x}_session.json （.gitignore で保護）
"""

import json
import sys
from pathlib import Path

SESSION_DIR = Path(__file__).parent / ".sessions"
SESSION_DIR.mkdir(exist_ok=True)

PLATFORMS = {
    "note": {
        "url": "https://note.com/login",
        "session_file": SESSION_DIR / "note_session.json",
        "check": "note.com",
    },
    "x": {
        "url": "https://x.com/login",
        "session_file": SESSION_DIR / "x_session.json",
        "check": "x.com",
    },
}


def setup(platform: str):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[ERROR] pip install playwright && playwright install chromium")
        sys.exit(1)

    cfg = PLATFORMS[platform]
    print(f"\n[{platform}] ブラウザを開きます。ログインしてください。")
    print(f"  URL: {cfg['url']}")
    print("  ログイン完了したらターミナルで Enter を押してください。\n")

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=False, slow_mo=80)
        except Exception:
            browser = p.chromium.launch(headless=False, slow_mo=80)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()
        page.goto(cfg["url"])
        input()
        storage = context.storage_state()
        cfg["session_file"].write_text(
            json.dumps(storage, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  ✅ 保存: {cfg['session_file']}")
        browser.close()


def status():
    print("\n[セッション状態]")
    for name, cfg in PLATFORMS.items():
        ok = cfg["session_file"].exists()
        print(f"  {name}: {'✅ 保存済み' if ok else '❌ 未設定'}")


if __name__ == "__main__":
    status()
    print()
    targets = sys.argv[1:] or list(PLATFORMS.keys())
    for t in targets:
        if t in PLATFORMS:
            setup(t)
        else:
            print(f"[ERROR] 未対応: {t}")
    print("\n完了。publish_note.py / post_x.py / run_all.py を実行できます。")
