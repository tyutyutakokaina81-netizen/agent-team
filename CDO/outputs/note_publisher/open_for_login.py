#!/usr/bin/env python3
"""ワーカーと同じブラウザプロファイルで Reddit/Quora(等) に owner がログインするためのヘルパー。

背景(2026-07-25): ワーカーは publish と同じ永続プロファイル ~/.note_publisher_profile を使う。
owner が"通常のChrome"でログインしても、このプロファイルには反映されず、ワーカーは未ログイン扱いになる
（07-25便で「Reddit/Quora未ログイン→投稿保留」が実証）。
→ このスクリプトを Mac で 1 回実行し、開いた"見えるブラウザ"で Reddit と Quora にログインすれば、
   セッションがプロファイルに保存され、以後ワーカーが被リンク投稿できる。認証情報はスクリプトに一切書かない/保存しない。

使い方（Mac のターミナル）:
    cd ~/agent-team-run && python3 CDO/outputs/note_publisher/open_for_login.py
    → 見えるChromeが開く → Reddit/Quora のタブで「Continue with Google（てつ）」でログイン
    → 済んだらターミナルで Enter → ブラウザが閉じてセッション保存完了。
"""
import sys
from pathlib import Path

PROFILE_DIR = Path.home() / ".note_publisher_profile"  # publish_to_note.py と統一

URLS = [
    "https://www.reddit.com/login",
    "https://www.quora.com/",
    "https://kdp.amazon.co.jp",  # 2026-07-25 KDP追加=ワーカーが本の登録を代行できるよう同プロファイルにログイン
]


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print("Playwright未インストール。~/agent-team-run で setup 済みのはず。", file=sys.stderr)
        return 1
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        # headless=False = 実ウィンドウを表示（owner が手でログインする）
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE_DIR), headless=False, viewport={"width": 1280, "height": 900}
        )
        # 各サービスをタブで開く
        first = ctx.pages[0] if ctx.pages else ctx.new_page()
        first.goto(URLS[0], wait_until="domcontentloaded")
        for u in URLS[1:]:
            pg = ctx.new_page()
            pg.goto(u, wait_until="domcontentloaded")
        print("=" * 60)
        print("ブラウザを開きました。各タブで Reddit / Quora に")
        print("「Continue with Google（てつのアカウント）」でログインしてください。")
        print("※パスワードはこのスクリプトに保存されません（ブラウザのプロファイルにセッションが残るだけ）。")
        print("ログインが済んだら、このターミナルで Enter を押してください。")
        print("=" * 60)
        try:
            input()
        except EOFError:
            pass
        ctx.close()
    print("完了。セッションを ~/.note_publisher_profile に保存しました。次のワーカー便が投稿できます。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
