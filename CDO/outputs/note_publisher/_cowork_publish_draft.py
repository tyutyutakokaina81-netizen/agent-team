#!/usr/bin/env python3
"""cowork: 「公開したはずなのに note 上では下書きのまま」の記事を、**既にある下書きのまま**公開する。
使い方: python3 _cowork_publish_draft.py <NID> [--go]
  --go なし=DRY（開いて照合するだけ） / --go で「投稿する」を押す。

2026-10-24 inbox 2026-10-24_005（code 指示）用。update_article.py は下書きの「投稿する」を
押さない安全ガードを持つ（09-24 の重複再公開事故）。その穴を広げないため、ここは別の口にして
次の条件をすべて満たすときだけ押す:
  - NID が ops/public_fix_todo.tsv（code が「公開漏れ」と確定した一覧）に載っている
  - _note_safety.DO_NOT_TOUCH に載っていない（台帳の unpublished 印は、この一覧の記事では
    「下書きのままと判明」の意味なので見ない）
  - ログアウト状態で 404（＝まだ公開されていない）
  - 編集画面のタイトルが一覧のタイトルと一致する
  - /publish/ 画面に「更新する」が無く「投稿する」がある（＝下書き）
"""
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import publish_to_note as P  # noqa: E402
import _note_safety as S  # noqa: E402

EDIT_URL = "https://editor.note.com/notes/{nid}/edit/"
TODO = ROOT / "ops" / "public_fix_todo.tsv"
MAG_TODO = ROOT / "ops" / "magazine_todo.tsv"


def _norm(s: str) -> str:
    return re.sub(r"[\s　。、—\-「」]", "", s or "")


def allowed() -> dict:
    out = {}
    for ln in TODO.read_text(encoding="utf-8").splitlines():
        if not ln.strip() or ln.startswith("#") or ln.startswith("note_id"):
            continue
        c = ln.split("\t")
        if len(c) >= 3 and re.fullmatch(r"n[0-9a-f]{12,13}", c[0]):
            out[c[0]] = c[2]
    return out


