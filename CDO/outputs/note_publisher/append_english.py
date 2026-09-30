#!/usr/bin/env python3
"""公開済み note 記事の **末尾に英語要約だけを足す**（owner の Mac で実行）。

なぜ update_article.py ではなく別の道具なのか（2026-09-30）:
  update_article.py は**本文を全置換する**。置換では `[写真X]` を入れないと決めてあるので、
  写真つきで公開した記事に使うと **本文中の写真が消える**。今回直したいのは
  「英語が本文に入っていない」1点だけなので、**消さずに足す**口を作る。

なぜ直すのか:
  publisher は `## 本文` 直下の ``` ブロックだけを note に貼る。英語要約は
  `## English Summary` セクション＝**ブロックの外**に書いていたため、md には英語があるのに
  **note 上は日本語だけ**で公開されていた。5月からの累計 141本。North Star は
  「海外読者に読まれる」なので、書いた英語がそのまま捨てられていたことになる。

安全のために:
  - 押すのは「更新する」だけ（`_note_safety.save_published`）。下書きなら押さずに止まる。
  - DO_NOT_TOUCH は開く前に弾く。
  - **すでに英文が入っている記事は触らない**（二重に足さない）。
  - 足す前の本文を `_before_update/<NID>.txt` に保存する。
  - 既定は読むだけ。実際に足すのは `--go` のときだけ。
  - タイトル・写真・見出し画像・タグ・マガジンには**一切触らない**。

使い方:
  python3 append_english.py <NID> <記事md> [--go]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import publish_to_note as P          # noqa: E402
import _note_safety as _safety       # noqa: E402

EDIT_URL = "https://editor.note.com/notes/{nid}/edit/"
PUBLISH_URL = "https://editor.note.com/notes/{nid}/publish/"
BACKUP_DIR = Path(__file__).resolve().parent / "_before_update"
SEP = "――――――――――"
SENT = re.compile(r"\b(?:[A-Za-z][A-Za-z'\-,\.]*\s+){7,}[A-Za-z]")


def english_block(md_text: str) -> str:
    """md の本文ブロックから `【English】` 以降を取り出す（inline_english.py が入れたもの）。"""
    m = re.search(r"##\s*本文.*?\n```\n(.+?)\n```", md_text, re.S)
    if not m:
        return ""
    body = m.group(1)
    i = body.find("【English】")
    if i < 0:
        return ""
    chunk = body[i:]
    # 見出し画像クレジット行は本文の最後に置く約束なので、あれば落とす
    lines = [l for l in chunk.split("\n") if "見出し画像" not in l]
    return "\n".join(lines).strip()


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
    P._assert_not_paid_article(text, md)
    blk = english_block(text)
    if not blk:
        print(f"✗ md に `【English】` が無い: {md.name}"
              "  → 先に `python3 ops/inline_english.py --go` を回してください")
        return 1
    print(f"■ 足す内容（{len(blk)}字）\n  {blk[:90]}…")

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

            editor = page.locator('div[contenteditable="true"]').last
            editor.wait_for(state="visible", timeout=20000)
            try:
                cur = editor.inner_text() or ""
            except Exception:
                cur = ""
            if not cur.strip():
                print("✗ 本文を読めませんでした。画面が変わった可能性があるので"
                      "**何も触らずに**終わります")
                return 2
            print(f"\n■ いまの記事\n  本文: {len(cur)}字"
                  f"\n  冒頭: {' / '.join(x.strip() for x in cur.splitlines() if x.strip())[:70]}")

            if SENT.search(cur) or "【English】" in cur:
                print("SKIP_HAS_ENGLISH: すでに英文が入っています。触りません")
                return 0

            BACKUP_DIR.mkdir(exist_ok=True)
            (BACKUP_DIR / f"{nid}.txt").write_text(
                f"(append_english の前)\n\n----\n\n{cur}\n", encoding="utf-8")

            if not go:
                print("\nDRY-RUN: 何も変更していません。実行するなら --go を付けてください")
                return 0

            editor.click()
            page.wait_for_timeout(200)
            # 末尾へ。macOS は Meta+ArrowDown が文書末尾
            for key in ("Meta+ArrowDown", "Control+End", "End"):
                try:
                    page.keyboard.press(key)
                    page.wait_for_timeout(150)
                except Exception:
                    continue
            page.keyboard.press("Enter")
            page.wait_for_timeout(200)
            for i, line in enumerate([SEP] + blk.split("\n")):
                if line:
                    page.keyboard.insert_text(line)
                page.keyboard.press("Enter")
                page.wait_for_timeout(30)
            page.wait_for_timeout(800)

            try:
                after = editor.inner_text() or ""
            except Exception:
                after = ""
            if not SENT.search(after):
                print("✗ 足したはずの英文が本文に見えません。**保存せずに**終わります")
                return 2
            print(f"✅ 末尾に英語を足しました（{len(cur)}字 → {len(after)}字）")

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
