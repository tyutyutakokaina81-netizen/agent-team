#!/usr/bin/env python3
"""公開済み note 記事の **末尾にフォロー導線＋あわせて読む3本を足す**（owner の Mac で実行）。

なぜ（2026-10-02 に数えて分かったこと）:
  公開210本のうち **他記事へのリンクがあるのは10本(4%)／フォローの一言があるのは7本(3%)**。
  1本読んだ人が次へ行く道も、フォローする理由も、ほとんどの記事に無かった。
  フッターを作る仕組み（note_footer/gen_footers.py）は 2026-06-07 からあったのに
  **一度も記事に適用されていなかった**。マガジン196本・英語141本と同じ型。

安全のために:
  - **本文を全置換しない。末尾に足すだけ**（置換すると本文中の写真が消える）。
  - 押すのは「更新する」だけ。下書きなら押さずに止まる。DO_NOT_TOUCH は開く前に弾く。
  - すでに「あわせて読む」がある記事は触らない。
  - 足す前の本文を `_before_update/<NID>_follow.txt` に保存する。
  - 既定は読むだけ。実際に足すのは `--go` のときだけ。

使い方:
  python3 append_follow_footer.py <NID> [--go]
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import publish_to_note as P          # noqa: E402
import _note_safety as _safety       # noqa: E402

EDIT_URL = "https://editor.note.com/notes/{nid}/edit/"
PUBLISH_URL = "https://editor.note.com/notes/{nid}/publish/"
BACKUP_DIR = Path(__file__).resolve().parent / "_before_update"
BLOCKS = Path(__file__).resolve().parents[3] / "ops/follow_blocks.tsv"


def load_block(nid: str):
    if not BLOCKS.exists():
        return None
    for line in BLOCKS.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        c = line.split("\t")
        if len(c) >= 3 and c[0] == nid:
            return c[2].replace("\\n", "\n")
    return None


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    go = "--go" in sys.argv
    if not args:
        print(__doc__)
        return 1
    nid = args[0]

    why = _safety.blocked_reason(nid)
    if why:
        print(f"✗ {nid} は触らない記事です: {why}")
        return 1

    blk = load_block(nid)
    if not blk:
        print(f"✗ {nid} のブロックがありません → `python3 ops/build_follow_blocks.py` を先に回す")
        return 1
    print(f"■ 足す内容（{len(blk)}字）\n{blk[:160]}…")

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
                print("✗ 本文を読めませんでした。**何も触らずに**終わります")
                return 2
            print(f"\n■ いまの記事\n  本文: {len(cur)}字")

            if "あわせて読む" in cur:
                print("SKIP_HAS_FOOTER: すでに導線が入っています。触りません")
                return 0

            BACKUP_DIR.mkdir(exist_ok=True)
            (BACKUP_DIR / f"{nid}_follow.txt").write_text(cur, encoding="utf-8")

            if not go:
                print("\nDRY-RUN: 何も変更していません。実行するなら --go を付けてください")
                return 0

            editor.click()
            page.wait_for_timeout(200)
            for key in ("Meta+ArrowDown", "Control+End", "End"):
                try:
                    page.keyboard.press(key)
                    page.wait_for_timeout(150)
                except Exception:
                    continue
            page.keyboard.press("Enter")
            page.wait_for_timeout(200)
            for line in blk.split("\n"):
                if line:
                    page.keyboard.insert_text(line)
                page.keyboard.press("Enter")
                page.wait_for_timeout(30)
            page.wait_for_timeout(800)

            try:
                after = editor.inner_text() or ""
            except Exception:
                after = ""
            if "あわせて読む" not in after:
                print("✗ 足したはずの導線が本文に見えません。**保存せずに**終わります")
                return 2
            print(f"✅ 末尾に導線を足しました（{len(cur)}字 → {len(after)}字）")

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
