#!/usr/bin/env python3
"""cowork: ログアウト状態で有料4本のペイウォールを検証。正常=can_read=False/is_limited=Trueで本文が切れる。"""
import json
from playwright.sync_api import sync_playwright
PAID={"nba958ccd6cb8":100,"nb90084f378c8":100,"n78279355fd10":300,"n6e7ca70475c8":980}
with sync_playwright() as pw:
    b=pw.chromium.launch(headless=True); ctx=b.new_context(); page=ctx.new_page()
    page.goto("https://note.com/",wait_until="domcontentloaded",timeout=45000); page.wait_for_timeout(1500)
    for nid,price in PAID.items():
        r=page.evaluate("""async(u)=>{const x=await fetch(u);return{s:x.status,t:await x.text()}}""",
                        f"https://note.com/api/v3/notes/{nid}")
        try:
            d=json.loads(r['t']).get('data',{})
            paywalled = (d.get('can_read')==False) or (d.get('is_limited')==True)
            print(f"{nid} ¥{price}: http={r['s']} status={d.get('status')} price={d.get('price')} "
                  f"can_read={d.get('can_read')} is_limited={d.get('is_limited')} "
                  f"=> {'PAYWALLED_OK' if paywalled else 'FULL-FREE?'}  {str(d.get('name'))[:34]}")
        except Exception as e:
            print(f"{nid}: parse/err http={r['s']} {str(r['t'])[:80]}")
    ctx.close(); b.close()
