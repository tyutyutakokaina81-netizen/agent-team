#!/usr/bin/env python3
"""note の自分の記事一覧が「実際にどう並んでいるか」を吸い出す診断ツール。

attach_thumbnails.py が URL_NOT_FOUND になる原因
（公開記事の探し方/タイトル一致/下書きか公開か）を特定するために、
note.com/notes（および表示されるダッシュボード）上の記事リンクとタイトルを列挙する。

前提: publish_to_note.py --login 済み。
使い方: python3 inspect_note_list.py
出力（このテキストをそのまま貼ってください）:
  - 到達URL / 記事リンク(href)とその表示テキスト / 「公開」「下書き」等のタブ語
"""
from __future__ import annotations
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("Playwright未インストール。setup.sh を先に。")

PROFILE_DIR = Path.home() / ".note_publisher_profile"
URLS = ["https://note.com/notes", "https://note.com/sitesettings", "https://note.com/"]


def launch(p):
    for kw in ({"channel": "chrome"}, {}):
        try:
            return p.chromium.launch_persistent_context(
                str(PROFILE_DIR), headless=False,
                viewport={"width": 1280, "height": 900},
                args=["--disable-blink-features=AutomationControlled"], **kw)
        except Exception:
            continue
    raise RuntimeError("ブラウザ起動失敗")


def dump(page, label):
    print(f"\n========== {label} ==========")
    print("到達URL:", page.url)
    # 記事っぽいリンク（/n/ を含む）を列挙
    links = page.eval_on_selector_all(
        "a",
        "els => els.map(e => ({t:(e.innerText||'').trim().slice(0,40), h:e.getAttribute('href')||''}))"
        ".filter(x => x.h.includes('/n/') || x.h.includes('/notes') || x.h.includes('edit'))")
    seen = set()
    print(f"【記事候補リンク {len(links)}件（最大40）】")
    for x in links[:40]:
        key = x["h"]
        if key in seen:
            continue
        seen.add(key)
        print(f"  text='{x['t']}'  href={x['h']}")
    # タブ/見出しの語（公開/下書き等）
    btns = page.eval_on_selector_all(
        "button,a,div[role=tab]", "els => els.map(e=>(e.innerText||'').trim()).filter(t=>t && t.length<=8)")
    tabs = sorted(set(t for t in btns if any(k in t for k in ("公開", "下書", "記事", "予約", "すべて"))))
    print("【タブ/区分らしき語】", tabs)


def main():
    if not PROFILE_DIR.exists():
        sys.exit("未ログイン。先に python3 publish_to_note.py --login")
    with sync_playwright() as p:
        ctx = launch(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        for u in URLS:
            try:
                page.goto(u)
                page.wait_for_timeout(5000)
                dump(page, u)
            except Exception as e:
                print(f"\n{u} 取得失敗: {e}")
        print("\n--- ここまで。上の出力を全部コピーして貼ってください ---")
        page.wait_for_timeout(1000)
        ctx.close()


if __name__ == "__main__":
    main()
