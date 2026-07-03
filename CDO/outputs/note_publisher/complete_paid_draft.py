#!/usr/bin/env python3
"""既存の有料下書きを開いて「投稿する」まで完遂する（重複ドラフトを作らない）。

publish_paid_note.py は毎回 editor.note.com/new から新規下書きを作るため、
既に本文・有料ライン・価格まで仕込んである下書き(nea8b690cde14 等)を完遂するには
そのIDを直接開いて最終モーダルだけ突破する必要がある。worker-prompt.txt の6段階法を実装。

使い方:
  python3 complete_paid_draft.py <note_id> --inspect             # 読み取りのみ（公開しない）
  python3 complete_paid_draft.py <note_id> --publish --price 300 # 投稿する まで（公開1回のみ）
安全: 既定=inspect。--publish時のみ最終ボタン。公開状態へ遷移したら即停止（二重公開防止）。
"""
import argparse, re, sys
from pathlib import Path
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("Playwright未インストール")

PROFILE_DIR = Path.home() / ".note_publisher_profile"

def _launch(p):
    for kw in ({"channel": "chrome"}, {}):
        try:
            return p.chromium.launch_persistent_context(
                str(PROFILE_DIR), headless=False, viewport={"width":1360,"height":940},
                args=["--disable-blink-features=AutomationControlled"], **kw)
        except Exception:
            continue
    raise RuntimeError("ブラウザ起動失敗")

def _dump_buttons(page, label):
    print(f"\n---- {label}: buttons/labels ----")
    items = page.eval_on_selector_all(
        "button,[role=button],label,a",
        "els=>els.map(e=>({t:(e.innerText||e.getAttribute('aria-label')||'').trim().slice(0,30),tag:e.tagName,dis:e.disabled===true})).filter(x=>x.t)")
    seen=set()
    for x in items:
        k=(x['t'],x['tag'])
        if k in seen: continue
        seen.add(k)
        print(f"  [{x['tag']}]{'(disabled)' if x['dis'] else ''} '{x['t']}'")

def _pid(page):
    m=re.search(r"/(n[a-z0-9]{8,})", page.url)
    return m.group(1) if m else None

