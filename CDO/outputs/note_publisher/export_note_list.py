#!/usr/bin/env python3
"""
note 公開記事の一覧を自動エクスポートする（オーナーのMacで実行）。

reconcile_ledger.py の入力(TSV: note_id<TAB>title)を、手コピペ無しで作るためのツール。
publish_to_note.py と同じ「ログイン済み本物Chromeプロファイル」を使うので、
note の自分の記事一覧ページを開いて、リンク(note_id)と表示タイトルを総ざらいする。

前提: `python3 publish_to_note.py --login` 済み（~/.note_publisher_profile がある）。

使い方:
  python3 export_note_list.py                     # 既定: note_published_export.tsv に書き出し
  python3 export_note_list.py --out mylist.tsv    # 出力先を指定
  python3 export_note_list.py --max-scroll 80     # 件数が多くて取りこぼす場合に増やす

出力後の流れ:
  python3 reconcile_ledger.py --note-export note_published_export.tsv --out reconcile_report.md

⚠️ note の DOM 変更でリンクが取れない場合は、取得URLとヒット件数を見てセレクタ調整が必要。
   その時は inspect_note_list.py の出力を貼ってくれれば調整する。
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("Playwright未インストール。setup.sh を先に実行してください。")

PROFILE_DIR = Path.home() / ".note_publisher_profile"
HERE = Path(__file__).resolve().parent
# 自分の記事管理ページ候補（ログイン状態で公開記事が並ぶ）
LIST_URLS = ["https://note.com/notes", "https://note.com/"]
NOTE_ID_RE = re.compile(r"/(n[0-9a-f]{8,})")   # 記事URL中の note_id（例 /n75868bbf7284 や /n/xxxx）


def launch(p):
    if not PROFILE_DIR.exists() or not any(PROFILE_DIR.iterdir()):
        sys.exit("初回ログインがまだです。 `python3 publish_to_note.py --login` を先に。")
    for kw in ({"channel": "chrome"}, {}):
        try:
            return p.chromium.launch_persistent_context(
                str(PROFILE_DIR), headless=False,
                viewport={"width": 1280, "height": 900},
                args=["--disable-blink-features=AutomationControlled"], **kw)
        except Exception:
            continue
    raise RuntimeError("ブラウザ起動失敗")


def harvest(page, max_scroll: int) -> dict:
    """ページを下までスクロールしながら、記事リンク(note_id→title)を収集する。"""
    found: dict[str, str] = {}
    stable = 0
    for i in range(max_scroll):
        anchors = page.eval_on_selector_all(
            "a",
            "els => els.map(e => ({h: e.getAttribute('href') || '', t: (e.innerText||'').trim()}))",
        )
        before = len(found)
        for a in anchors:
            m = NOTE_ID_RE.search(a["h"])
            if not m:
                continue
            nid = m.group(1)
            title = a["t"].splitlines()[0].strip() if a["t"] else ""
            # タイトルが空 or 既出で内容が薄い場合は、より良いタイトルが来たら上書き
            if title and (nid not in found or len(found[nid]) < len(title)):
                found[nid] = title
            elif nid not in found:
                found[nid] = found.get(nid, "")
        # スクロールして遅延ロードを促す
        page.mouse.wheel(0, 4000)
        page.wait_for_timeout(700)
        if len(found) == before:
            stable += 1
            if stable >= 4:   # 4回連続で増えなければ打ち切り
                break
        else:
            stable = 0
    return found


def main():
    ap = argparse.ArgumentParser(description="note公開記事の一覧をTSVにエクスポート")
    ap.add_argument("--out", default=str(HERE / "note_published_export.tsv"))
    ap.add_argument("--max-scroll", type=int, default=60)
    args = ap.parse_args()

    all_found: dict[str, str] = {}
    with sync_playwright() as p:
        ctx = launch(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        for url in LIST_URLS:
            try:
                page.goto(url, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=20000)
            except Exception as e:
                print(f"⚠️ {url} 取得失敗: {e}")
                continue
            if "login" in page.url or "accounts.google.com" in page.url:
                ctx.close()
                sys.exit("✗ 未ログイン状態です。 `python3 publish_to_note.py --login` を再実行してください。")
            got = harvest(page, args.max_scroll)
            print(f"  {url} → 記事リンク {len(got)} 件")
            for nid, t in got.items():
                if t and (nid not in all_found or len(all_found[nid]) < len(t)):
                    all_found[nid] = t
                else:
                    all_found.setdefault(nid, t)
        ctx.close()

    if not all_found:
        sys.exit("✗ 記事リンクを1件も取得できませんでした。inspect_note_list.py の出力を貼ってください（セレクタ調整します）。")

    out = Path(args.out)
    lines = ["note_id\ttitle"]
    blank = 0
    for nid, t in sorted(all_found.items(), key=lambda x: x[1]):
        if not t:
            blank += 1
        lines.append(f"{nid}\t{t}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\n✅ {len(all_found)} 件を書き出しました: {out}")
    if blank:
        print(f"   ⚠️ うち {blank} 件はタイトル空（一覧で表示文字が拾えず）。reconcile前に手で補完推奨。")
    print("次へ:")
    print(f"  python3 {HERE / 'reconcile_ledger.py'} --note-export {out} --out reconcile_report.md")


if __name__ == "__main__":
    main()
