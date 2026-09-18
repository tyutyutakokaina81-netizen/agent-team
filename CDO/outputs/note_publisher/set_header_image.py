#!/usr/bin/env python3
"""set_header_image.py — 公開済み note 記事に見出し画像を後から付ける／今のUIを実測する。

背景（2026-09-18）:
  publish_to_note.py のサムネ用セレクタ候補7つが**全部 Timeout** し、5本が見出し画像なしで公開された。
  原因は note 側のエディタUI変更。code は A1 で note を開けないので、**owner の Mac で実測する**しかない。

このツールがやること:
  --probe  … 何も変更せず、編集画面に実在するボタン/aria-label/input[type=file] を全部出して HTML を保存する
             （＝セレクタを直すための証拠集め。まずこれを回す）
  （既定） … 見出し画像を実際に設定して更新する。ボタン名に頼らない方法から順に試す:
             ①DOM にある input[type=file] へ直接 set_files（ボタン名が変わっても効く）
             ②「画像」「追加」等を含むボタンを片っ端から押してから ①を再試行
             ③expect_file_chooser（旧来の方法）
             どれも駄目なら証拠を保存して次の記事へ（黙って失敗しない）。

使い方（リポジトリのルートから）:
  python3 CDO/outputs/note_publisher/set_header_image.py --probe
  python3 CDO/outputs/note_publisher/set_header_image.py
  python3 CDO/outputs/note_publisher/set_header_image.py --only n242960f609cf
  python3 CDO/outputs/note_publisher/set_header_image.py --no-update   # 画像だけ入れて更新は手でやる

前提: publish_to_note.py --login 済み（~/.note_publisher_profile）。
"""
from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("Playwright未インストール。CDO/outputs/note_publisher/setup.sh を先に実行してください。")

SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parents[2]
PROFILE_DIR = Path.home() / ".note_publisher_profile"
TODO = REPO / "ops" / "header_image_todo.tsv"
DBG = REPO / "ops" / "logs" / "_thumb_debug"
EDIT_URL = "https://editor.note.com/notes/{nid}/edit/"

# 見出し画像が入ったかの判定（上部にある大きめの画像）。ボタン名に依存しない。
_HAS_IMAGE_JS = """() => {
  const imgs = [...document.querySelectorAll('img')];
  return imgs.some(im => {
    const r = im.getBoundingClientRect();
    const src = im.currentSrc || im.src || '';
    return r.width >= 280 && r.height >= 90 && r.top < 800 &&
           /st-note|note\\.com|blob:|data:image/.test(src);
  });
}"""


def load_todo(only: str = "") -> list[tuple[str, Path]]:
    if not TODO.exists():
        sys.exit(f"対象リストが無い: {TODO}")
    rows = []
    for line in TODO.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("DONE"):
            continue
        parts = s.split("\t")
        if len(parts) < 2:
            continue
        nid, rel = parts[0].strip(), parts[1].strip()
        if only and nid != only:
            continue
        rows.append((nid, REPO / rel))
    return rows


def mark_done(nid: str):
    if not TODO.exists():
        return
    txt = TODO.read_text(encoding="utf-8")
    TODO.write_text(txt.replace(f"\n{nid}\t", f"\nDONE\t{nid}\t"), encoding="utf-8")


def launch(p, headless: bool):
    if not PROFILE_DIR.exists() or not any(PROFILE_DIR.iterdir()):
        sys.exit("初回ログインがまだ。`python3 CDO/outputs/note_publisher/publish_to_note.py --login` を先に。")
    for kw in ({"channel": "chrome"}, {}):
        try:
            return p.chromium.launch_persistent_context(
                str(PROFILE_DIR), headless=headless,
                viewport={"width": 1280, "height": 900},
                args=["--disable-blink-features=AutomationControlled"], **kw)
        except Exception:
            continue
    raise RuntimeError("ブラウザ起動失敗")


