#!/usr/bin/env python3
"""cowork(2026-07-28便): batch3トピックの実在Quora質問を広く探索し、質問リンクを収集。投稿しない。"""
import sys, json, urllib.parse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright
import publish_to_note as P

QUERIES = [
    ("takaoka", "Is Takaoka worth visiting"),
    ("toyama-worth", "Is Toyama worth visiting"),
    ("alpine-worth", "Tateyama Kurobe Alpine Route worth it"),
    ("shirakawago", "Shirakawa-go from Kanazawa how to get"),
    ("underrated", "underrated places to visit in Japan off beaten path"),
    ("gassho", "stay overnight gassho-zukuri farmhouse Japan"),
    ("hokuriku", "things to do Hokuriku region Japan"),
]

def is_question_link(href, txt):
    if "quora.com/" not in href and not href.startswith("/"): return False
    if any(x in href for x in ["/profile/","/topic/","/spaces","/answer","/following","/notifications"]): return False
    slug = href.split("quora.com")[-1].lstrip("/").split("?")[0]
    if slug.count("-") < 4: return False
    if not txt.endswith("?"): return False
    if len(txt) < 22: return False
    return True

def collect(page, key, q):
    url = "https://www.quora.com/search?q=" + urllib.parse.quote(q)
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(5000)
    for _ in range(4):
        page.mouse.wheel(0, 1700); page.wait_for_timeout(1300)
    anchors = page.query_selector_all("a")
    rows=[]; seen=set()
    for a in anchors:
        href = a.get_attribute("href") or ""
        txt = (a.inner_text() or "").strip().replace("\n"," ")
        if not is_question_link(href, txt): continue
        full = (href if href.startswith("http") else "https://www.quora.com"+href).split("?")[0]
        if full in seen: continue
        seen.add(full)
        rows.append({"q": txt[:150], "url": full})
    return {"key": key, "search": q, "n": len(rows), "found": rows[:10]}

def main():
    out=[]; reddit=None
    with sync_playwright() as pw:
        ctx = P.load_context(pw)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            for key,q in QUERIES:
                try: out.append(collect(page,key,q))
                except Exception as e: out.append({"key":key,"error":str(e)[:150]})
            # Reddit login check (named venue)
            try:
                page.goto("https://www.reddit.com/", wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(4000)
                rb = page.inner_text("body")[:3000]
                reddit = {"url": page.url,
                          "logged_in_guess": ("Log In" not in rb[:400]) and ("Create Account" not in rb[:400])}
            except Exception as e:
                reddit = {"error": str(e)[:150]}
        finally:
            ctx.close()
    print("===QUORA_FIND2===")
    print(json.dumps({"quora": out, "reddit": reddit}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
