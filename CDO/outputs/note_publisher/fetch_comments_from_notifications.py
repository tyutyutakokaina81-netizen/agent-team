#!/usr/bin/env python3
"""note の**通知欄**からコメントを拾う（cowork 側で実行・読み取りのみ）。

なぜ作ったか（2026-10-07）:
  これまでは **公開記事を1本ずつ巡回して** コメント欄を探していた。237本あるので時間がかかり、
  しかも「一度見た記事は二度と見ない」作りだったため、**既存記事に後から来たコメントが
  構造的に見つからなかった**（10/06 に判明して直した）。
  だが、そもそも**オーナーが「コメントきてる」と気づくのは通知欄**だ。
  通知欄なら**1ページで、どの記事に来たかに関係なく**新着が並ぶ。
  巡回は「取りこぼしが無いか」の確認用に残し、**日々の入口はこちらにする**。

設計:
  - **読み取りのみ**。note 側を一切変更しない（返信も投稿もしない）。
  - 取れなければ**画面の実物を保存**する（A1 で code から DOM を見られないため）。
    保存さえされれば、code が中身を読んで返信文を書ける。
  - 既存の `ops/comments/pending.tsv` にそのまま追記する（下流の仕分けを変えない）。
  - comment_id は **記事URL + 相手 + 本文の先頭** で作る。note 側の id が取れなくても
    再取得で同じ値になり、二重に登録されない。

使い方:
  python3 fetch_comments_from_notifications.py          # 見るだけ
  python3 fetch_comments_from_notifications.py --go     # pending.tsv に追記する
"""
import csv
import datetime
import hashlib
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
COMMENT_DIR = ROOT / "ops" / "comments"
PENDING = COMMENT_DIR / "pending.tsv"
DUMP_DIR = COMMENT_DIR / "_debug"
GO = "--go" in sys.argv

# note の通知ページ。変わることがあるので順に試す。
URLS = [
    "https://note.com/notifications",
    "https://note.com/notification",
    "https://note.com/sitesettings/notifications",
]

# 通知欄には「スキ」「フォロー」「コメント」が混ざる。コメントだけを採る。
COMMENT_WORDS = ("コメント", "返信")
SKIP_WORDS = ("スキしました", "フォローしました", "マガジンに追加")


def detect_lang(text: str) -> str:
    return "ja" if re.search(r"[ぁ-んァ-ヶ一-龥]", text or "") else "en"


def load_seen() -> set:
    if not PENDING.exists():
        return set()
    out = set()
    with PENDING.open(encoding="utf-8") as fh:
        for row in csv.reader(fh, delimiter="\t"):
            if row and not row[0].startswith("comment_id"):
                out.add(row[0])
    return out


def dump(page, why: str):
    try:
        DUMP_DIR.mkdir(parents=True, exist_ok=True)
        p = DUMP_DIR / "notifications.html"
        p.write_text(page.content(), encoding="utf-8")
        txt = DUMP_DIR / "notifications.txt"
        txt.write_text(page.inner_text("body")[:20000], encoding="utf-8")
        print(f"DUMP: {why}")
        print(f"      画面の実物を {p} と {txt} に保存した。")
        print("      これを push すれば code が中身を読んで返信文を書けます")
    except Exception as e:
        print(f"DUMP_FAILED: {type(e).__name__} {e}")


_ROWS_JS = r"""() => {
  // 通知の行は作りが変わるので、**クラス名に頼らない**。
  // 記事へのリンク(/n/nXXXX)を持つ最小のまとまりを1行とみなす。
  const out = [];
  const seen = new Set();
  for (const a of document.querySelectorAll("a[href*='/n/n']")) {
    const m = (a.getAttribute('href') || '').match(/\/n\/(n[0-9a-f]{12})/);
    if (!m) continue;
    let row = a;
    for (let i = 0; i < 6 && row; i++) {
      row = row.parentElement;
      if (!row) break;
      const t = (row.innerText || '').trim();
      if (t.length > 40) break;
    }
    if (!row) continue;
    const text = (row.innerText || '').replace(/ /g, ' ').trim();
    const key = m[1] + '|' + text.slice(0, 60);
    if (seen.has(key)) continue;
    seen.add(key);
    out.push({nid: m[1], href: a.getAttribute('href'), text: text});
  }
  return out;
}"""


