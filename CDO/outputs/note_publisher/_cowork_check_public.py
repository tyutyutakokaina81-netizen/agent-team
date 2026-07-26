#!/usr/bin/env python3
"""cowork: ログアウト状態(素のchromium)で公開可視性を確認。公開中なら本文が見え、下書きなら404/非公開。"""
from playwright.sync_api import sync_playwright
AUTHOR="safe_canna441"
IDS=["nc7a3522ade60","n0443f87ce4df"]
with sync_playwright() as pw:
    b=pw.chromium.launch(headless=True)
    ctx=b.new_context()
    page=ctx.new_page()
    for nid in IDS:
        url=f"https://note.com/{AUTHOR}/n/{nid}"
        try:
            r=page.goto(url,wait_until="domcontentloaded",timeout=45000)
            page.wait_for_timeout(3500)
            body=page.evaluate("()=>document.body.innerText.slice(0,240)")
            gone=("見つかりません" in body) or ("削除" in body) or ("ページが存在" in body) or ("非公開" in body)
            print(f"\n[{nid}] http={r.status if r else '?'} final={page.url}")
            print(f"  gone/hidden={gone}")
            print(f"  body_head: {body[:160].replace(chr(10),' ')}")
        except Exception as e:
            print(f"[{nid}] ERR {e}")
    ctx.close(); b.close()
