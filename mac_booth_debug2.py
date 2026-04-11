#!/usr/bin/env python3
"""
mac_booth_debug2.py — select_typeページとフォームの構造を調べる
"""
import asyncio, json
from pathlib import Path

SESSION_FILE = Path(__file__).parent / ".sessions" / "booth_session.json"
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

def load_cookies():
    data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    cookie_str = data.get("cookie", "")
    cookies = []
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            cookies.append({"name": k.strip(), "value": v.strip(),
                            "domain": ".booth.pm", "path": "/"})
    return cookies

async def main():
    from playwright.async_api import async_playwright

    cookies = load_cookies()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context()
        await ctx.add_cookies(cookies)
        page = await ctx.new_page()

        # select_type ページ
        print("=== select_type ページ ===")
        await page.goto("https://manage.booth.pm/items/select_type",
                        wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        shot1 = LOG_DIR / "select_type.png"
        await page.screenshot(path=str(shot1), full_page=True)
        print(f"スクリーンショット保存: {shot1}")
        print(f"URL: {page.url}")

        # リンクとボタンを全表示
        links = await page.eval_on_selector_all("a, button", """
            els => els.map(e => ({
                tag: e.tagName,
                text: e.innerText?.trim().substring(0, 50),
                href: e.href || '',
                class: e.className?.substring(0, 60)
            }))
        """)
        print("\nクリック可能な要素:")
        for l in links:
            if l.get("text"):
                print(f"  [{l['tag']}] {l['text']} | href: {l['href'][:60]}")

        # デジタルコンテンツを探してクリック
        print("\n=== デジタルコンテンツを選択 ===")
        clicked = False
        for sel in [
            "a:has-text('デジタル')",
            "a:has-text('digital')",
            "a[href*='digital']",
            "a[href*='type']",
            "button:has-text('デジタル')",
        ]:
            el = page.locator(sel).first
            if await el.count() > 0:
                text = await el.inner_text()
                href = await el.get_attribute("href") or ""
                print(f"  見つかった: [{sel}] text={text[:30]} href={href[:60]}")
                await el.click()
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_timeout(3000)
                clicked = True
                break

        if not clicked:
            # 全リンクのhrefを表示
            all_links = await page.eval_on_selector_all("a[href]",
                "els => els.map(e => e.href)")
            print("  全リンク:")
            for l in all_links[:20]:
                print(f"    {l}")

        # フォームページ
        print(f"\n=== フォームページ ===")
        print(f"URL: {page.url}")
        shot2 = LOG_DIR / "form_page.png"
        await page.screenshot(path=str(shot2), full_page=True)
        print(f"スクリーンショット保存: {shot2}")

        # input/textarea を全表示
        inputs = await page.eval_on_selector_all("input, textarea, select", """
            els => els.map(e => ({
                tag: e.tagName,
                name: e.name,
                id: e.id,
                placeholder: e.placeholder,
                type: e.type,
                class: e.className?.substring(0, 40)
            }))
        """)
        print("\nフォーム要素:")
        for inp in inputs:
            print(f"  [{inp['tag']}] name={inp['name']} id={inp['id']} "
                  f"placeholder={inp['placeholder']} type={inp['type']}")

        await browser.close()

asyncio.run(main())
