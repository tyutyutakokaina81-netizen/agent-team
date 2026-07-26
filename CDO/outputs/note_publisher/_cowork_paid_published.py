#!/usr/bin/env python3
"""cowork: 公開済みの中で price>0(有料)の記事を列挙(key/name/price)。読み取りのみ。"""
import sys, json, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright
import publish_to_note as P
def hit(page,u): return page.evaluate("""async(u)=>{const r=await fetch(u,{credentials:'include'});return{s:r.status,t:await r.text()}}""",u)
def main():
    with sync_playwright() as pw:
        ctx=P.load_context(pw); page=ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto("https://note.com/",wait_until="domcontentloaded",timeout=45000); page.wait_for_timeout(1500)
            paid=[]
            for pg in range(1,9):
                r=hit(page,f"https://note.com/api/v2/creators/safe_canna441/contents?kind=note&page={pg}")
                if r['s']!=200: break
                d=json.loads(r['t']).get('data',{})
                notes=d.get('contents',d.get('notes',[])) if isinstance(d,dict) else []
                for n in notes:
                    pr=n.get('price',0)
                    if pr and int(pr)>0:
                        paid.append((n.get('key'),int(pr),str(n.get('name'))[:60]))
                if d.get('isLastPage'): break
            print("=== PUBLISHED paid notes (price>0) ===")
            for k,pr,nm in paid: print(f"  {k}  ¥{pr}  {nm}")
            print(f"total published paid: {len(paid)}")
        finally:
            ctx.close()
if __name__=="__main__": main()
