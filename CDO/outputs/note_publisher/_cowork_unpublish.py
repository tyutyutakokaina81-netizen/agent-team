#!/usr/bin/env python3
"""cowork: 氷見牛2本目 nc7a3522ade60 を「下書きに戻す」。--go でクリック実行、無しは実測のみ。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright
import publish_to_note as P

NID = "nc7a3522ade60"
GO = "--go" in sys.argv

def find_card(page):
    """スクロールして NID のカードを探す。見つかったら True。"""
    for i in range(40):
        if page.query_selector(f'a[href*="{NID}"]'):
            return True
        page.mouse.wheel(0, 3000)
        page.wait_for_timeout(900)
        # click もっとみる if present
        more = page.query_selector('button:has-text("もっとみる"), button:has-text("さらに")')
        if more:
            try: more.click(); page.wait_for_timeout(1200)
            except Exception: pass
    return bool(page.query_selector(f'a[href*="{NID}"]'))

def main():
    with sync_playwright() as pw:
        ctx = P.load_context(pw)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto("https://note.com/notes", wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(3500)
            if not find_card(page):
                print("NOT_FOUND: nc7a3522ade60 のカードがリストに見つからない")
                return
            print("FOUND card for", NID)
            # kebab within the card ancestry
            kebabs = page.query_selector_all(
                f"xpath=//a[contains(@href,'{NID}')]/ancestor::*[position()<=8]//button")
            print("candidate buttons:", [ (b.get_attribute('aria-label') or b.inner_text() or '').strip()[:24] for b in kebabs])
            menu_texts = []
            opened_btn = None
            for b in kebabs:
                lbl = (b.get_attribute("aria-label") or b.inner_text() or "").strip()
                try:
                    b.scroll_into_view_if_needed()
                    b.click()
                    page.wait_for_timeout(1200)
                    items = page.query_selector_all('[role="menuitem"], [role="menu"] button, [role="menu"] a, [role="menu"] li')
                    texts = list({(i.inner_text() or "").strip() for i in items if (i.inner_text() or "").strip()})
                    if any("下書き" in t or "非公開" in t or "公開" in t for t in texts):
                        menu_texts = texts; opened_btn = b
                        print(f">> menu opened via '{lbl}':", texts)
                        break
                    else:
                        # close and try next
                        page.keyboard.press("Escape"); page.wait_for_timeout(400)
                except Exception as ex:
                    print("  btn err", ex)
            if not menu_texts:
                print("MENU_NOT_FOUND: 下書きに戻す等の項目が見つからない")
                return
            if not GO:
                print("DRY-RUN: --go を付けると『下書きに戻す/非公開』をクリックします")
                return
            # click the unpublish item
            target = None
            for i in page.query_selector_all('[role="menuitem"], [role="menu"] button, [role="menu"] a, [role="menu"] li'):
                t = (i.inner_text() or "").strip()
                if "下書きに戻す" in t or ("非公開" in t and "設定" not in t):
                    target = i; break
            if not target:
                print("UNPUBLISH_ITEM_NOT_FOUND in", menu_texts); return
            print("clicking:", (target.inner_text() or "").strip())
            target.click()
            page.wait_for_timeout(1500)
            # confirm dialog?
            for conf in ['button:has-text("下書きに戻す")', 'button:has-text("戻す")', 'button:has-text("OK")', 'button:has-text("はい")']:
                c = page.query_selector(conf)
                if c:
                    print("confirm:", conf); c.click(); page.wait_for_timeout(1500); break
            print("DONE. verify state...")
            page.goto(f"https://editor.note.com/notes/{NID}/edit", wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(3000)
            btns = list({(b.inner_text() or '').strip() for b in page.query_selector_all('button') if (b.inner_text() or '').strip() and len((b.inner_text() or '').strip())<12})
            print("editor buttons now:", btns)
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