def parse_row(text: str):
    """通知1行から (相手, コメント本文) を取る。取れなければ (None, None)。

    note の文面は変わりうるので、**行全体を残したうえで**切り出しを試す。
    切り出せなくても、行全体を本文として扱えば返信は書ける（捨てない）。
    """
    lines = [x.strip() for x in text.split("\n") if x.strip()]
    if not lines:
        return None, None
    author = lines[0][:40]
    body = " ".join(lines[1:]).strip()
    # 「〜さんがコメントしました」のような説明行を落とす
    body = re.sub(r"^(さん)?が?(コメント|返信)(を)?(しました|를)?[：:]?\s*", "", body)
    return author, (body or text.strip())


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print("NG: playwright が入っていない。cowork 側（owner の Mac）で実行する")
        return 1
    sys.path.insert(0, str(HERE))
    import publish_to_note as P

    with sync_playwright() as pw:
        ctx = P.load_context(pw)                 # 公開と同じログイン済みプロファイル
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        opened = None
        for u in URLS:
            try:
                page.goto(u, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(3000)
                body = page.inner_text("body")
                if "ログイン" in body[:200] and "/login" in page.url:
                    print(f"NG: ログインが切れている → `python3 publish_to_note.py --login`")
                    return 1
                if len(body.strip()) > 200:
                    opened = u
                    break
            except Exception as e:
                print(f"OPEN_FAILED {u}: {type(e).__name__} {e}")
        if not opened:
            dump(page, "通知ページを開けなかった（URL が変わった可能性）")
            return 1
        print(f"OPEN: {opened}")

        # 通知は下に続くので少し送る
        for _ in range(8):
            page.mouse.wheel(0, 3000)
            page.wait_for_timeout(700)

        try:
            rows = page.evaluate(_ROWS_JS)
        except Exception as e:
            dump(page, f"行を取れなかった: {type(e).__name__} {e}")
            return 1
        print(f"通知の行: {len(rows)}")

        cands = []
        for r in rows:
            t = r["text"]
            if any(w in t for w in SKIP_WORDS):
                continue
            if not any(w in t for w in COMMENT_WORDS):
                continue
            cands.append(r)
        print(f"コメントらしい行: {len(cands)}")

        if not cands:
            # **0件を黙って信じない**。行自体が取れているかで意味が変わる。
            dump(page, f"コメントらしい行が0件（通知の行は {len(rows)} 件取れている）")
            print("→ 通知の文面が想定と違う可能性。保存した実物を push してください")
            ctx.close()
            return 0

        seen = load_seen()
        now = datetime.datetime.now().isoformat(timespec="seconds")
        new = []
        for r in cands:
            author, body = parse_row(r["text"])
            if not body:
                continue
            url = f"https://note.com{r['href']}" if r["href"].startswith("/") else r["href"]
            cid = "ntf_" + hashlib.md5(
                (r["nid"] + "|" + (author or "") + "|" + body[:40]).encode("utf-8")).hexdigest()[:16]
            if cid in seen:
                continue
            new.append([cid, url, author or "", detect_lang(body), body, now])
            print(f"  + {author}: {body[:60]}")
        ctx.close()

    if not new:
        print("新しいコメントは無い（すでに pending.tsv にある分だけ）")
        return 0
    if not GO:
        print(f"\nDRY: {len(new)}件。`--go` で pending.tsv に追記する")
        return 0

    PENDING.parent.mkdir(parents=True, exist_ok=True)
    head = not PENDING.exists() or PENDING.stat().st_size == 0
    with PENDING.open("a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        if head:
            w.writerow(["comment_id", "article", "author", "lang", "text", "fetched_at"])
        w.writerows(new)
    print(f"\n{len(new)}件を {PENDING} に追記した")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
