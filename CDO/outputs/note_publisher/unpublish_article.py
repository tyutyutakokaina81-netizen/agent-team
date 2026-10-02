#!/usr/bin/env python3
"""公開中の note 記事を **下書きに戻す**（owner の Mac で実行）。

なぜ要るのか（2026-10-02）:
  `nc7a3522ade60`（氷見牛の2本目＝重複記事）が 2026-09-24 に誤って再公開されてから、
  **9日間ずっと公開されたまま**だった。原因は「note の画面で手でクリックする」以外に
  方法が無く、owner の作業として積まれ続けたこと。R34 はそれを毎日 BROKEN で出していたが、
  **検知しても手段が無ければ減らない**。だからコマンドにする。

安全のために:
  - **DO_NOT_TOUCH に載っている記事だけ**を対象にする（間違って普通の記事を下げない）。
  - 下げる前の本文を `_before_update/<NID>_unpublish.txt` に保存する。
  - 既定は読むだけ。実際に下げるのは `--go` のときだけ。
  - 「下書きに戻す」が見つからなければ**何もせずに終わる**（別のボタンを押さない）。

使い方:
  python3 unpublish_article.py <NID> [--go]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import publish_to_note as P          # noqa: E402
import _note_safety as _safety       # noqa: E402

EDIT_URL = "https://editor.note.com/notes/{nid}/edit/"
BACKUP_DIR = Path(__file__).resolve().parent / "_before_update"

# 「下書きに戻す」に相当する押し先。note の画面は変わるので複数持つ。
DRAFT_LABELS = ("下書きに戻す", "下書きに保存", "非公開にする")


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    go = "--go" in sys.argv
    if not args:
        print(__doc__)
        return 1
    nid = args[0]

    why = _safety.DO_NOT_TOUCH.get(nid)
    if not why:
        print(f"✗ {nid} は DO_NOT_TOUCH に載っていません。")
        print("  このコマンドは**取り下げると決めた記事だけ**を対象にします。")
        print("  下げる必要があるなら、先に _note_safety.py の DO_NOT_TOUCH に理由とともに足してください。")
        return 1
    print(f"■ 対象: {nid}\n  理由: {why}")

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
            try:
                cur = editor.inner_text() or ""
            except Exception:
                cur = ""
            print(f"  いまの本文: {len(cur)}字")
            if cur.strip():
                BACKUP_DIR.mkdir(exist_ok=True)
                (BACKUP_DIR / f"{nid}_unpublish.txt").write_text(cur, encoding="utf-8")
                print(f"  下げる前の本文を保存しました: {BACKUP_DIR / (nid + '_unpublish.txt')}")

            def _find():
                for label in DRAFT_LABELS:
                    for sel in (f'button:has-text("{label}")', f'[role="menuitem"]:has-text("{label}")'):
                        try:
                            loc = page.locator(sel).last
                            if loc.count() > 0 and loc.is_visible(timeout=800):
                                return (label, loc)
                        except Exception:
                            continue
                    try:
                        loc = page.get_by_text(label, exact=False).first
                        if loc.count() > 0 and loc.is_visible(timeout=800):
                            return (label, loc)
                    except Exception:
                        continue
                return None

            found = _find()
            if not found:
                # ★2026-10-02 実測: 直接は見つからなかった。note は「…」のメニューの中に
                #   入れていることがあるので、**開いてからもう一度探す**。
                for opener in ("その他", "もっと見る", "メニュー", "設定"):
                    try:
                        b = page.get_by_role("button", name=opener)
                        if b.count() > 0 and b.first.is_visible(timeout=800):
                            print(f"  「{opener}」を開いて探します")
                            b.first.click()
                            page.wait_for_timeout(900)
                            found = _find()
                            if found:
                                break
                    except Exception:
                        continue
            if not found:
                # **画面に何があるかを出す。** 見えないまま「無い」と言うと、次に何を直せばよいか
                #   分からず、同じ往復を繰り返すことになる（9日間そうなっていた）。
                print("✗ 「下書きに戻す」に当たるものが画面にありません。**何も押していません。**")
                print("\n  画面に見えているボタン:")
                try:
                    btns = page.locator("button")
                    seen = []
                    for i in range(min(btns.count(), 60)):
                        try:
                            b = btns.nth(i)
                            if not b.is_visible():
                                continue
                            t = (b.inner_text() or "").strip().replace("\n", " ")[:28]
                            a = (b.get_attribute("aria-label") or "").strip()[:28]
                            lab = t or a
                            if lab and lab not in seen:
                                seen.append(lab)
                        except Exception:
                            continue
                    for x in seen:
                        print(f"    - {x}")
                    if not seen:
                        print("    （1つも読めませんでした）")
                except Exception as e:
                    print(f"    （一覧を取れませんでした: {type(e).__name__}）")
                print("\n  この一覧をそのまま Claude に貼ってください。押し先を特定します。")
                print("  ※ すでに下書きなら、そもそも下げる必要はありません。")
                return 2
            print(f"  見つけたもの: 「{found[0]}」")

            if not go:
                print("\nDRY-RUN: 何も変更していません。実行するなら --go を付けてください")
                return 0

            found[1].click()
            page.wait_for_timeout(1500)
            # 確認ダイアログが出る場合に備える
            for label in ("下書きに戻す", "OK", "はい"):
                try:
                    b = page.get_by_role("button", name=label)
                    if b.count() > 0 and b.first.is_visible():
                        b.first.click()
                        page.wait_for_timeout(1200)
                        break
                except Exception:
                    continue
            print(f"\n✅ 下書きに戻しました: {nid}")
            print("   note の画面で、記事が一覧から消えている（下書きにある）ことを確認してください。")
            print("   確認できたら _note_safety.py の『要再取り下げ』の文言を消してください。")
            return 0
        finally:
            try:
                ctx.close()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
