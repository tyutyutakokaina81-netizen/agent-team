#!/usr/bin/env python3
"""記事を**クリエイターページに固定表示**する（owner の Mac で実行）。

なぜ（2026-10-02）:
  プロフィールに来た人が最初に見る1本を決められる。案内記事（10,254字・28本へのリンク・
  何を書く人かが全部書いてある）を置けば、フォローの判断材料がその1本で足りる。
  ブラウザで3クリックの作業だが、**手順書に書くと動かない**ことを何度も見たのでコマンドにする。

安全のために:
  - 押すのは「固定」系のものだけ。見つからなければ**何も押さずに終わり、画面の項目を全部出す**
    （見えないまま「無い」と言うと、次に何を直せばよいか分からず往復が続く）。
  - 記事の本文・タイトル・タグには一切触らない。

使い方:
  python3 pin_article.py <NID> [--go]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import publish_to_note as P          # noqa: E402

VIEW_URL = "https://note.com/{author}/n/{nid}"
PIN_LABELS = ("クリエイターページに固定表示", "固定表示", "ピン留め", "固定する")
UNPIN_HINT = ("固定表示を解除", "固定を解除")


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    go = "--go" in sys.argv
    if not args:
        print(__doc__)
        return 1
    nid = args[0]

    P._require_playwright()
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        ctx = P.load_context(pw)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            url = VIEW_URL.format(author=P.AUTHOR_ID, nid=nid)
            print(f"■ 開く: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2500)

            # 「…」メニューを開く
            opened = False
            for name in ("その他", "もっと見る", "メニュー", "オプション"):
                try:
                    b = page.get_by_role("button", name=name)
                    if b.count() > 0 and b.first.is_visible(timeout=800):
                        b.first.click()
                        page.wait_for_timeout(900)
                        opened = True
                        print(f"  「{name}」を開きました")
                        break
                except Exception:
                    continue
            if not opened:
                # aria-label が無いことがあるので、記事ヘッダ付近の最後のボタンも試す
                try:
                    page.locator("button").last.click()
                    page.wait_for_timeout(900)
                except Exception:
                    pass

            for lab in UNPIN_HINT:
                try:
                    if page.get_by_text(lab, exact=False).count() > 0:
                        print(f"✅ すでに固定表示されています（『{lab}』が出ている）。何もしません")
                        return 0
                except Exception:
                    continue

            found = None
            for lab in PIN_LABELS:
                for sel in (f'[role="menuitem"]:has-text("{lab}")', f'button:has-text("{lab}")'):
                    try:
                        loc = page.locator(sel).last
                        if loc.count() > 0 and loc.is_visible(timeout=800):
                            found = (lab, loc)
                            break
                    except Exception:
                        continue
                if found:
                    break
                try:
                    loc = page.get_by_text(lab, exact=False).first
                    if loc.count() > 0 and loc.is_visible(timeout=800):
                        found = (lab, loc)
                        break
                except Exception:
                    continue

            if not found:
                print("✗ 固定表示に当たるものが見つかりません。**何も押していません。**")
                print("\n  画面に見えている項目:")
                seen = []
                for sel in ("button", '[role="menuitem"]', "a"):
                    try:
                        loc = page.locator(sel)
                        for i in range(min(loc.count(), 50)):
                            e = loc.nth(i)
                            if not e.is_visible():
                                continue
                            t = (e.inner_text() or "").strip().replace("\n", " ")[:26]
                            a = (e.get_attribute("aria-label") or "").strip()[:26]
                            lab = t or a
                            if lab and lab not in seen:
                                seen.append(lab)
                    except Exception:
                        continue
                for x in seen[:40]:
                    print(f"    - {x}")
                print("\n  この一覧をそのまま Claude に貼ってください。押し先を特定します。")
                return 2

            print(f"  見つけたもの: 「{found[0]}」")
            if not go:
                print("\nDRY-RUN: 何も変更していません。実行するなら --go を付けてください")
                return 0
            found[1].click()
            page.wait_for_timeout(1500)
            print(f"\n✅ 固定表示にしました: {url}")
            print("   クリエイターページを開いて、いちばん上に出ているか確認してください。")
            return 0
        finally:
            try:
                ctx.close()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
