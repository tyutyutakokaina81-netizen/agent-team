#!/usr/bin/env python3
"""公開済み note 記事から、**指定の文字列を含む段落だけ**を消す（owner の Mac で実行）。

なぜ要るのか（2026-11-14・cowork 2026-11-14_001 の依頼）:
  墓参り(nf2aad02f3b00) の本文に **却下した画像のクレジット行**が残っていて、読者に見えている。
  消したいのは**その1行だけ**なのに、`update_article.py` は**本文を全文差し替える**作りなので使えない。
  実測（cowork の --probe）: **ライブ 2706字 / md 2345字**。
  ライブにしかないもの＝**本文中の写真1枚**と**フォロー導線＋あわせて読む3本**。
  全文差し替えをすると**それが消える**。cowork は正しく止まった。

  ★`update_article.py` にモードを足すのではなく**別ファイルにした**。
    あちらは「全文を置き換える」道具で、こちらは「1段落だけ消す」道具。
    混ぜると、**消すだけのつもりで全文差し替えが走る**事故の余地ができる。

安全のために決めてあること:
  - **既定は読むだけ**。実際に消すのは `--go` を付けたときだけ。
  - 一致した段落が **ちょうど1つでないときは何もしない**（0個でも2個以上でも中断）。
    どれを消すか機械が選べない状態で消すのは、消しすぎと同じ。
  - 消す前に**ライブ本文をファイルに保存する**（`_before_update/<nid>.drop.txt`）。
  - ★**消したあと、保存する前に確かめる**:
      ① 指定の文字列が本文から消えたか
      ② **減った字数が、消したかった段落の長さとほぼ同じか**（＝他が巻き添えになっていないか）
      ③ 本文の冒頭と末尾が元のままか
    ひとつでも外れたら **保存せずに終わる**（保存しなければライブは元のまま）。
  - 下書きへ戻した記事（DO_NOT_TOUCH）は開く前に弾く。押すのは「更新する」だけ。

⚠️ **このスクリプトは実機未検証**（code は note に繋げない＝A1）。
   **必ず最初に --go 無しで走らせ、出てくる段落が消したいものか目で見てから** --go を付けること。

使い方:
  python3 drop_paragraph.py <NID> --contains "<段落に含まれる文字列>" [--go]
    例) python3 drop_paragraph.py nf2aad02f3b00 --contains "見出し画像：" 
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

# 消した字数が、狙った段落の長さとどれだけずれてよいか。
# 改行やゼロ幅文字の数え方が環境で1〜2字ぶれるので、少しだけ許す。
LEN_TOLERANCE = 4


def _arg(name: str, default=None):
    a = sys.argv
    if name in a:
        i = a.index(name)
        if i + 1 < len(a):
            return a[i + 1]
    return default


def _norm(s: str) -> str:
    """空白・改行の違いを無視して比べるための形にする。

    エディタは空段落を畳んだり改行の数を変えたりするので、そこで差が出ると
    **中身が同じなのに「壊れた」と言ってしまう**。見たいのは文字の中身だけ。
    """
    return re.sub(r"\s+", "", s or "")


def verify(before: str, after: str, target: str, needle: str) -> list:
    """消したあとの本文が正しいかを確かめる。**保存する前に**呼ぶ。

    やり方＝**本文まるごとを突き合わせる**。
      「元の本文から、狙った段落を取り除いた文字列」と「いま画面にある本文」が、
      空白を無視して**一致するか**を見る。一致すれば、狙った段落だけが消えて
      **ほかはどこも変わっていない**と言える。

    ★2026-11-14: 最初は「冒頭40字」「末尾40字」が変わっていないかで見ていたが、
      `test_drop_paragraph.py` が**この道具がまさに使われる場面で誤判定する**ことを捕まえた＝
      **消す段落が本文の最後にあると、末尾40字がその段落自身**なので、
      正しく消せているのに「末尾が変わった」と鳴る（墓参りのクレジット行がこれ）。
      端だけ見る判定は、端を消すときに効かない。だから全体で突き合わせる形に変えた。

    戻り値が空リストなら OK。中身があれば、それが保存しない理由。
    """
    problems = []
    if needle in after:
        problems.append("指定の文字列がまだ本文に残っている")
    if target and target not in before:
        problems.append("狙った段落が、元の本文の中に見つからない（段落の取り方が合っていない）")
        return problems
    expected = before.replace(target, "", 1)
    if _norm(after) != _norm(expected):
        dropped = len(before) - len(after)
        want = len(target)
        problems.append(
            f"狙った段落以外も変わっている（{dropped}字 減ったが、狙った段落は {want}字）"
            "＝ほかの段落を巻き添えにした可能性がある")
    return problems


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    go = "--go" in sys.argv
    needle = _arg("--contains")
    if not args or not needle:
        print(__doc__)
        return 1
    nid = args[0]

    why = _safety.blocked_reason(nid)
    if why:
        print(f"✗ {nid} は触らない記事です: {why}")
        return 1

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
            before = editor.inner_text() or ""
            if not before.strip():
                print("✗ 本文を読めませんでした。画面が変わった可能性があるので何もしません")
                return 2

            # 段落＝エディタ直下の子要素。note は段落ごとに別ブロックになる。
            blocks = editor.locator("xpath=./*")
            n = blocks.count()
            hits = []
            for i in range(n):
                b = blocks.nth(i)
                try:
                    txt = b.inner_text() or ""
                except Exception:
                    continue
                if needle in txt:
                    hits.append((i, txt))

            print(f"■ いまの本文: {len(before)}字 / 段落 {n}個")
            print(f"■ 「{needle}」を含む段落: {len(hits)}個")
            for i, txt in hits:
                print(f"   [{i}] {txt.strip()[:120]}")

            if len(hits) != 1:
                print("✗ ちょうど1個でないので何もしません"
                      "（0個＝見つからない／2個以上＝どれを消すか機械には選べない）。"
                      "--contains をもっと長い文字列にしてください")
                return 2

            idx, target = hits[0]
            BACKUP_DIR.mkdir(exist_ok=True)
            bk = BACKUP_DIR / f"{nid}.drop.txt"
            bk.write_text(before + "\n", encoding="utf-8")
            print(f"  いまの本文を保存しました: {bk}")

            if not go:
                print("\nDRY-RUN: 何も変更していません。"
                      "上の段落が消したいものなら、同じコマンドに --go を付けてください")
                return 0

            # 段落をまるごと選んで消す。三連クリックでその段落だけが選ばれる。
            blk = blocks.nth(idx)
            blk.click(click_count=3, timeout=10000)
            page.wait_for_timeout(300)
            page.keyboard.press("Delete")
            page.wait_for_timeout(300)
            # 空になったブロックを畳む（前の行の末尾へ繋ぐ）
            page.keyboard.press("Backspace")
            page.wait_for_timeout(600)

            after = editor.inner_text() or ""
            dropped = len(before) - len(after)
            want = len(target)
            print(f"\n■ 消したあと: {len(after)}字（{dropped}字 減／狙いは {want}字 前後）")

            problems = verify(before, after, target, needle)

            if problems:
                print("\n✗ 保存しません。確認に引っかかりました:")
                for p in problems:
                    print(f"   - {p}")
                print(f"   元の本文は {bk} にあります。"
                      "ブラウザは保存せずに閉じるので、ライブの記事は元のままです")
                return 2

            print("✅ 確認OK（狙った段落だけが消えている）")

            try:
                page.locator('button:has-text("公開に進む")').last.click(timeout=10000)
                page.wait_for_url("**/publish/**", timeout=20000)
                page.wait_for_timeout(2500)
            except Exception as e:
                print(f"✗ 「公開に進む」で遷移できませんでした（{str(e)[:80]}）。保存せず終わります")
                return 2

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