def public_status(nid: str) -> int:
    req = urllib.request.Request(f"https://note.com/{P.AUTHOR_ID}/n/{nid}",
                                 headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def find_md(title: str):
    for md in sorted((ROOT / "CMO" / "outputs").glob("*_note記事_*.md")):
        try:
            t, *_ = P.parse_article(md)
        except (Exception, SystemExit):
            continue
        if _norm(t) == _norm(title) or (len(_norm(title)) >= 12 and _norm(t).startswith(_norm(title))):
            return md
    return None


def mags_for(nid: str) -> list:
    out = []
    for ln in MAG_TODO.read_text(encoding="utf-8").splitlines():
        c = ln.split("\t")
        if len(c) >= 2 and c[0] == nid:
            out += [m.strip() for m in re.split(r"[／/]", c[1]) if m.strip()]
    return out


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    go = "--go" in sys.argv
    if not args:
        print(__doc__)
        return 1
    nid = args[0]
    allow = allowed()
    if nid not in allow:
        print(f"✗ {nid} は public_fix_todo.tsv に無い。押さない")
        return 1
    if nid in S.DO_NOT_TOUCH:
        print(f"✗ {nid} は DO_NOT_TOUCH: {S.DO_NOT_TOUCH[nid]}")
        return 1
    want = allow[nid]
    st = public_status(nid)
    print(f"■ {nid} 「{want}」 ログアウトで {st}")
    if st == 200:
        print("  既に読者に見えている。何もしない")
        return 0
    md = find_md(want)
    tags, mags = [], mags_for(nid)
    if md:
        _t, _b, _ph, tags, m2 = P.parse_article(md)
        mags = mags or m2
    print(f"  md: {md.name if md else '（見つからず・タグは入れない）'} / タグ {tags} / マガジン {mags}")

    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        ctx = P.load_context(pw)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto(EDIT_URL.format(nid=nid), wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(9000)   # 2026-10-24 実測: 3秒ではタイトル/本文が空で読める
            for _ in range(3):
                page.keyboard.press("Escape")
                page.wait_for_timeout(250)
            ti = page.locator(P.TITLE_SELECTOR).first
            ti.wait_for(state="visible", timeout=20000)
            from update_article import _read_title
            cur = _read_title(ti)
            body = page.locator('div[contenteditable="true"]').last.inner_text() or ""
            print(f"  編集画面: 「{cur[:50]}」 本文 {len(body)}字")
            if _norm(cur)[:12] != _norm(want)[:12]:
                print("✗ タイトルが一覧と一致しない。押さない")
                return 2
            if len(body.strip()) < 500:
                print("✗ 本文が短すぎる（空の下書きの可能性）。押さない")
                return 2

            page.locator('button:has-text("公開に進む")').last.click(timeout=10000)
            page.wait_for_url("**/publish/**", timeout=20000)
            page.wait_for_timeout(3000)
            if page.locator(f'button:has-text("{S.SAVE_LABEL}")').count() and \
                    page.locator(f'button:has-text("{S.SAVE_LABEL}")').last.is_visible():
                print("✗ 「更新する」がある＝公開済みの記事。押さない")
                return 2
            pub = page.locator('button:has-text("投稿する")').first
            pub.wait_for(state="visible", timeout=10000)
            print("  /publish/: 「投稿する」あり・「更新する」なし＝下書きで確定")
            if not go:
                print("DRY-RUN: 押していない。--go で公開する")
                return 0

            if tags:
                try:
                    tin = page.locator('input[placeholder*="ハッシュタグ"], input[placeholder*="タグ"]').first
                    tin.wait_for(state="visible", timeout=8000)
                    have = page.inner_text("body")
                    n = 0
                    for t in tags[:10]:
                        if f"#{t}" in have:
                            continue
                        tin.click()
                        page.keyboard.type(t)
                        page.keyboard.press("Enter")
                        page.wait_for_timeout(200)
                        n += 1
                    print(f"  ✅ タグ {n} 個を追加（既にあったものは飛ばした）")
                except Exception as e:
                    print(f"  ⚠ タグ入力に失敗: {str(e)[:80]}")
            if mags:
                try:
                    tab = page.locator("#item-magazine-add").first
                    if tab.is_visible(timeout=4000):
                        tab.click()
                        page.wait_for_timeout(1200)
                except Exception:
                    pass
                for m in mags:
                    r = page.evaluate("""(want) => {
                      const all = [...document.querySelectorAll('div[class*="sc-d0ee9310-6"], button')];
                      for (let i = 0; i < all.length; i++) {
                        if (all[i].tagName === 'BUTTON') continue;
                        if ((all[i].innerText || '').trim() !== want) continue;
                        for (let j = i + 1; j < all.length; j++) {
                          if (all[j].tagName !== 'BUTTON') break;
                          const t = (all[j].innerText || '').trim();
                          if (t === '追加') { all[j].click(); return 'CLICKED'; }
                          if (t === '追加済み' || t === '追加済' || t === '削除') return 'ALREADY';
                        }
                        return 'NOBUTTON';
                      }
                      return 'NOTFOUND';
                    }""", m)
                    print(f"  マガジン『{m}』: {r}")
                    page.wait_for_timeout(800)

            page.wait_for_timeout(1000)
            pub = page.locator('button:has-text("投稿する")').first
            pub.click()
            page.wait_for_timeout(2500)
            for lbl in ("投稿する", "公開する", "OK"):
                try:
                    c = page.locator(f'[role="dialog"] >> button:has-text("{lbl}")').last
                    if c.is_visible(timeout=800):
                        c.click()
                        page.wait_for_timeout(1500)
                        break
                except Exception:
                    continue
            page.wait_for_timeout(4000)
            print(f"  投稿するを押した。最終URL: {page.url}")
        finally:
            try:
                ctx.close()
            except Exception:
                pass

    import time
    for _ in range(6):
        st = public_status(nid)
        if st == 200:
            break
        time.sleep(5)
    print(f"結果: ログアウトで {st} → {'PUBLISHED' if st == 200 else 'NOT_VISIBLE'}")
    print(f"  https://note.com/{P.AUTHOR_ID}/n/{nid}")
    return 0 if st == 200 else 2


if __name__ == "__main__":
    sys.exit(main())
