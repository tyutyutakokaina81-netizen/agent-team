#!/usr/bin/env python3
"""**コメントをくれた人をフォローする**（cowork 側で実行・読み取り＋フォローのみ）。

なぜ（2026-10-07）:
  オーナー「コメントをフォローして」。そのとおりで、**コメントを書いた人は
  いちばんフォローバックが期待できる相手**。わざわざ名前を出して反応してくれている。
  これまでの集客はハッシュタグ検索で見つけた人だけを見ていて、
  **すでにこちらに反応してくれた人を素通りしていた**。

やること:
  - `ops/comments/pending.tsv` の author 欄から handle（@xxxx）を取る
  - その人のプロフィールを開いてフォローする
  - 済んだ相手は `ops/followed_commenters.tsv` に記録して二度行かない
  - フォロー判定は `_cowork_growth.do_follow` を使う（実装を2つ持たない）

安全:
  - **スキもコメントもしない**。フォローだけ。
  - 1回の上限は既定10人（bot 判定を避ける）。
  - 相手のページでフォローボタンを特定できなければ**押さずに記録する**。

使い方:
  python3 ops/follow_commenters.py            # 誰に行くか見るだけ
  python3 ops/follow_commenters.py --go       # 実際にフォローする
  python3 ops/follow_commenters.py --go --limit 5
"""
import csv
import datetime
import importlib.util
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PENDING = os.path.join(ROOT, "ops/comments/pending.tsv")
DONE = os.path.join(ROOT, "ops/followed_commenters.tsv")
PUBDIR = os.path.join(ROOT, "CDO/outputs/note_publisher")
GO = "--go" in sys.argv
LIMIT = 10
if "--limit" in sys.argv:
    try:
        LIMIT = int(sys.argv[sys.argv.index("--limit") + 1])
    except Exception:
        pass


def handles_from_pending():
    """author 欄から handle を取る。`名前(@handle)` または `@handle` の形。"""
    out = []
    if not os.path.exists(PENDING):
        return out
    with open(PENDING, encoding="utf-8") as fh:
        for r in csv.reader(fh, delimiter="\t"):
            if not r or r[0].startswith("comment_id") or len(r) < 3:
                continue
            m = re.search(r"@([A-Za-z0-9_]{3,30})", r[2] or "")
            if m and m.group(1) not in [h for h, _ in out]:
                out.append((m.group(1), (r[4] if len(r) > 4 else "")[:40]))
    return out


def load_done():
    done = set()
    if os.path.exists(DONE):
        for line in open(DONE, encoding="utf-8"):
            if line.startswith("#") or line.startswith("handle"):
                continue
            p = line.split("\t")
            if p:
                done.add(p[0].strip())
    return done


def main():
    cands = handles_from_pending()
    done = load_done()
    todo = [(h, t) for h, t in cands if h not in done][:LIMIT]
    print(f"コメントをくれた人: {len(cands)}人 / すでに行った: {len(done)}人 / 今回: {len(todo)}人")
    if not cands:
        print("pending.tsv に handle が入っていません。")
        print("  → 先に `bash ops/comments_now.sh`（通知欄から handle ごと取ります）")
        return 0
    for h, t in todo:
        print(f"  @{h}  ← {t}")
    if not todo:
        print("新しく行く相手はいません")
        return 0
    if not GO:
        print("\nDRY: `--go` で実際にフォローします")
        return 0

    sys.path.insert(0, PUBDIR)
    spec = importlib.util.spec_from_file_location("growth", os.path.join(PUBDIR, "_cowork_growth.py"))
    G = importlib.util.module_from_spec(spec)
    sys.modules["growth"] = G
    try:
        spec.loader.exec_module(G)
    except SystemExit:
        pass
    from playwright.sync_api import sync_playwright
    import publish_to_note as P

    rows, ok = [], 0
    now = datetime.datetime.now().isoformat(timespec="seconds")
    with sync_playwright() as pw:
        ctx = P.load_context(pw)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        for h, t in todo:
            url = f"https://note.com/{h}"
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(3000)
                r = G.do_follow(page, h)
            except Exception as e:
                r = f"err:{type(e).__name__}"
            print(f"  @{h}: {r}")
            rows.append([h, r, now])
            if r in ("followed", "clicked", "already-following"):
                ok += 1
            page.wait_for_timeout(7000)       # 連続に見せない
        ctx.close()

    head = not os.path.exists(DONE) or os.path.getsize(DONE) == 0
    with open(DONE, "a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        if head:
            w.writerow(["handle", "result", "at"])
        w.writerows(rows)
    print(f"\n== フォローできた/済み {ok}人 / 試した {len(rows)}人 ==")
    if ok == 0:
        print("⚠️ 1人も増えていません。ops/logs/follow_buttons.json を push してください")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
