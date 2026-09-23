#!/usr/bin/env python3
"""set_tags.py — 公開済み note 記事に、後からハッシュタグを付ける。

背景（2026-09-23）:
  公開済み196本のうち **39本がタグ0個** で出ていた（2026-08-25〜09-18）。
  publish_to_note.py は記事に `## ハッシュタグ` ブロックが無ければ黙って0個で公開する仕様で、
  その時期の記事にブロックが無かった。note ではタグがタグページ・おすすめ経由の
  主要な発見経路なので、**タグ0個は露出が構造的に落ちる**。
  見出し画像と同じく、**公開後でも後から付けられる**（/publish/ 画面にタグ欄がある）。

  ※ set_header_image.py と同じ作り。A1 で code は note を開けないので、owner の Mac で動かす。

使い方（リポジトリのルートから）:
  python3 CDO/outputs/note_publisher/set_tags.py --probe        # 変更せず、今のタグと画面を見るだけ
  python3 CDO/outputs/note_publisher/set_tags.py                # 実際に付けて更新する
  python3 CDO/outputs/note_publisher/set_tags.py --only nXXXX   # 1本だけ試す
  python3 CDO/outputs/note_publisher/set_tags.py --max 5        # 5本で止める

前提: publish_to_note.py --login 済み（~/.note_publisher_profile）。
"""
from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

# ★2026-09-23: import の時点で落とすと `--help` すら出ず、code 側では中身の確認もできない
#   （publish_to_note.py で同じことをやって直したばかり）。**使う直前に確かめる**。
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
TODO = REPO / "ops" / "tag_backfill_todo.tsv"
DBG = REPO / "ops" / "logs" / "_tag_debug"
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
        tags = [t.lstrip("#") for t in parts[1].split() if t.strip()]
        if only and nid != only:
            continue
        rows.append((nid, tags))
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


def read_current_tags(page) -> list[str]:
    """画面にいま入っているタグを読む。**入っているものは二度打ちしない**ため。"""
    try:
        return page.eval_on_selector_all(
            "*",
            """els => {
                 const out = new Set();
                 for (const e of els) {
                   const t = (e.innerText || '').trim();
                   // 「#」で始まり、短く、子要素を持たない要素＝タグチップとみなす
                   if (t.startsWith('#') && t.length <= 30 && e.children.length === 0) out.add(t.slice(1));
                 }
                 return [...out];
               }""") or []
    except Exception:
        return []


def dump_ui(page, nid: str, tag: str = ""):
    """うまくいかなかったときの証拠。set_header_image.py と同じ作法で残す。"""
    try:
        DBG.mkdir(parents=True, exist_ok=True)
        sfx = f"_{tag}" if tag else ""
        (DBG / f"publish_{nid}{sfx}.html").write_text(page.content(), encoding="utf-8")
        page.screenshot(path=str(DBG / f"shot_{nid}{sfx}.png"), full_page=False)
        print(f"   --- 証拠を保存: {DBG} ---")
    except Exception as e:
        print(f"   （証拠の保存に失敗: {e}）")


def type_tags(page, tags: list[str]) -> tuple[int, str]:
    """タグ欄へ入力する。戻り値=(入れた数, 失敗理由)。"""
    try:
        box = page.locator(
            'input[placeholder*="ハッシュタグ"], input[placeholder*="タグ"], '
            'textarea[placeholder*="ハッシュタグ"]'
        ).first
        box.wait_for(state="visible", timeout=8000)
    except Exception as e:
        return 0, f"タグ欄が見つからない: {str(e)[:70]}"
    have = {t.casefold() for t in read_current_tags(page)}
    added = 0
    for t in tags:
        if t.casefold() in have:
            continue
        if added >= 10:            # note の上限にぶつけない
            break
        try:
            box.click()
            page.keyboard.type(t)
            page.keyboard.press("Enter")
            page.wait_for_timeout(250)
            added += 1
        except Exception as e:
            return added, f"{t} の入力で失敗: {str(e)[:60]}"
    return added, ""


def update_published(page, nid: str) -> str:
    """公開設定画面で更新を確定する。すでに /publish/ にいる前提。"""
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


def main():
    ap = argparse.ArgumentParser(description="公開済み note 記事にハッシュタグを後から付ける")
    ap.add_argument("--probe", action="store_true", help="変更せず、今のタグと画面を見るだけ（まずこれ）")
    ap.add_argument("--only", default="", help="note_id を1つだけ処理")
    ap.add_argument("--max", type=int, default=0, help="この本数で止める（0=全部）")
    ap.add_argument("--no-update", action="store_true", help="タグを入れるだけで更新ボタンは押さない")
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
        for nid, tags in todo:
            print(f"\n=== {nid} … 付けたいタグ {len(tags)}個: {' '.join('#'+t for t in tags)}")
            try:
                page.goto(PUBLISH_URL.format(nid=nid), wait_until="domcontentloaded", timeout=25000)
                page.wait_for_timeout(2500)
            except Exception as e:
                print(f"   ✗ 開けない: {str(e)[:80]}")
                results.append((nid, "OPEN_FAIL"))
                continue

            cur = read_current_tags(page)
            print(f"   いま入っているタグ: {len(cur)}個 {cur[:8]}")
            if args.probe:
                dump_ui(page, nid, "probe")
                results.append((nid, f"PROBED:{len(cur)}tags"))
                continue
            if len(cur) >= 5:
                # 既に十分付いている＝この記事はもう対象外。触って壊さない。
                print("   → すでに5個以上あるので触らない")
                mark_done(nid)
                results.append((nid, f"SKIP_HAS_TAGS:{len(cur)}"))
                continue

            added, err = type_tags(page, tags)
            if err:
                print(f"   ✗ {err}")
                dump_ui(page, nid, "fail")
                results.append((nid, "TYPE_FAIL"))
                continue
            print(f"   ✅ {added}個を入力")
            if args.no_update:
                results.append((nid, f"SET_ONLY:{added}"))
                if sys.stdin.isatty():
                    input("   画面を確認して、よければ手で更新してください。Enterで次へ ...")
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
    if any(s in ("TYPE_FAIL", "OPEN_FAIL") for _, s in results):
        print(f"失敗分の証拠: {DBG}  ← このフォルダごと commit すれば code が直せます")


if __name__ == "__main__":
    main()
