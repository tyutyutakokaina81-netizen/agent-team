#!/usr/bin/env python3
"""cowork: 既公開noteのタイトルだけを直す（本文は触らない）。
publish_to_note.py の TITLE_SELECTOR とダイアログ処理を再利用。
使い方: python3 _cowork_fix_title.py <NID> "<新タイトル>" [--go]
  --go なし=編集画面まで開いて現状表示のみ / --go でタイトル差し替え→更新公開。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright
import publish_to_note as P

args = [a for a in sys.argv[1:] if not a.startswith("--")]
if len(args) < 2:
    print('usage: _cowork_fix_title.py <NID> "<new title>" [--go]'); sys.exit(1)
NID, NEW_TITLE = args[0], args[1]
GO = "--go" in sys.argv


def main():
    with sync_playwright() as pw:
        ctx = P.load_context(pw)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto(f"https://editor.note.com/notes/{NID}/edit/",
                      wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2500)
            # ダイアログ除去（下書き復元/通知許可等）
            for _ in range(3):
                page.keyboard.press("Escape"); page.wait_for_timeout(250)
            title_input = page.locator(P.TITLE_SELECTOR).first
            title_input.wait_for(state="visible", timeout=20000)
            cur = (title_input.inner_text() or title_input.input_value() if hasattr(title_input, "input_value") else "") if False else ""
            try:
                cur = title_input.inner_text()
            except Exception:
                pass
            print("現タイトル(推定):", repr(cur)[:80])
            if not GO:
                print("DRY-RUN: --go で『%s』へ差し替えて更新します" % NEW_TITLE)
                return
            # タイトルを全選択→削除→新タイトル入力
            # ★macOSの全選択は Meta+A（Control+Aだと効かず旧タイトルが残る＝実害）。
            title_input.click()
            page.wait_for_timeout(200)
            for _ in range(3):
                page.keyboard.press("Meta+A")
                page.keyboard.press("Delete")
                page.wait_for_timeout(200)
                try:
                    left = (title_input.inner_text() or "").strip()
                except Exception:
                    left = ""
                if not left:
                    break
                # 残っていれば末尾からBackspaceで消し切る
                page.keyboard.press("End")
                for _ in range(len(left) + 5):
                    page.keyboard.press("Backspace")
                page.wait_for_timeout(150)
            try:
                print("クリア後:", repr((title_input.inner_text() or "").strip())[:40])
            except Exception:
                pass
            title_input.type(NEW_TITLE)
            page.wait_for_timeout(500)
            print("✅ 新タイトル入力:", NEW_TITLE)
            # 下書き保存で確定
            try:
                ds = page.locator('button:has-text("下書き保存")').first
                if ds.is_visible(timeout=2000):
                    ds.click(); page.wait_for_timeout(2500); print("✅ 下書き保存で確定")
            except Exception as e:
                print("下書き保存省略:", e)
            # 公開に進む
            try:
                page.locator('button:has-text("公開に進む")').first.click()
                try:
                    page.wait_for_url("**/publish/**", timeout=15000)
                except Exception:
                    page.wait_for_timeout(3000)
            except Exception as e:
                print("公開に進む失敗:", e)
            if "/publish" not in page.url:
                page.goto(f"https://editor.note.com/notes/{NID}/publish/",
                          wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(2500)
            # 更新/投稿する（既公開の更新は『更新する』のこともある）
            page.wait_for_timeout(1000)
            clicked = False
            for lbl in ("更新する", "投稿する", "公開する"):
                try:
                    b = page.locator(f'button:has-text("{lbl}")').first
                    if b.is_visible(timeout=3000):
                        b.click(); page.wait_for_timeout(2500)
                        print(f"✅ 『{lbl}』クリック")
                        clicked = True
                        break
                except Exception:
                    continue
            # 確認ダイアログ
            for lbl in ("更新する", "投稿する", "公開する", "OK"):
                try:
                    c = page.locator(f'[role="dialog"] >> button:has-text("{lbl}")').last
                    if c.is_visible(timeout=800):
                        c.click(); page.wait_for_timeout(1500); break
                except Exception:
                    continue
            page.wait_for_timeout(3000)
            print("最終URL:", page.url, "clicked=", clicked)
        finally:
            ctx.close()


if __name__ == "__main__":
    main()
