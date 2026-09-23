#!/usr/bin/env python3
"""set_magazine.py — 公開済み note 記事を、既存のマガジンに追加する。

背景（2026-09-23）:
  マガジンは **note の回遊導線**で、テーマで束ねると1本読んだ人が次を読む。
  owner のアカウントには既に5つある（タグ修復のときに保存した /publish/ のHTMLで確認）:
      高岡の食 / English Articles / 高岡・富山を歩く / 仕事とAI / 北陸の暮らし
  ところが、調べた39本は**どれも5つ全部が「追加」ボタンのまま**＝1つも入っていなかった。
  マガジン編成リスト（CMO/outputs/2026-06-29_note_マガジン編成リスト.md）は6月に作られたが、
  owner が手でクリックする前提だったので実行されていない。

  ※ set_tags.py / set_header_image.py と同じ作り。A1 で code は note を開けない。

使い方（リポジトリのルートから）:
  python3 CDO/outputs/note_publisher/set_magazine.py --probe      # 何も変えず、各記事の所属を見るだけ
  python3 CDO/outputs/note_publisher/set_magazine.py --max 5      # 5本だけ
  python3 CDO/outputs/note_publisher/set_magazine.py              # 全部

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
    sync_playwright = None


def _require_playwright():
    if sync_playwright is None:
        sys.exit("Playwright未インストール。CDO/outputs/note_publisher/setup.sh を先に実行してください。")


SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parents[2]
PROFILE_DIR = Path.home() / ".note_publisher_profile"
TODO = REPO / "ops" / "magazine_todo.tsv"
DBG = REPO / "ops" / "logs" / "_magazine_debug"
PUBLISH_URL = "https://editor.note.com/notes/{nid}/publish/"


def load_todo(only: str = "") -> list[tuple[str, list[str]]]:
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
        nid = parts[0].strip()
        mags = [m.strip() for m in parts[1].split("／") if m.strip()]
        if only and nid != only:
            continue
        rows.append((nid, mags))
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


# マガジン1件 = 名前 + その行のボタン文言（追加 / 追加済み など）。
# ★タグのときの失敗（候補ボタンを入力済みと誤読）を踏まえ、**行ごとに名前とボタンを対にして読む**。
#   名前だけ拾って別の場所のボタンを押す、という取り違えが起きない形にする。
# ★クラス名（sc-d0ee9310-6）は note のビルドごとに変わりうる。**名前で引けなくなったら
#   「追加/追加済み ボタンを持つ行」から逆に辿る**フォールバックを持たせる。
#   タグのときは「# で始まる要素」を広く拾って候補まで数えてしまったので、
#   ここでは**行を特定してから名前とボタンを対にする**という順序を崩さない。
_READ_JS = """() => {
  const pick = (root) => {
    const name = [...root.querySelectorAll('*')]
      .filter(e => e.children.length === 0)
      .map(e => (e.innerText || '').trim())
      .filter(t => t && !['追加', '追加済み', '削除'].includes(t));
    return name.length ? name[0] : '';
  };
  const rows = [];
  const named = document.querySelectorAll('div[class*="sc-d0ee9310-6"]');
  if (named.length) {
    for (const nameEl of named) {
      const name = (nameEl.innerText || '').trim();
      if (!name) continue;
      let row = nameEl;
      for (let i = 0; i < 4 && row.parentElement; i++) row = row.parentElement;
      const btn = row.querySelector('button');
      rows.push({name, label: btn ? (btn.innerText || '').trim() : ''});
    }
    return rows;
  }
  // フォールバック: 「追加」ボタンを起点に、その行の中の名前らしきテキストを拾う
  for (const btn of document.querySelectorAll('button')) {
    const label = (btn.innerText || '').trim();
    if (label !== '追加' && label !== '追加済み') continue;
    let row = btn;
    for (let i = 0; i < 4 && row.parentElement; i++) row = row.parentElement;
    const name = pick(row);
    if (name) rows.push({name, label});
  }
  return rows;
}"""


def read_magazines(page):
    """マガジン欄を開いて、(名前, ボタン文言) の一覧を返す。開けなければ None。"""
    try:
        tab = page.locator("#item-magazine-add").first
        if tab.is_visible(timeout=4000):
            tab.click()
            page.wait_for_timeout(1200)
    except Exception:
        pass
    try:
        rows = page.evaluate(_READ_JS)
    except Exception:
        return None
    return rows if rows else None


def add_to(page, name: str) -> str:
    """名前の行の「追加」を押す。戻り値=ADDED / ALREADY / NOTFOUND / FAIL:理由"""
    try:
        n = page.evaluate("""(want) => {
            for (const nameEl of document.querySelectorAll('div[class*="sc-d0ee9310-6"]')) {
              if ((nameEl.innerText || '').trim() !== want) continue;
              let row = nameEl;
              for (let i = 0; i < 4 && row.parentElement; i++) row = row.parentElement;
              const btn = row.querySelector('button');
              if (!btn) return 'NOBUTTON';
              const label = (btn.innerText || '').trim();
              if (label !== '追加') return 'ALREADY:' + label;
              btn.click();
              return 'CLICKED';
            }
            return 'NOTFOUND';
        }""", name)
    except Exception as e:
        return f"FAIL:{str(e)[:60]}"
    if n == "CLICKED":
        page.wait_for_timeout(900)
        return "ADDED"
    if str(n).startswith("ALREADY"):
        return "ALREADY"
    return "NOTFOUND" if n == "NOTFOUND" else f"FAIL:{n}"


def update_published(page, nid: str) -> str:
    if "/publish" not in page.url:
        try:
            page.goto(PUBLISH_URL.format(nid=nid), wait_until="domcontentloaded", timeout=20000)
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


def dump_ui(page, nid: str, tag: str = ""):
    try:
        DBG.mkdir(parents=True, exist_ok=True)
        sfx = f"_{tag}" if tag else ""
        (DBG / f"publish_{nid}{sfx}.html").write_text(page.content(), encoding="utf-8")
        page.screenshot(path=str(DBG / f"shot_{nid}{sfx}.png"), full_page=False)
        print(f"   --- 証拠を保存: {DBG} ---")
    except Exception as e:
        print(f"   （証拠の保存に失敗: {e}）")


def main():
    ap = argparse.ArgumentParser(description="公開済み note 記事をマガジンに追加する")
    ap.add_argument("--probe", action="store_true", help="変更せず、所属だけ見る（まずこれ）")
    ap.add_argument("--only", default="", help="note_id を1つだけ処理")
    ap.add_argument("--max", type=int, default=0, help="この本数で止める（0=全部）")
    ap.add_argument("--headless", action="store_true", help="画面を出さずに実行")
    args = ap.parse_args()

    todo = load_todo(args.only)
    if args.max > 0:
        todo = todo[: args.max]
    if not todo:
        print("対象がありません（全部 DONE か、リストが空）")
        return
    print(f"対象 {len(todo)} 本{'（--probe：何も変更しません）' if args.probe else ''}")

    _require_playwright()
    results = []
    with sync_playwright() as p:
        ctx = launch(p, args.headless)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        for nid, mags in todo:
            print(f"\n=== {nid} … 入れたいマガジン: {' / '.join(mags)}")
            try:
                page.goto(PUBLISH_URL.format(nid=nid), wait_until="domcontentloaded", timeout=25000)
                page.wait_for_timeout(2500)
            except Exception as e:
                print(f"   ✗ 開けない: {str(e)[:80]}")
                results.append((nid, "OPEN_FAIL"))
                continue

            rows = read_magazines(page)
            if rows is None:
                print("   ⚠️ マガジン欄を読めなかった（判定不能）→ 証拠を残して次へ")
                dump_ui(page, nid, "unreadable")
                results.append((nid, "READ_FAIL"))
                continue
            print("   いまの状態: " + " / ".join(f"{r['name']}={r['label'] or '?'}" for r in rows))
            if args.probe:
                results.append((nid, "PROBED:" + ",".join(
                    f"{r['name']}={r['label']}" for r in rows if r['label'] != '追加')  or "PROBED:どこにも入っていない"))
                continue

            got = []
            for m in mags:
                st = add_to(page, m)
                print(f"   {m}: {st}")
                got.append(st)
            if all(s in ("ALREADY",) for s in got):
                print("   → すでに全部入っている。更新しない")
                mark_done(nid)
                results.append((nid, "SKIP_ALREADY"))
                continue
            if not any(s == "ADDED" for s in got):
                print("   ✗ 1つも追加できなかった → 証拠を残す")
                dump_ui(page, nid, "fail")
                results.append((nid, "ADD_FAIL"))
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
    if any(s in ("ADD_FAIL", "OPEN_FAIL", "READ_FAIL") for _, s in results):
        print(f"失敗分の証拠: {DBG}  ← このフォルダごと commit すれば code が直せます")


if __name__ == "__main__":
    main()
