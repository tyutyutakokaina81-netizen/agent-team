#!/usr/bin/env python3
"""note 記事の本文に入っている **【English】** から、英語サイトのページ用 md を作る。

なぜ（2026-10-08）:
  英語ページ（apps/toyama-guide/en-*.html）は **2026-09-23 で生成が止まっていた**。
  その後に書いた記事36本には英語ページが無い。
  North Star は「海外の読者に読まれること」で、**海外の人は note に来ない**。
  届く場所はこの英語サイトのほうなのに、そこへ出すのが止まっていた。
  「作ってあるが繋がっていない」型の**9件目**。

  幸い、英語を書き直す必要はない。**全記事の本文に【English】が入っている**
  （R36 で担保されている）。それをページの形に移すだけでよい。

作り:
  - `## 本文` ブロックの `【English】` 以降を取る
  - 1行目を見出し（# Title）、残りを本文にする
  - slug は見出しから作る（英数とハイフンのみ）
  - 出力は `EN/waves/<日付>/<slug>.md`。その後 `deploy_wave_pages.py` が HTML にする
    （重複ゲートはそちらが持っているので、ここでは触らない）

使い方:
  python3 EN/build_pages_from_articles.py --since 2026-09-24          # 作るものを見る
  python3 EN/build_pages_from_articles.py --since 2026-09-24 --go     # md を書き出す
"""
import argparse
import datetime
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ARTS = REPO / "CMO" / "outputs"
GUIDE = REPO / "apps" / "toyama-guide"


def slugify(title: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-").lower()
    s = re.sub(r"-{2,}", "-", s)
    return s[:60] or "page"


def english_block(md_text: str):
    """本文ブロックの中の【English】以降を (見出し, 本文) で返す。無ければ None。"""
    m = re.search(r"##\s*本文.*?\n```\n(.+?)\n```", md_text, re.S)
    if not m:
        return None
    body = m.group(1)
    i = body.find("【English】")
    if i < 0:
        return None
    en = body[i + len("【English】"):].strip()
    # クレジット行（日本語）は英語ページに持ち込まない
    en = re.sub(r"（見出し画像：[^（）]*(?:（[^（）]*）[^（）]*)*）", "", en).strip()
    lines = [x.strip() for x in en.split("\n") if x.strip()]
    if not lines:
        return None
    title = lines[0].rstrip(":：")
    rest = "\n\n".join(lines[1:])
    if len(rest) < 400:          # 短すぎるものはページにしない
        return None
    return title, rest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2026-09-24")
    ap.add_argument("--go", action="store_true")
    a = ap.parse_args()

    existing = {p.stem[3:] for p in GUIDE.glob("en-*.html")}   # en- を除いた slug
    wave = REPO / "EN" / "waves" / datetime.date.today().isoformat()
    made, skipped = [], []

    for md in sorted(ARTS.glob("*note記事*.md")):
        d = md.name[:10]
        if d < a.since:
            continue
        got = english_block(md.read_text(encoding="utf-8", errors="replace"))
        if not got:
            skipped.append((md.name[:44], "【English】が無い／短すぎる"))
            continue
        title, rest = got
        slug = slugify(title)
        if slug in existing:
            skipped.append((md.name[:44], f"既に en-{slug}.html がある"))
            continue
        if any(s == slug for s, _ in [(m2, "") for m2 in [x[0] for x in made]]):
            skipped.append((md.name[:44], "同じ slug が今回すでにある"))
            continue
        made.append((slug, title, rest, md.name))

    print(f"対象 {a.since} 以降 / 作るページ {len(made)}本 / 飛ばす {len(skipped)}本")
    for slug, title, _r, src in made[:12]:
        print(f"  + en-{slug}.html  ← {title[:46]}")
    if len(made) > 12:
        print(f"  ほか {len(made) - 12}本")
    for name, why in skipped[:8]:
        print(f"  - {name}: {why}")

    if not a.go:
        print("\nDRY: `--go` で EN/waves/ に書き出す")
        return 0
    if not made:
        print("作るものが無い")
        return 0

    wave.mkdir(parents=True, exist_ok=True)
    for slug, title, rest, _src in made:
        (wave / f"{slug}.md").write_text(f"# {title}\n\n{rest}\n", encoding="utf-8")
    print(f"\n書き出した: {wave}（{len(made)}本）")
    print("次:")
    print(f"  python3 EN/deploy_wave_pages.py {wave.relative_to(REPO)} " +
          " ".join(s for s, _t, _r, _x in made[:6]) + (" ..." if len(made) > 6 else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
