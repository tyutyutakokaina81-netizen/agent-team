#!/usr/bin/env python3
"""
重複noteを「下書きに戻す／公開停止」する（v2・自己診断つき）。

v1 は note のUIでボタンを見つけられず 74/74 manual だった。v2 は
1) より広いセレクタでメニュー/ボタンを探して **実際にクリック** し、
2) 見つからなければ **その記事のボタン一覧テキストとスクショを保存** する。
→ 1回 --execute --limit 1 を回せば、「成功」か「実DOM情報（code が直せる材料）」が必ず得られる。

⚠️ 公開状態を変える操作。既定 dry-run。実行は --execute。まず --execute --limit 1 で1本。
　削除（取り消し不可）は自動では押さない。下書き化/公開停止のみ自動。削除しか無い場合は manual 報告。

前提: publish_to_note.py --login 済み。
使い方:
  python3 unpublish_notes.py                      # dry-run（対象表示）
  python3 unpublish_notes.py --execute --limit 1  # 1本だけ実行（まずこれ）
  python3 unpublish_notes.py --execute            # 全部
失敗時の材料: CDO/outputs/note_publisher/unpublish_debug/<note_id>.txt / .png
"""
from __future__ import annotations
import argparse
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
DEDUP_TSV = HERE / "dedup_unpublish_list.tsv"
LOG = HERE / "unpublish_log.tsv"
DEBUG_DIR = HERE / "unpublish_debug"
PROFILE_DIR = Path.home() / ".note_publisher_profile"

# 自動で押してよい（復元可能な）操作のラベル。削除は含めない。
TARGET_LABELS = ["下書きに戻す", "下書きに変更", "公開を停止", "公開停止", "非公開にする", "下書きにする"]
# メニューを開くトリガー候補
MENU_SELECTORS = [
    'button[aria-label*="メニュー"]', 'button[aria-label*="設定"]', 'button[aria-label*="その他"]',
    'button[aria-haspopup]', '[data-testid*="menu"]', '[data-testid*="option"]',
    'button:has-text("…")', 'button:has-text("⋯")', 'button:has-text("︙")',
    'header button', 'nav button',
]


def load_targets(p: Path):
    if not p.exists():
        sys.exit(f"✗ {p} が無い。先に note_cleanup_all.py を実行。")
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("action") or line.startswith("#"):
            continue
        c = line.split("\t")
        if len(c) >= 2 and c[0].strip() == "unpublish":
            out.append((c[1].strip(), c[2].strip() if len(c) >= 3 else ""))
    return out


def _record(nid, title, result):
    new = not LOG.exists()
    with LOG.open("a", encoding="utf-8") as f:
        if new:
            f.write("# note_id\ttitle\tresult\tat(UTC)\n")
        f.write(f"{nid}\t{title}\t{result}\t{datetime.now(timezone.utc).isoformat()}\n")


def _click_target_if_present(page) -> bool:
    """画面内に下書き化/公開停止ラベルがあれば押して確定。押せたら True。"""
    for label in TARGET_LABELS:
        try:
            el = page.locator(f'text="{label}"').first
            if el.count() and el.is_visible(timeout=500):
                el.click()
                page.wait_for_timeout(600)
                for ok in ("戻す", "停止", "変更", "非公開", "はい", "OK", "実行", "確定"):
                    try:
                        b = page.locator(f'button:has-text("{ok}")').last
                        if b.is_visible(timeout=400):
                            b.click(); page.wait_for_timeout(800); break
                    except Exception:
                        continue
                return True
        except Exception:
            continue
    return False


def _scan(page):
    try:
        return page.eval_on_selector_all(
            'button, a, [role="button"], [role="menuitem"], [role="menuitemradio"], [role="link"]',
            "els => els.map(e => ({t:(e.innerText||'').trim().slice(0,40),"
            "a:(e.getAttribute('aria-label')||''),"
            "d:(e.getAttribute('data-testid')||'')})).filter(x=>x.t||x.a||x.d)",
        )
    except Exception as e:
        return [{"t": f"(scan失敗:{e})", "a": "", "d": ""}]


def _append_dump(nid, label, page):
    DEBUG_DIR.mkdir(exist_ok=True)
    items = _scan(page)
    lines = [f"\n===== {label} =====", f"URL: {page.url}", f"clickable要素 {len(items)}件:"]
    for x in items:
        lines.append(f"  text='{x['t']}' aria='{x['a']}' testid='{x['d']}'")
    with (DEBUG_DIR / f"{nid}.txt").open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    try:
        page.screenshot(path=str(DEBUG_DIR / f"{nid}_{label}.png"), full_page=True)
    except Exception:
        pass