def dump_ui(page, nid: str):
    """今のUIに実在する要素を全部出して保存する。これがセレクタ修理の材料になる。"""
    print("   --- 画面上のボタン/ラベル（aria-label と文言） ---")
    try:
        els = page.eval_on_selector_all(
            "button, [role='button'], label, a[role='button']",
            """els => els.slice(0, 80).map(e => ({
                 tag: e.tagName.toLowerCase(),
                 aria: e.getAttribute('aria-label') || '',
                 cls: (e.getAttribute('class') || '').slice(0, 70),
                 txt: (e.innerText || '').trim().slice(0, 30)
               }))""")
        for e in els:
            if e["aria"] or e["txt"]:
                print(f"   [{e['tag']}] aria={e['aria']!r} txt={e['txt']!r} cls={e['cls']!r}")
    except Exception as e:
        print(f"   （ボタン一覧の取得に失敗: {e}）")
    try:
        fi = page.eval_on_selector_all(
            "input[type=file]",
            """els => els.map(e => ({accept: e.getAttribute('accept')||'',
                                     cls: (e.getAttribute('class')||'').slice(0,60),
                                     hidden: e.offsetParent === null}))""")
        print(f"   --- input[type=file] の数: {len(fi)} {fi} ---")
    except Exception as e:
        print(f"   （file input の取得に失敗: {e}）")
    try:
        DBG.mkdir(parents=True, exist_ok=True)
        out = DBG / f"edit_{nid}.html"
        out.write_text(page.content(), encoding="utf-8")
        print(f"   --- HTMLを保存: {out} ---")
    except Exception as e:
        print(f"   （HTML保存に失敗: {e}）")


def set_files_on_any_input(page, img: Path) -> str:
    """DOM にある input[type=file] へ直接投入する。**hidden でも Playwright は受け付ける**ので
    ボタンの aria-label が変わっても効く。成功したら方法名、駄目なら空文字。"""
    inputs = page.locator('input[type="file"]')
    n = inputs.count()
    for i in range(n):
        try:
            inputs.nth(i).set_input_files(str(img), timeout=5000)
            page.wait_for_timeout(3500)
            if page.evaluate(_HAS_IMAGE_JS):
                return f"input[type=file] #{i} へ直接投入"
        except Exception as e:
            print(f"      ・file input #{i} 不可: {type(e).__name__}: {str(e)[:90]}")
    return ""


def click_image_buttons(page) -> int:
    """「画像」「追加」等を含むボタンを押して、遅延生成される file input を出させる。"""
    pressed = 0
    try:
        cands = page.eval_on_selector_all(
            "button, [role='button'], label",
            """els => els.map((e, i) => ({i,
                 s: ((e.getAttribute('aria-label')||'') + ' ' + (e.innerText||'')).trim()}))
               .filter(o => /画像|追加|アップロード|eyecatch|イメージ/i.test(o.s))""")
    except Exception:
        cands = []
    all_btns = page.locator("button, [role='button'], label")
    for c in cands[:8]:
        try:
            all_btns.nth(c["i"]).click(timeout=2500)
            pressed += 1
            page.wait_for_timeout(900)
        except Exception:
            continue
    return pressed


def confirm_crop(page):
    """トリミング/位置調整ダイアログの確定。ダイアログ内に限定して『下書き保存』の誤爆を防ぐ。"""
    dlg = '[role="dialog"], [aria-modal="true"], .ReactModal__Content'
    for label in ("保存", "適用", "決定", "完了", "この画像を挿入"):
        try:
            btn = page.locator(f'{dlg} >> button:has-text("{label}")').last
            if btn.is_visible(timeout=600):
                btn.click()
                page.wait_for_timeout(1200)
                return label
        except Exception:
            continue
    return ""


