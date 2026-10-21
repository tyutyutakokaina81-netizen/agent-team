#!/usr/bin/env python3
"""note のコメントに**スレッド返信**する（1件ずつ・cowork 側で実行）。

2026-10-21 cowork 実測（self-fix）:
  - 返信ボタン = `button:has(svg[aria-label="返信"])`（ラベル文字は無いアイコンボタン）
  - 押すと返信用 textarea が出る（記事下の「コメント入力欄」とは別）
  - 送信 = その textarea の form 内の `button[type=submit]:has(svg[aria-label="送信"])`
  - post_comment_replies.py は**トップレベルにコメントを新規投稿**する作りで、送信候補の
    `button:has-text('投稿')` はヘッダの「新規投稿」と取り違えうる。返信はこちらを使う。
  - 確認は API `GET /api/v3/notes/<key>/note_comments` の `is_creator_replied`。

使い方:
  python3 reply_to_comment.py <note_key> "<コメント本文の一部>" "<返信文>"        # DRY
  python3 reply_to_comment.py <note_key> "<コメント本文の一部>" "<返信文>" --go   # 投稿
"""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright
import publish_to_note as P
key,snippet,text,go=sys.argv[1],sys.argv[2],sys.argv[3],"--go" in sys.argv
with sync_playwright() as pw:
    ctx=P.load_context(pw); page=ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(f"https://note.com/safe_canna441/n/{key}",wait_until="domcontentloaded",timeout=45000)
    page.wait_for_timeout(4000)
    page.locator("textarea[aria-label='コメント入力欄']").first.scroll_into_view_if_needed(); page.wait_for_timeout(2500)
    btns=page.locator("button:has(svg[aria-label='返信'])")
    n=btns.count(); print("reply buttons:",n)
    target=None
    for i in range(n):
        b=btns.nth(i)
        # 返信ボタンを含む最小の祖先で、コメント本文 snippet を含むもの
        cont=b.locator(f"xpath=ancestor::*[contains(normalize-space(.),'{snippet}')][1]")
        if cont.count() and len(cont.first.inner_text())<1500:
            target=(b,cont.first); break
    if not target: print("NO_TARGET"); ctx.close(); sys.exit(2)
    b,cont=target
    print("target comment:",cont.inner_text()[:80].replace("\n"," "))
    if not go: print("DRY"); ctx.close(); sys.exit(0)
    b.click(); page.wait_for_timeout(1500)
    tas=page.locator("textarea"); print("textareas:",tas.count())
    ta=None
    for i in range(tas.count()):
        t=tas.nth(i)
        if t.get_attribute("aria-label")!="コメント入力欄" and t.is_visible(): ta=t
    if ta is None:
        ta=cont.locator("textarea").first if cont.locator("textarea").count() else None
    if ta is None: print("NO_REPLY_BOX"); ctx.close(); sys.exit(3)
    ta.click(); ta.type(text,delay=20); page.wait_for_timeout(800)
    send=ta.locator("xpath=ancestor::form[1]").locator("button[type=submit]:has(svg[aria-label='送信'])")
    print("send in form:",send.count())
    if send.count()!=1: print("NO_SEND"); ta.fill(""); ctx.close(); sys.exit(4)
    send.first.click(); page.wait_for_timeout(4000)
    ctx.close()
d=json.load(urllib.request.urlopen(f"https://note.com/api/v3/notes/{key}/note_comments"))
for c in d["data"]: print("API:",c["key"],"replied=",c["is_creator_replied"],"reply_count=",c["reply_count"])
