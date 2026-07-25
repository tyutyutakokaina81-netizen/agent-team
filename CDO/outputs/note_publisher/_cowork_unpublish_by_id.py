#!/usr/bin/env python3
"""cowork: 指定 note ID を「下書きに戻す」化する（重複解消用）。削除ではない。
使い方: python3 _cowork_unpublish_by_id.py <NID> [--go]
  --go なし=DRY（カード/メニュー実測のみ） / --go で下書きに戻す。

2026-07-25 実測メモ（self-fix）:
  - editor.note.com/notes/<id>/edit のメニューに「下書きに戻す」は無い（削除/公開に進む/変更履歴のみ）。
  - note.com/notes 管理一覧のカード右端「…」ケバブに「編集/複製/下書きに戻す/…/削除」がある。
  - カードのボタンは aria-label 無し＝ancestor xpath だと一覧全体を拾い誤爆する。
    → カードリンクの bounding_box と同じ行(y近接)・右側(x>link)のボタンを幾何で特定して開く方式が確実。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright
import publish_to_note as P

args = [a for a in sys.argv[1:] if not a.startswith("--")]
if not args:
    print("usage: _cowork_unpublish_by_id.py <NID> [--go]"); sys.exit(1)
NID = args[0]
GO = "--go" in sys.argv

MENU_SEL = '[role="menuitem"],[role="menu"] button,[role="menu"] a,[role="menu"] li'


def main():
    with sync_playwright() as pw:
        ctx = P.load_context(pw)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto("https://note.com/notes", wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(4000)
            found = False
            for _ in range(30):
                if page.query_selector(f'a[href*="{NID}"]'):
                    found = True; break
                page.mouse.wheel(0, 2500); page.wait_for_timeout(700)
            if not found:
                print(f"CARD_NOT_FOUND: {NID}"); return
            link = page.query_selector(f'a[href*="{NID}"]')
            link.scroll_into_view_if_needed(); page.wait_for_timeout(1000)
            lb = link.bounding_box()
            # 同じ行・リンク右側のボタン（=カード右端のケバブ）を右から順に試す
            cands = []
            for b in page.query_selector_all('button'):
                try:
                    bb = b.bounding_box()
                    if not bb:
                        continue
                    if abs((bb['y'] + bb['height'] / 2) - (lb['y'] + lb['height'] / 2)) < 38 and bb['x'] > lb['x'] + 40:
                        cands.append((bb['x'], b))
                except Exception:
                    pass
            cands.sort(reverse=True)
            for _x, b in cands:
                try:
                    b.scroll_into_view_if_needed(); page.wait_for_timeout(400)
                    b.click(); page.wait_for_timeout(1200)
                except Exception:
                    continue
                items = page.query_selector_all(MENU_SEL)
                hit = None
                for i in items:
                    t = (i.inner_text() or "").strip()
                    if "下書きに戻す" in t or ("非公開" in t and "設定" not in t):
                        hit = i; break
                if hit:
                    print("FOUND unpublish item:", (hit.inner_text() or "").strip())
                    if not GO:
                        print("DRY-RUN: --go で下書きに戻します"); return
                    hit.click(); page.wait_for_timeout(1500)
                    for conf in ['button:has-text("下書きに戻す")', 'button:has-text("戻す")',
                                 'button:has-text("OK")', 'button:has-text("はい")']:
                        c = page.query_selector(conf)
                        if c:
                            print("confirm:", conf); c.click(); page.wait_for_timeout(1500); break
                    print("DONE: 下書きに戻す 実行（公開URLは404になる想定）")
                    return
                page.keyboard.press("Escape"); page.wait_for_timeout(400)
            print("KEBAB_NOT_FOUND: 同行右側ボタンに『下書きに戻す』メニューが見つからない")
        finally:
            ctx.close()


if __name__ == "__main__":
    main()