def update_published(page, nid: str) -> str:
    """公開済み記事の更新。publish_to_note.py と同じ経路（下書き保存→公開に進む→最終ボタン）。"""
    try:
        ds = page.locator('button:has-text("下書き保存")').first
        if ds.is_visible(timeout=1500):
            ds.click()
            page.wait_for_timeout(2500)
    except Exception:
        pass
    try:
        page.locator('button:has-text("公開に進む"), button:has-text("更新する")').first.click(timeout=6000)
        page.wait_for_timeout(2500)
    except Exception as e:
        return f"UPDATE_FAIL:公開に進む/更新するが押せない {str(e)[:80]}"
    if "/publish" not in page.url:
        try:
            page.goto(f"https://editor.note.com/notes/{nid}/publish/",
                      wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(2500)
        except Exception as e:
            return f"UPDATE_FAIL:/publish/へ行けない {str(e)[:80]}"
    for label in ("更新する", "投稿する", "公開する"):
        try:
            btn = page.locator(f'button:has-text("{label}")').last
            if btn.is_visible(timeout=1500):
                btn.click()
                page.wait_for_timeout(4000)
                return f"UPDATED:{label}"
        except Exception:
            continue
    return "UPDATE_FAIL:最終ボタン(更新する/投稿する)が見つからない"


def main():
    ap = argparse.ArgumentParser(description="公開済み note 記事に見出し画像を付ける／UIを実測する")
    ap.add_argument("--probe", action="store_true", help="変更せずUIの実測だけ（まずこれ）")
    ap.add_argument("--only", default="", help="note_id を1つだけ処理")
    ap.add_argument("--no-update", action="store_true", help="画像を入れるだけで更新ボタンは押さない")
    ap.add_argument("--headless", action="store_true", help="画面を出さずに実行")
    args = ap.parse_args()

    targets = load_todo(args.only)
    if not targets:
        print("対象なし（ops/header_image_todo.tsv が空か、全部 DONE）。")
        return
    print(f"対象 {len(targets)} 件 / モード={'PROBE(変更しない)' if args.probe else '設定して更新'}")

    results = []
    with sync_playwright() as p:
        ctx = launch(p, args.headless)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        for nid, img in targets:
            print(f"\n=== {nid} ===")
            if not img.exists():
                print(f"   ✗ 画像が無い: {img}")
                results.append((nid, "NO_IMAGE"))
                continue
            try:
                page.goto(EDIT_URL.format(nid=nid), wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(4000)
            except Exception as e:
                print(f"   ✗ 編集画面を開けない: {e}")
                results.append((nid, "OPEN_FAIL"))
                continue
            if "login" in page.url:
                print("   ✗ ログイン切れ。publish_to_note.py --login をやり直してください。")
                results.append((nid, "NEEDS_LOGIN"))
                break

            had = page.evaluate(_HAS_IMAGE_JS)
            print(f"   見出し画像の有無（実行前）: {'あり' if had else 'なし'}")

            if args.probe:
                dump_ui(page, nid)
                results.append((nid, "PROBED_HAS_IMAGE" if had else "PROBED_NO_IMAGE"))
                continue

            if had:
                print("   → 既に画像があるので触らない（上書き事故を避ける）")
                results.append((nid, "SKIP_HAS_IMAGE"))
                continue

            how = set_files_on_any_input(page, img)
            if not how:
                n = click_image_buttons(page)
                print(f"   方法②: 画像系ボタンを {n} 個押して file input を出させた")
                how = set_files_on_any_input(page, img)
            if not how:
                try:
                    with page.expect_file_chooser(timeout=6000) as fc:
                        page.locator('button:has-text("画像をアップロード"), button:has-text("アップロード"), '
                                     'button[aria-label*="画像"]').first.click(timeout=5000)
                    fc.value.set_files(str(img))
                    page.wait_for_timeout(3500)
                    if page.evaluate(_HAS_IMAGE_JS):
                        how = "file_chooser 経由"
                except Exception as e:
                    print(f"   方法③: file_chooser も不可: {type(e).__name__}: {str(e)[:90]}")

            if not how:
                print("   ✗ 見出し画像を設定できなかった → 証拠を保存する")
                dump_ui(page, nid)
                results.append((nid, "SET_FAIL"))
                continue

            crop = confirm_crop(page)
            print(f"   ✅ 画像を設定（{how}）{'／トリミング確定=' + crop if crop else ''}")
            if args.no_update:
                results.append((nid, f"SET_ONLY:{how}"))
                print("   （--no-update のため更新ボタンは押していない。画面で確認して手で更新してください）")
                if sys.stdin.isatty():
                    input("   Enterで次へ ...")
                continue
            st = update_published(page, nid)
            print(f"   {st}")
            if st.startswith("UPDATED"):
                mark_done(nid)
            results.append((nid, st))
        ctx.close()

    print("\n================ 結果 ================")
    for nid, st in results:
        print(f"  {nid}\t{st}")
    ok = sum(1 for _, s in results if s.startswith("UPDATED"))
    print(f"更新できた: {ok} / {len(results)}  （{datetime.datetime.now():%Y-%m-%d %H:%M}）")
    if any(s in ("SET_FAIL", "OPEN_FAIL") for _, s in results):
        print(f"失敗分の証拠HTML: {DBG}  ← このフォルダごと commit すれば code が直せます")


if __name__ == "__main__":
    main()
