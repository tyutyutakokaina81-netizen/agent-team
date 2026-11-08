#!/usr/bin/env python3
"""`ops/comments/replies.tsv` の READY を note に投稿する（cowork 側で実行）。

なぜ（2026-10-07）:
  自動返信は以前からの要件で、取得（fetch）と下書き（draft）の仕組みはあったのに、
  **投稿するスクリプトが存在しなかった**。READY にしても出ていかない＝0件のまま。
  マガジン196本・英語141本・フォロー導線・集客と同じ型で、これで7件目。

★2026-11-08 作り直し（cowork 報告 2026-11-08_001）:
  日次実行が「送信ボタンが見つからない」で止まっていた。note の送信ボタンが
  **文字の無いアイコン**に変わり、`button:has-text('投稿')` 等が当たらなくなったため。
  ただし**問題はセレクタだけではなかった**＝この script は記事下の
  **トップレベルのコメント欄**に打ち込む作りで、通っていたとしても
  **相手への返信ではなく、著者の新規コメントが1件ぶら下がるだけ**だった。
  さらに `button:has-text('投稿')` は**ヘッダの「新規投稿」と取り違えうる**
  （reply_to_comment.py の注記）。止まっていたおかげで実害が出ていなかった。
  → **投稿の仕方を、実地で動いている reply_to_comment.py の
    スレッド返信の手順に合わせた**（返信アイコン → 返信用 textarea →
    その form の中の送信アイコン）。文字で探す送信ボタンは**全部外した**。
  → 相手のコメントは **comment_id でログアウトAPIから本文を引き**、その文字列で
    DOM の該当コメントを特定する（replies.tsv に comment_id が入っている）。
  → **掴めなければ、その1件を飛ばす**。トップレベルに落として投稿することは
    **絶対にしない**（間違った場所に出すより、出さないほうがよい）。
  → 投稿後は **API の is_creator_replied で実際に付いたことを確かめてから** POSTED にする。

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

# ★文字で送信ボタンを探すのはやめた（2026-11-08）。
#   note の送信はアイコンになっていて当たらないうえ、`button:has-text('投稿')` は
#   **ヘッダの「新規投稿」**に当たりうる。押し間違えると記事の編集画面へ行く。
#   いま使うのは reply_to_comment.py で実地に動いている3つだけ:
REPLY_BTN = "button:has(svg[aria-label='返信'])"
SEND_BTN = "button[type=submit]:has(svg[aria-label='送信'])"
TOP_BOX = "textarea[aria-label='コメント入力欄']"   # ここには**打ち込まない**（位置の目印にだけ使う）


def load():
    if not REPLIES.exists():
        return [], []
    rows = list(csv.reader(REPLIES.open(encoding="utf-8"), delimiter="\t"))
    head = rows[0] if rows and rows[0] and rows[0][0] == "comment_id" else None
    body = rows[1:] if head else rows
    return head, body


def comment_text_by_id(note_key: str, comment_id: str):
    """ログアウトAPIから、その comment_id の本文を平文で返す。取れなければ None。

    返信先を DOM で特定するのに使う。**返信を出す相手を取り違えないため**、
    テキストの一致で掴む（reply_to_comment.py と同じやり方）。
    note_comments の本文は rich-text の木なので、fetch_note_comments の
    `_rich_text` で平文にする（同じ処理を2つ持たない）。
    """
    import importlib.util as _ilu
    import urllib.request
    try:
        _spec = _ilu.spec_from_file_location("_fnc_for_reply", str(HERE / "fetch_note_comments.py"))
        _m = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_m)
    except Exception as e:
        print(f"  ✗ fetch_note_comments を読めない: {type(e).__name__} {e}")
        return None
    try:
        with urllib.request.urlopen(
                f"https://note.com/api/v3/notes/{note_key}/note_comments", timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"  ✗ コメントAPIが引けない: {type(e).__name__} {e}")
        return None
    for c in (data.get("data") or []):
        if c.get("key") == comment_id:
            return (_m._rich_text(c.get("comment")) or "").strip() or None
    return None


def creator_replied(note_key: str, comment_id: str):
    """API で「著者が返信済み」になったかを見る。True/False/None(判定不能)。"""
    import urllib.request
    try:
        with urllib.request.urlopen(
                f"https://note.com/api/v3/notes/{note_key}/note_comments", timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception:
        return None
    for c in (data.get("data") or []):
        if c.get("key") == comment_id:
            return bool(c.get("is_creator_replied"))
    return None


def note_key_of(url: str):
    m = re.search(r"/n/(n[0-9a-f]{12})", url or "")
    return m.group(1) if m else ""


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
            cid = r[0]
            nkey = note_key_of(url)
            print(f"--- {url}  (comment {cid})")
            if not nkey:
                print("  ✗ URL から note_key が取れない。飛ばす")
                continue
            # ★返信先の本文を API から引く。掴めなければ**この1件は飛ばす**
            #   （トップレベルに落として投稿することはしない）。
            snippet = comment_text_by_id(nkey, cid)
            if not snippet:
                print("  ✗ 返信先のコメントが API で見つからない（消された／別記事）。飛ばす")
                continue
            snip = snippet[:24].replace("'", "")
            if len(snip) < 6:
                print("  ✗ 本文が短すぎて相手を特定できない。飛ばす")
                continue
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(4000)
                # コメント欄まで送る（**ここには打ち込まない**。位置の目印）
                try:
                    page.locator(TOP_BOX).first.scroll_into_view_if_needed()
                except Exception:
                    page.mouse.wheel(0, 20000)
                page.wait_for_timeout(2500)

                btns = page.locator(REPLY_BTN)
                n = btns.count()
                print(f"  返信ボタン: {n}個")
                target = None
                for i in range(n):
                    b = btns.nth(i)
                    cont = b.locator(
                        f"xpath=ancestor::*[contains(normalize-space(.),'{snip}')][1]")
                    if cont.count() and len(cont.first.inner_text()) < 1500:
                        target = (b, cont.first)
                        break
                if not target:
                    dump(page, f"返信先のコメントを画面で特定できない（{snip}）")
                    print("  ✗ 相手を特定できない。飛ばす（トップレベルには出さない）")
                    continue
                b, cont = target
                b.click()
                page.wait_for_timeout(1500)
                # 返信用の textarea ＝「コメント入力欄」**ではない**可視の textarea
                ta = None
                tas = page.locator("textarea")
                for i in range(tas.count()):
                    t = tas.nth(i)
                    try:
                        if t.get_attribute("aria-label") != "コメント入力欄" and t.is_visible():
                            ta = t
                    except Exception:
                        pass
                if ta is None and cont.locator("textarea").count():
                    ta = cont.locator("textarea").first
                if ta is None:
                    dump(page, "返信用の入力欄が出てこない")
                    print("  ✗ 返信欄が無い。飛ばす")
                    continue
                ta.click()
                ta.type(text, delay=20)
                page.wait_for_timeout(800)
                send = ta.locator("xpath=ancestor::form[1]").locator(SEND_BTN)
                if send.count() != 1:
                    # ★1個でないときは押さない＝どれを押すか決められない状態で押さない
                    try:
                        ta.fill("")
                    except Exception:
                        pass
                    dump(page, f"送信ボタンが{send.count()}個（1個のときだけ押す）")
                    print("  ✗ 送信ボタンを特定できない。打ち込みを消して飛ばす")
                    continue
                send.first.click()
                page.wait_for_timeout(4000)

                # ★API で実際に付いたか確かめてから POSTED にする
                ok = creator_replied(nkey, cid)
                if ok is True:
                    rows[idx][3] = "POSTED"
                    rows[idx][5] = url
                    rows[idx][6] = datetime.datetime.now().isoformat(timespec="seconds")
                    posted += 1
                    print("  ✅ 返信した（API で is_creator_replied=True を確認）")
                elif ok is False:
                    print("  ⚠️ 送信したが API では返信が付いていない。POSTED にしない"
                          "（次回また出すので、二重投稿になっていないか人が見ること）")
                else:
                    print("  ⚠️ API で確かめられなかった。POSTED にしない（次回に回す）")
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
