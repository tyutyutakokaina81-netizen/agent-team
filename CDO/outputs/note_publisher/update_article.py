#!/usr/bin/env python3
"""公開済み note 記事の **タイトルと本文を書き直した md で差し替える**（owner の Mac で実行）。

なぜ要るのか:
  書き直した記事を出す方法が、これまで無かった。`_cowork_fix_title.py` はタイトルだけ、
  `publish_to_note.py` は**新規投稿**しかできない。書き直しを新規で出すと
  **同じ題材が2本**になる（2026-07-04 の氷見牛と同じ事故）。だから「更新」の口を作る。

安全のために決めてあること:
  - 押すのは **「更新する」だけ**（`_note_safety.save_published`）。
    「投稿する」しか無い＝下書きのときは **押さずに止まる**。
    2026-09-24 に、下書きへ戻した重複記事を「投稿する」で再公開した事故があったため。
  - 下書きへ戻した記事（DO_NOT_TOUCH）は開く前に弾く。
  - **差し替える前の本文をファイルに保存する**。消えたら戻せないので。
  - 既定は `--probe`（読むだけ）。実際に書き換えるのは `--go` を付けたときだけ。
  - 本文中の `[写真X]` は**入れない**（画像の再挿入は別作業）。何個落としたかを必ず出す。
  - 有料記事の md は受け付けない（全文無料公開の事故を避ける）。

使い方:
  python3 update_article.py <NID> <記事md> [--go]
    例) python3 update_article.py na889c3862499 \
          "CMO/outputs/2026-06-01_note記事_富山ブラックラーメン_労働者の塩分補給.md"
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import publish_to_note as P          # noqa: E402
import _note_safety as _safety       # noqa: E402

EDIT_URL = "https://editor.note.com/notes/{nid}/edit/"
PUBLISH_URL = "https://editor.note.com/notes/{nid}/publish/"
BACKUP_DIR = Path(__file__).resolve().parent / "_before_update"


def _read_title(loc) -> str:
    """タイトル欄の中身を読む。

    2026-09-25 実測: `inner_text()` だけだと**空で返る**（note のタイトル欄は textarea で、
    テキストは value に入っているため）。owner の実行で「いまの記事のタイトル」が空欄で出て、
    **差し替え前に何を確認すればよいか分からない状態**になった。value 側も見る。
    """
    for how in ("input_value", "inner_text"):
        try:
            v = (getattr(loc, how)() or "").strip()
            if v:
                return v
        except Exception:
            continue
    try:
        v = (loc.get_attribute("value") or "").strip()
        if v:
            return v
    except Exception:
        pass
    return ""


def _clear(page, loc):
    """入力欄を空にする。macOS の全選択は Meta+A（Control+A では消えない）。"""
    loc.click()
    page.wait_for_timeout(200)
    for _ in range(3):
        page.keyboard.press("Meta+A")
        page.keyboard.press("Delete")
        page.wait_for_timeout(200)
        try:
            left = (loc.inner_text() or "").strip()
        except Exception:
            left = ""
        if not left:
            return True
        page.keyboard.press("End")
        for _ in range(len(left) + 5):
            page.keyboard.press("Backspace")
        page.wait_for_timeout(150)
    return False


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    go = "--go" in sys.argv
    if len(args) < 2:
        print(__doc__)
        return 1
    nid, md = args[0], Path(args[1])
    if not md.exists():
        print(f"✗ md が無い: {md}")
        return 1

    why = _safety.blocked_reason(nid)
    if why:
        print(f"✗ {nid} は触らない記事です: {why}")
        return 1

    text = md.read_text(encoding="utf-8")
    P._assert_not_paid_article(text, md)          # 有料記事は受け付けない
    title, body, photos, tags, mags = P.parse_article(md)
    if photos:
        print(f"⚠ 本文の [写真] {len(photos)}個は入れません（画像の再挿入は別作業）")
    print(f"■ 差し替える内容\n  タイトル: {title}\n  本文: {len(body)}字 / タグ {len(tags)}個 / マガジン {mags}")
    print("  ※ タグとマガジンはここでは触りません（set_tags.py / set_magazine.py の担当）")

    P._require_playwright()
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        ctx = P.load_context(pw)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto(EDIT_URL.format(nid=nid), wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2500)
            for _ in range(3):
                page.keyboard.press("Escape")
                page.wait_for_timeout(250)

            title_input = page.locator(P.TITLE_SELECTOR).first
            title_input.wait_for(state="visible", timeout=20000)
            cur_title = _read_title(title_input)
            editor = page.locator('div[contenteditable="true"]').last
            try:
                cur_body = editor.inner_text() or ""
            except Exception:
                cur_body = ""
            print(f"\n■ いまの記事\n  タイトル: {cur_title[:60] or '（読めませんでした）'}\n  本文: {len(cur_body)}字")
            # タイトルが読めないことがある（欄の作りによって取り方が違う）。
            # **確認材料が何も出ないまま --go を促すのは危ない**ので、本文の冒頭も出す。
            _head = " / ".join(x.strip() for x in cur_body.splitlines() if x.strip())[:70]
            print(f"  本文の冒頭: {_head}")

            if not cur_body.strip():
                print("✗ 本文を読めませんでした。画面が変わった可能性があるので、"
                      "何も触らずに終わります（--go でも書き換えません）")
                return 2

            BACKUP_DIR.mkdir(exist_ok=True)
            bk = BACKUP_DIR / f"{nid}.txt"
            bk.write_text(f"{cur_title}\n\n----\n\n{cur_body}\n", encoding="utf-8")
            print(f"  差し替え前の内容を保存しました: {bk}")

            if not go:
                print("\nDRY-RUN: 何も変更していません。実行するなら同じコマンドに --go を付けてください")
                return 0

            if not _clear(page, title_input):
                print("✗ タイトルを空にできませんでした。中断します")
                return 2
            page.keyboard.insert_text(title)
            print("✅ タイトルを差し替え")

            editor.click()
            page.wait_for_timeout(200)
            page.keyboard.press("Meta+A")
            page.keyboard.press("Delete")
            page.wait_for_timeout(400)
            paragraphs = P.split_body_by_photo_placeholders(body)
            for kind, val in paragraphs:
                if kind != "text":
                    continue                      # [写真X] は入れない
                lines = val.split("\n")
                for i, line in enumerate(lines):
                    if line:
                        page.keyboard.insert_text(line)
                    if i < len(lines) - 1:
                        page.keyboard.press("Enter")
                        page.wait_for_timeout(30)
            print("✅ 本文を差し替え")
            page.wait_for_timeout(800)

            st = _safety.save_published(page, nid, PUBLISH_URL)
            print(f"\n結果: {st}")
            if st.startswith("UPDATED"):
                print(f"  https://note.com/{P.AUTHOR_ID}/n/{nid}")
                return 0
            return 2
        finally:
            try:
                ctx.close()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
