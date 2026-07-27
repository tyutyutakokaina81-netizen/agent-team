#!/usr/bin/env python3
"""cowork(2026-07-28便): 候補質問の回答可否・飽和度・既回答有無を判定。投稿しない。"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright
import publish_to_note as P

URLS = [
    "https://www.quora.com/I-am-planning-a-trip-to-Japan-I-have-already-been-to-Tokyo-Osaka-and-Kyoto-What-are-some-other-great-towns-and-or-cities-that-are-worth-a-visit",
    "https://www.quora.com/What-are-some-underrated-less-common-travel-destinations-that-you-recommend",
    "https://www.quora.com/What-are-some-other-great-towns-and-or-cities-that-are-worth-a-visit",
]

def assess(page, url):
    r={"url":url}
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(4000)
        body = page.inner_text("body")
        js="""() => [...document.querySelectorAll("button,div[role='button']")]
            .map(e=>(e.innerText||'').trim().replace(/\\n/g,' ')).filter(Boolean)"""
        btns = page.evaluate(js)
        r["n_upvote"]=sum(1 for b in btns if b.startswith("Upvote"))
        r["has_answer_btn"]=any(b=="Answer" for b in btns)
        r["already_answered"]=any(k in body for k in ["Your answer","You answered"])
        # top answer upvote count (max number after Upvote)
        nums=[]
        for b in btns:
            if b.startswith("Upvote"):
                t=b.replace("Upvote","").strip().replace(",","").replace("K","000")
                if t.isdigit(): nums.append(int(t))
        r["top_upvotes"]=max(nums) if nums else 0
        r["title"]=page.title()[:80]
    except Exception as e:
        r["error"]=str(e)[:150]
    return r

def main():
    out=[]
    with sync_playwright() as pw:
        ctx = P.load_context(pw)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            for u in URLS:
                out.append(assess(page,u))
        finally:
            ctx.close()
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
