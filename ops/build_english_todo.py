#!/usr/bin/env python3
"""公開済みなのに **note 上は日本語だけ**の記事を洗い出して todo を作る。

背景（2026-09-30）: 英語要約を `## 本文` ブロックの外に書いていたため、md には英語があるのに
note には日本語しか貼られていなかった。md 側は `ops/inline_english.py` で直したが、
**すでに公開した記事は note を更新しないと変わらない**。その対象一覧がこれ。

出力: ops/english_backfill_todo.tsv （NID / md / タイトル）
     すでに済んだものは ops/english_backfill_done.tsv に記録し、ここからは外す。
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join(ROOT, "CDO/outputs/note_publisher/published_registry.json")
TODO = os.path.join(ROOT, "ops/english_backfill_todo.tsv")
DONE = os.path.join(ROOT, "ops/english_backfill_done.tsv")


def main() -> int:
    reg = json.load(open(REG, encoding="utf-8"))
    by_title = {}
    for r in reg:
        if r.get("unpublished"):
            continue
        m = re.search(r"/n/(n[0-9a-f]+)", r.get("url", ""))
        if m:
            by_title.setdefault(r["title"], m.group(1))

    done = set()
    if os.path.exists(DONE):
        done = {l.split("\t")[0].strip() for l in open(DONE, encoding="utf-8")
                if l.strip() and not l.startswith("#")}

    # 対象は **今回英語を足した記事だけ**。もともと本文に英語が入っていた記事（〜8月）を
    # 混ぜると、開いて SKIP_HAS_ENGLISH と出るだけの記事を100本ブラウザで回すことになる。
    inlined = os.path.join(ROOT, "ops/english_inlined.tsv")
    targets = [l.strip() for l in open(inlined, encoding="utf-8")
               if l.strip() and not l.startswith("#")]

    rows, no_nid = [], 0
    for rel in targets:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            continue
        t = open(p, encoding="utf-8").read()
        if "【English】" not in t:
            continue
        tm = re.search(r"##\s*タイトル.*?\n```\n(.+?)\n```", t, re.S)
        if not tm:
            continue
        title = tm.group(1).strip().splitlines()[0].strip()
        nid = by_title.get(title)
        if not nid:
            no_nid += 1
            continue
        if nid in done:
            continue
        rows.append((nid, os.path.relpath(p, ROOT), title))

    with open(TODO, "w", encoding="utf-8") as f:
        f.write("# NID\tmd\tタイトル  （ops/backfill_english.sh が上から順に処理する）\n")
        for r in rows:
            f.write("\t".join(r) + "\n")
    print(f"公開済みで英語をまだ足していない記事: {len(rows)}本 → {os.path.relpath(TODO, ROOT)}")
    print(f"（済み {len(done)}本 / まだ公開していない記事 {no_nid}本は対象外）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
