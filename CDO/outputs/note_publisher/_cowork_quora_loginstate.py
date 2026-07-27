#!/usr/bin/env python3
"""cowork(2026-07-28便): Quoraログイン状態を厳密判定。ヘッダのLogin/Sign Up vs プロフィールメニュー。"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright
import publish_to_note as P

def main():
    with sync_playwright() as pw:
        ctx = P.load_context(pw)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto("https://www.quora.com/", wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(5000)
            body = page.inner_text("body")
            btns = page.evaluate("""() => [...document.querySelectorAll("button,a")]
                .map(e=>(e.innerText||'').trim().replace(/\\n/g,' ')).filter(t=>t&&t.length<20).slice(0,50)""")
            has_login = any(t in ("Login","Log In","Sign In") for t in btns)
            has_signup = any("Sign" in t for t in btns)
            # logged-in markers
            has_notif = "notifications" in body.lower() or any("Notification" in t for t in btns)
            has_addq = any("Add question" in t for t in btns)
            print("URL:", page.url)
            print("HAS_LOGIN_BTN:", has_login, "HAS_SIGNUP_BTN:", has_signup)
            print("HAS_NOTIF:", has_notif, "HAS_ADDQ:", has_addq)
            print("HEADER_BTNS:", json.dumps(btns[:20], ensure_ascii=False))
            # try the /following page which requires login
            page.goto("https://www.quora.com/following", wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(4000)
            print("FOLLOWING_URL:", page.url)
            print("FOLLOWING_TITLE:", page.title()[:80])
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
