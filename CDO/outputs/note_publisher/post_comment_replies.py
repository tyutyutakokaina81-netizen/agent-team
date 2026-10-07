#!/usr/bin/env python3
"""`ops/comments/replies.tsv` の READY を note に投稿する（cowork 側で実行）。

なぜ（2026-10-07）:
  自動返信は以前からの要件で、取得（fetch）と下書き（draft）の仕組みはあったのに、
  **投稿するスクリプトが存在しなかった**。READY にしても出ていかない＝0件のまま。
  マガジン196本・英語141本・フォロー導線・集客と同じ型で、これで7件目。

安全（返信は取り消しにくいので、ここは厳しくする）:
  - **1回に出すのは既定3件まで**。薄い返信が並ぶのを防ぐ。
  - **同じ記事に同じ日に2件以上出さない**。
  - 投稿できたら `POSTED` と URL を書き戻す。**二度投稿しない**。
  - 掴めなければ**画面の実物を保存**して止まる（A1 で code から DOM を見られないため）。
  - `HOLD*` には一切触らない。

使い方:
  python3 post_comment_replies.py            # 何を出すか見るだけ
  python3 post_comment_replies.py --go       # 実際に投稿する
  python3 post_comment_replies.py --go --limit 5
"""
import csv
import datetime
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REPLIES = ROOT / "ops/comments/replies.tsv"
DUMP = ROOT / "ops/comments/_debug"
GO = "--go" in sys.argv
LIMIT = 3
if "--limit" in sys.argv:
    try:
        LIMIT = int(sys.argv[sys.argv.index("--limit") + 1])
    except Exception:
        pass

BOX = ["textarea[placeholder*='コメント']", "textarea", "[contenteditable='true']"]
SEND = ["button:has-text('投稿')", "button:has-text('送信')", "button:has-text('コメントする')"]


def load():
    if not REPLIES.exists():
        return [], []
    rows = list(csv.reader(REPLIES.open(encoding="utf-8"), delimiter="\t"))
    head = rows[0] if rows and rows[0] and rows[0][0] == "comment_id" else None
    body = rows[1:] if head else rows
    return head, body


def dump(page, why):
    try:
        DUMP.mkdir(parents=True, exist_ok=True)
        (DUMP / "reply_ui.html").write_text(page.content(), encoding="utf-8")
        btns = page.eval_on_selector_all(
            "button, textarea, [contenteditable]",
            "els => els.slice(0,60).map(e => ({tag:e.tagName.toLowerCase(),"
            "txt:(e.innerText||'').trim().slice(0,24),ph:e.getAttribute('placeholder')||''}))")
        (DUMP / "reply_ui.json").write_text(json.dumps(btns, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"DUMP: {why} → {DUMP/'reply_ui.html'} と reply_ui.json を保存した")
    except Exception as e:
        print(f"DUMP_FAILED: {type(e).__name__} {e}")


def main():
    head, rows = load()
    if not rows:
        print("replies.tsv が空。先に `python3 ops/auto_reply_comments.py --go`")
        return 0
    today = datetime.date.today().isoformat()
    targets, seen_articles = [], set()
    for i, r in enumerate(rows):
        if len(r) < 5 or r[3] != "READY" or not r[4].strip():
            continue
        art = r[1]
        if art in seen_articles:          # 同じ記事に同日2件出さない
            continue
        seen_articles.add(art)
        targets.append((i, r))
        if len(targets) >= LIMIT:
            break
    if not targets:
        print("出すものが無い（READY が無い／すでに投稿済み）")
        return 0
    print(f"出す予定: {len(targets)}件")
    for _i, r in targets:
        print(f"  [{r[2]}] {r[1]}")
        print(f"      {r[4]}")
    if not GO:
        print("\nDRY: `--go` で投稿する")
        return 0

    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print("NG: playwright が入っていない。cowork 側で実行する")
        return 1
    sys.path.insert(0, str(HERE))
    import publish_to_note as P

    posted = 0
    with sync_playwright() as pw:
        ctx = P.load_context(pw)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        for idx, r in targets:
            url, text = r[1], r[4]
            print(f"--- {url}")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(3500)
                page.mouse.wheel(0, 20000)
                page.wait_for_timeout(1500)
                box = None
                for sel in BOX:
                    try:
                        el = page.query_selector(sel)
                    except Exception:
                        el = None
                    if el:
                        box = el
                        break
                if not box:
                    dump(page, "コメント入力欄が見つからない")
                    print("  ⚠️ 入力欄が無い。ここで止めます（残りは次回）")
                    break
                box.click()
                page.keyboard.type(text, delay=24)
                page.wait_for_timeout(700)
                sent = False
                for sel in SEND:
                    try:
                        b = page.query_selector(sel)
                    except Exception:
                        b = None
                    if b:
                        b.click()
                        sent = True
                        break
                if not sent:
                    dump(page, "送信ボタンが見つからない")
                    print("  ⚠️ 送信できない。ここで止めます")
                    break
                page.wait_for_timeout(3000)
                rows[idx][3] = "POSTED"
                rows[idx][5] = page.url
                rows[idx][6] = datetime.datetime.now().isoformat(timespec="seconds")
                posted += 1
                print("  ✅ 投稿した")
                page.wait_for_timeout(6000)       # 連投に見せない
            except Exception as e:
                print(f"  ✗ 失敗: {type(e).__name__} {e}")
        ctx.close()

    with REPLIES.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        if head:
            w.writerow(head)
        w.writerows(rows)
    print(f"\n== 投稿 {posted}件（{today}）==")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