def run(note_id, do_publish, price):
    edit_url=f"https://editor.note.com/notes/{note_id}/edit"
    with sync_playwright() as p:
        ctx=_launch(p); page=ctx.pages[0] if ctx.pages else ctx.new_page()
        print(f"🔗 開く: {edit_url}")
        page.goto(edit_url, wait_until="domcontentloaded"); page.wait_for_timeout(4000)
        print("到達URL:", page.url)
        try:
            te=page.locator('textarea[placeholder="記事タイトル"], input[placeholder*="タイトル"], h1[contenteditable="true"]').first
            tv=te.input_value() if te.count() else ""
        except Exception: tv=""
        try: body=page.locator('div[contenteditable="true"]').first.inner_text()
        except Exception: body=""
        print(f"📝 タイトル: {tv[:60]}")
        print(f"📄 本文文字数: {len(body)}")
        try:
            btn=page.locator('button:has-text("公開に進む"), button:has-text("公開設定")').first
            btn.wait_for(state="visible", timeout=8000); btn.click()
            print("▶️  『公開に進む』クリック")
            try: page.wait_for_url("**/publish**", timeout=12000)
            except Exception: page.wait_for_timeout(3000)
        except Exception as e:
            print(f"⚠️  『公開に進む』未検出: {e}")
        page.wait_for_timeout(2000)
        print("公開画面URL:", page.url)
        try: vals=page.evaluate("()=>[...document.querySelectorAll('input')].map(i=>i.value).filter(Boolean)")
        except Exception: vals=[]
        print(f"💴 input値: {vals}")
        _dump_buttons(page, "publish画面")
        if not do_publish:
            print("\n📋 inspectモード：公開しません。")
            ctx.close(); return None

        if price and str(price) not in vals:
            for sel in ('label:has-text("有料")','input[value="paid"]','text=有料'):
                try:
                    el=page.locator(sel).first
                    if el.is_visible(timeout=1000): el.click(); page.wait_for_timeout(1000); break
                except Exception: continue
            for sel in ('input[type="number"]','input[inputmode="numeric"]','input[placeholder="300"]'):
                try:
                    inp=page.locator(sel).first
                    if inp.is_visible(timeout=1200): inp.click(); inp.fill(""); inp.fill(str(price)); page.wait_for_timeout(500); break
                except Exception: continue
            try:
                b=page.locator('button:has-text("このラインより先を有料にする")').first
                if b.is_visible(timeout=1500): b.click(); page.wait_for_timeout(800)
            except Exception: pass

        def _confirmed():
            page.wait_for_timeout(1500)
            if "/publish" not in page.url and _pid(page): return True
            if page.locator('text=公開しました').count()>0 or page.locator('text=投稿しました').count()>0: return True
            return False
        def find_btn():
            for sel in ('button:has-text("投稿する")','button:has-text("公開する")','[role="dialog"] button:has-text("投稿する")'):
                loc=page.locator(sel).first
                if loc.count() and loc.is_visible(): return loc
            return None
        def m1():
            b=find_btn();
            if not b: return False
            box=b.bounding_box()
            if not box: return False
            page.mouse.click(box["x"]+box["width"]/2, box["y"]+box["height"]/2); return True
        def m2():
            ln=page.locator('text=ここから有料').first
            if ln.count():
                lb=ln.bounding_box()
                if lb: page.mouse.click(lb["x"]+lb["width"]/2, lb["y"]+lb["height"]/2); page.wait_for_timeout(500)
            b=find_btn()
            if b: b.click(timeout=3000); return True
            return False
        def m3():
            b=find_btn()
            if not b: return False
            b.focus(); page.keyboard.press("Enter"); return True
        def m4():
            b=find_btn()
            if not b: return False
            b.focus(); page.keyboard.press("Space"); return True
        def m5():
            return bool(page.evaluate("""()=>{const bs=[...document.querySelectorAll('button')].filter(b=>/投稿する|公開する/.test(b.innerText));if(!bs.length)return false;const b=bs[bs.length-1];for(const t of['pointerdown','pointerup','click']){b.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window}));}return true;}"""))
        def m6():
            return bool(page.evaluate("""()=>{const d=document.querySelector('[role=dialog]')||document;const f=d.querySelector('form');if(!f)return false;f.submit();return true;}"""))
        methods=[("実マウス座標クリック",m1),("境界行クリック→ボタン",m2),("focus+Enter",m3),("focus+Space",m4),("JS pointer sequence",m5),("form submit",m6)]
        start=page.url
        for name,fn in methods:
            try:
                print(f"\n🚀 手段: {name}")
                ok=fn()
                if not ok: print("   （未検出/未実行）")
                page.wait_for_timeout(1500)
                for lbl in ("有料エリア設定で投稿","投稿する","公開する","OK"):
                    try:
                        c=page.locator(f'[role="dialog"] button:has-text("{lbl}")').last
                        if c.count() and c.is_visible(): c.click(); page.wait_for_timeout(1200); break
                    except Exception: pass
                if _confirmed():
                    pid=_pid(page) or note_id
                    print(f"\n✅ 公開成功: https://note.com/safe_canna441/{pid}")
                    print(f"最終URL: {page.url}")
                    ctx.close(); return pid
            except Exception as e:
                print(f"   手段失敗: {e}")
        print("\n🛑 全6手段で最終ボタン突破できず。下書きのまま保持（未公開）。")
        print(f"   現在URL: {page.url} (start:{start})")
        ctx.close(); return None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("note_id"); ap.add_argument("--publish",action="store_true"); ap.add_argument("--price",type=int,default=None)
    a=ap.parse_args()
    pid=run(a.note_id,a.publish,a.price)
    if a.publish: print("\nRESULT:", ("PUBLISHED "+pid) if pid else "NOT_PUBLISHED (draft kept)")

if __name__=="__main__":
    main()
