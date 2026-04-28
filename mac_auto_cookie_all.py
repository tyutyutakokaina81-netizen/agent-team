#!/usr/bin/env python3
"""
mac_auto_cookie_all.py — Chrome から BOOTH / note / X のセッションを一括取得

Chromeにログイン済みであれば手動操作ゼロで全サービスのセッションを保存する。
browser-cookie3 は Playwright の storage_state 形式に変換して保存するため、
auto_note_publish.py / auto_x_post.py / auto_d_apply.py がそのまま使用できる。
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SESSIONS = Path(__file__).parent / ".sessions"
SESSIONS.mkdir(exist_ok=True)

SERVICES = [
    {
        "name": "BOOTH",
        "domain": ".booth.pm",
        "file": SESSIONS / "booth_session.json",
        "format": "cookie_str",
    },
    {
        "name": "note",
        "domain": ".note.com",
        "file": SESSIONS / "note_session.json",
        "format": "playwright",
    },
    {
        "name": "X(Twitter)",
        "domain": ".twitter.com",
        "file": SESSIONS / "x_session.json",
        "format": "playwright",
    },
]


def install_deps():
    for cmd in [
        [sys.executable, "-m", "pip", "install", "browser-cookie3", "--break-system-packages", "-q"],
        [sys.executable, "-m", "pip", "install", "browser-cookie3", "-q"],
    ]:
        if subprocess.run(cmd, capture_output=True).returncode == 0:
            return


def to_playwright_state(cookies: dict, domain: str) -> dict:
    """browser_cookie3 の dict を Playwright storage_state 形式に変換"""
    cookie_list = []
    for name, value in cookies.items():
        cookie_list.append({
            "name": name,
            "value": value,
            "domain": domain,
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": True,
            "sameSite": "None",
        })
    return {"cookies": cookie_list, "origins": []}


def fetch_service(svc: dict, bc3) -> bool:
    domain = svc["domain"]
    name = svc["name"]

    try:
        jar = bc3.chrome(domain_name=domain)
        cookies = {c.name: c.value for c in jar}

        if not cookies:
            jar = bc3.safari(domain_name=domain)
            cookies = {c.name: c.value for c in jar}

        if not cookies:
            print(f"  ❌ {name}: Chromeにログインしていません → 手動ログイン後に再実行")
            return False

        if svc["format"] == "cookie_str":
            data = {"cookie": "; ".join(f"{k}={v}" for k, v in cookies.items())}
        else:
            data = to_playwright_state(cookies, domain)

        svc["file"].write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        print(f"  ✅ {name}: {len(cookies)}個のクッキーを保存 → {svc['file'].name}")
        return True

    except Exception as e:
        print(f"  ❌ {name}: {e}")
        return False


def main():
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  Chrome セッション一括取得")
    print("  BOOTH / note / X(Twitter)")
    print("  ※ キーチェーンのダイアログが出たら「許可」")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    try:
        import browser_cookie3 as bc3
    except ImportError:
        print("📦 browser-cookie3 をインストール中...")
        install_deps()
        try:
            import browser_cookie3 as bc3
        except ImportError:
            print("❌ インストール失敗: pip install browser-cookie3")
            sys.exit(1)

    results = {}
    for svc in SERVICES:
        results[svc["name"]] = fetch_service(svc, bc3)

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    ok = sum(results.values())
    print(f"  完了: {ok}/{len(SERVICES)} サービス")
    if ok == len(SERVICES):
        print("  全サービス準備OK → zsh run_daily_auto.sh で実行できます")
    else:
        missing = [k for k, v in results.items() if not v]
        print(f"  未取得: {', '.join(missing)}")
        print("  該当サービスにChromeでログイン後、再実行してください")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    main()