def _try_unpublish_on_page(page) -> bool:
    """今のページで 下書きに戻す/公開停止 を探して押す。SPA描画を待ってから。"""
    page.wait_for_timeout(4500)   # SPA描画待ち
    if _click_target_if_present(page):
        return True
    for sel in MENU_SELECTORS:
        try:
            locs = page.locator(sel)
            n = min(locs.count(), 8)
            for i in range(n):
                try:
                    b = locs.nth(i)
                    if not b.is_visible(timeout=300):
                        continue
                    b.click()
                    page.wait_for_timeout(600)
                    if _click_target_if_present(page):
                        return True
                    page.keyboard.press("Escape")
                except Exception:
                    continue
        except Exception:
            continue
    return False


def _get_urlname(ctx, nid) -> str:
    for ver in ("v2", "v3", "v1"):
        try:
            r = ctx.request.get(f"https://note.com/api/{ver}/notes/{nid}", timeout=15000)
            if r.ok:
                j = r.json()
                d = j.get("data", j)
                if isinstance(d, dict) and isinstance(d.get("data"), dict):
                    d = d["data"]
                u = (d.get("user") or {}) if isinstance(d, dict) else {}
                for k in ("urlname", "url_name", "key"):
                    if u.get(k):
                        return u[k]
        except Exception:
            continue
    return ""


def revert_one(page, nid, ctx) -> str:
    # 試行A：エディタ（公開設定）画面
    try:
        page.goto(f"https://note.com/notes/{nid}/edit", timeout=30000)
        page.wait_for_load_state("load", timeout=20000)
    except Exception:
        pass
    if "accounts.google.com" in page.url or page.url.endswith("note.com/login"):
        return "not_logged_in"
    if _try_unpublish_on_page(page):
        return "ok"
    _append_dump(nid, "editor", page)

    # 試行B：自分の記事公開ページの「…」メニュー（urlname を API から取得）
    urlname = _get_urlname(ctx, nid)
    if urlname:
        try:
            page.goto(f"https://note.com/{urlname}/n/{nid}", timeout=30000)
            page.wait_for_load_state("load", timeout=20000)
            if _try_unpublish_on_page(page):
                return "ok"
            _append_dump(nid, "article", page)
        except Exception:
            pass
    else:
        with (DEBUG_DIR / f"{nid}.txt").open("a", encoding="utf-8") as f:
            f.write("\n(urlname 取得失敗：記事ページ試行スキップ)\n")
    return "manual"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", default=str(DEDUP_TSV))
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    targets = load_targets(Path(args.list))
    if args.limit > 0:
        targets = targets[:args.limit]
    print(f"対象（unpublish）: {len(targets)} 件")

    if not args.execute:
        print("【dry-run】--execute で実行。まず --execute --limit 1 推奨。\n")
        for nid, t in targets:
            print(f"  - {nid}  https://note.com/notes/{nid}/edit  「{t}」")
        return

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("✗ Playwright未インストール。setup.sh を先に。")
    if not PROFILE_DIR.exists() or not any(PROFILE_DIR.iterdir()):
        sys.exit("✗ 初回ログイン未了。 publish_to_note.py --login を先に。")

    ok = manual = fail = 0
    with sync_playwright() as p:
        ctx = None
        for kw in ({"channel": "chrome"}, {}):
            try:
                ctx = p.chromium.launch_persistent_context(
                    str(PROFILE_DIR), headless=False,
                    viewport={"width": 1280, "height": 900},
                    args=["--disable-blink-features=AutomationControlled"], **kw)
                break
            except Exception:
                continue
        if ctx is None:
            sys.exit("✗ ブラウザ起動失敗")
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        for i, (nid, t) in enumerate(targets, 1):
            try:
                r = revert_one(page, nid, ctx)
            except Exception as e:
                r = f"error:{e}"
            ok += r == "ok"; manual += r == "manual"; fail += r not in ("ok", "manual")
            _record(nid, t, r)
            print(f"  [{i}/{len(targets)}] {r}  {nid}  「{t[:30]}」")
            if r == "not_logged_in":
                print("✗ 未ログイン。publish_to_note.py --login を再実行。"); break
            page.wait_for_timeout(400)
        ctx.close()

    print(f"\n完了：下書き化 {ok} / 要手動 {manual} / 失敗 {fail}（ログ: {LOG}）")
    if manual:
        print(f"  ⚠️ manual の記事は {DEBUG_DIR}/<note_id>.txt にボタン一覧、.png にスクショを保存。")
        print("     その .txt の中身（1本ぶんでOK）を貼ってくれれば、セレクタを直して完全自動化する。")


if __name__ == "__main__":
    main()
