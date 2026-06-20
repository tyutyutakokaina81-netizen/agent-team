#!/usr/bin/env python3
"""
重複noteを「下書きに戻す」補助ツール（オーナーのMacで実行）。

dedup_unpublish_list.tsv の action=unpublish 行を読み、各記事を
note 上で「下書きに戻す（=公開停止）」する。**削除ではなく下書き化＝復元可能**。

⚠️ 公開状態を変える操作。既定は dry-run（何もしない）。実行は --execute が必要。
   まず `--execute --limit 1` で1本だけ試し、UIの流れが合っているか確認してから全件へ。

前提: publish_to_note.py --login 済み（~/.note_publisher_profile）。

使い方:
  python3 unpublish_notes.py                      # dry-run：対象一覧とURLを表示するだけ
  python3 unpublish_notes.py --execute --limit 1  # 1本だけ実際に下書きへ（動作確認）
  python3 unpublish_notes.py --execute            # 全unpublish対象を下書きへ
  python3 unpublish_notes.py --list FILE          # 別の非公開化リストを使う

各記事で下書き化に失敗した場合は、その edit URL をログに残すので手動で対応できる。
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
DEDUP_TSV = HERE / "dedup_unpublish_list.tsv"
LOG = HERE / "unpublish_log.tsv"
PROFILE_DIR = Path.home() / ".note_publisher_profile"


def load_targets(list_path: Path) -> list[tuple[str, str]]:
    """action=unpublish の (note_id, title) を返す。"""
    if not list_path.exists():
        sys.exit(f"✗ リストが見つかりません: {list_path}\n"
                 f"  先に note_cleanup_all.py を実行して生成してください。")
    out = []
    for raw in list_path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip("\n")
        if not line.strip() or line.startswith("action") or line.startswith("#"):
            continue
        cols = line.split("\t")
        if len(cols) >= 2 and cols[0].strip() == "unpublish":
            out.append((cols[1].strip(), cols[2].strip() if len(cols) >= 3 else ""))
    return out


def _record(note_id: str, title: str, result: str):
    new = not LOG.exists()
    with LOG.open("a", encoding="utf-8") as f:
        if new:
            f.write("# note_id\ttitle\tresult\tat(UTC)\n")
        f.write(f"{note_id}\t{title}\t{result}\t{datetime.now(timezone.utc).isoformat()}\n")


def revert_one(page, note_id: str) -> str:
    """1記事を下書きに戻す。成功なら 'ok'、UIで見つからなければ 'manual'。"""
    url = f"https://note.com/notes/{note_id}/edit"
    page.goto(url, timeout=30000)
    page.wait_for_load_state("networkidle", timeout=20000)
    if "login" in page.url or "accounts.google.com" in page.url:
        return "not_logged_in"
    # メニュー（…）を開く → 「下書きに戻す」「公開を停止」等を探す
    for opener in ('button[aria-label*="メニュー"]', 'button[aria-label*="設定"]',
                   'button:has-text("…")', '[data-testid*="menu"]'):
        try:
            btn = page.locator(opener).first
            if btn.is_visible(timeout=800):
                btn.click()
                page.wait_for_timeout(500)
                break
        except Exception:
            continue
    for label in ("下書きに戻す", "公開を停止", "公開停止", "非公開にする", "下書きにする"):
        try:
            item = page.locator(f'text="{label}"').first
            if item.is_visible(timeout=800):
                item.click()
                page.wait_for_timeout(600)
                # 確認ダイアログ
                for ok in ("戻す", "停止", "はい", "OK", "実行"):
                    try:
                        c = page.locator(f'button:has-text("{ok}")').last
                        if c.is_visible(timeout=500):
                            c.click()
                            page.wait_for_timeout(800)
                            break
                    except Exception:
                        continue
                return "ok"
        except Exception:
            continue
    return "manual"


def main():
    ap = argparse.ArgumentParser(description="重複noteを下書きに戻す（既定dry-run）")
    ap.add_argument("--list", default=str(DEDUP_TSV))
    ap.add_argument("--execute", action="store_true", help="実際に下書き化する（無指定はdry-run）")
    ap.add_argument("--limit", type=int, default=0, help="先頭N件だけ処理（0=全件）")
    args = ap.parse_args()

    targets = load_targets(Path(args.list))
    if args.limit > 0:
        targets = targets[:args.limit]
    print(f"対象（unpublish）: {len(targets)} 件")

    if not args.execute:
        print("【dry-run】実行しません。--execute で初めて下書き化します。\n")
        for nid, t in targets:
            print(f"  - {nid}  https://note.com/notes/{nid}/edit  「{t}」")
        print(f"\n確認後の実行例: python3 {Path(__file__).name} --execute --limit 1")
        return

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("✗ Playwright未インストール。setup.sh を先に。")
    if not PROFILE_DIR.exists() or not any(PROFILE_DIR.iterdir()):
        sys.exit("✗ 初回ログイン未了。 `python3 publish_to_note.py --login` を先に。")

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
            sys.exit("✗ ブラウザ起動に失敗しました。")
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        for i, (nid, t) in enumerate(targets, 1):
            try:
                r = revert_one(page, nid)
            except Exception as e:
                r = f"error:{e}"
            if r == "ok":
                ok += 1
            elif r == "manual":
                manual += 1
            else:
                fail += 1
            _record(nid, t, r)
            print(f"  [{i}/{len(targets)}] {r}  {nid}  「{t}」")
            if r == "not_logged_in":
                print("✗ 未ログインのため中断します。 publish_to_note.py --login を再実行。")
                break
            page.wait_for_timeout(400)
        ctx.close()

    print(f"\n完了：下書き化 {ok} / 要手動 {manual} / 失敗 {fail}（ログ: {LOG}）")
    if manual or fail:
        print("  'manual'/'失敗' は上のedit URLを開いて手動で下書きに戻してください。")


if __name__ == "__main__":
    main()
