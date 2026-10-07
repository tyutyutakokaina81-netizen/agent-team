#!/usr/bin/env python3
"""**公開する前に**、記事の本文へ「あわせて読む3本＋フォローの一言」を入れる。

なぜ（2026-10-07）:
  これまでフォロー導線は `backfill_follow.sh` で**公開済みの記事に後から足していた**。
  それは 210本が行き止まりだったのを埋めるための後始末で、1日6本ずつしか進まない。
  **これから出す記事は、最初から入った状態で出すほうがいい**——
  公開直後がいちばん読まれるのに、そのときだけ導線が無い、というのは順序が逆だった。

作り:
  - 「あわせて読む」の選び方と CTA は `ops/build_follow_blocks.py` をそのまま使う
    （2つの実装を持つと必ず片方が古くなる）。
  - 入れる場所は **本文ブロックの中・英語要約の直前**。
    publisher は ```本文``` ブロックだけを note に貼るので、ここに入れないと届かない。
  - すでに「あわせて読む」がある記事は触らない（二重に入れない）。
  - `CMO/outputs/` の正本と `drafts/queue/` の両方を同じ内容に揃える。

使い方:
  python3 ops/add_follow_before_publish.py          # 何が入るか見るだけ
  python3 ops/add_follow_before_publish.py --go     # 実際に書き込む
"""
import glob
import importlib.util
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "drafts/queue")
GO = "--go" in sys.argv

_spec = importlib.util.spec_from_file_location(
    "build_follow_blocks", os.path.join(ROOT, "ops/build_follow_blocks.py"))
B = importlib.util.module_from_spec(_spec)
sys.modules["build_follow_blocks"] = B
try:
    _spec.loader.exec_module(B)
except SystemExit:
    pass

SEP = "――――――――――\n【English】"


def parse(path):
    """公開前の記事を、build_follow_blocks が扱える形にする。"""
    t = open(path, encoding="utf-8").read()
    tm = re.search(r"##\s*タイトル.*?\n```\n(.+?)\n```", t, re.S)
    bm = re.search(r"##\s*本文.*?\n```\n(.+?)\n```", t, re.S)
    if not tm or not bm:
        return None
    gm = re.search(r"##\s*ハッシュタグ.*?\n```\n(.+?)\n```", t, re.S)
    tags = {x.lstrip("#").lower() for x in re.findall(r"#\S+", gm.group(1))} if gm else set()
    cm = re.search(r"-\s*カテゴリ:\s*(.+)", t)
    kind = B.kind_of(cm.group(1) if cm else "")   # 判定は1か所にまとめる
    return {"path": path, "stem": os.path.basename(path)[:-3],
            "title": tm.group(1).strip().splitlines()[0].strip(),
            "tags": tags, "kind": kind,
            "nid": "__unpublished__" + os.path.basename(path),   # 自分自身を除くための印
            "date": os.path.basename(path)[:10], "body": bm.group(1), "text": t}


def build_block(a, arts, seed):
    rel = B.related(a, arts, 3)
    if len(rel) < 2:
        return None, rel
    cta = B.CTA[a["kind"]][seed % len(B.CTA[a["kind"]])]
    lines = ["――――――――――", cta, "", "あわせて読む"]
    for b in rel:
        lines.append(f"・{b['title']}")
        lines.append(b["url"])
    return "\n".join(lines), rel


def main():
    arts = B.load_articles()          # 公開済みだけ＝リンク切れを作らない
    files = sorted(glob.glob(os.path.join(QUEUE, "*.md")))
    if not files:
        print("公開キューが空です")
        return 0
    print(f"公開済み {len(arts)}本から選びます／キュー {len(files)}本\n")
    done = 0
    for i, qp in enumerate(files):
        a = parse(qp)
        name = os.path.basename(qp)[:-3]
        if not a:
            print(f"- {name[:44]}: タイトルか本文のブロックが読めない → 飛ばす")
            continue
        if "あわせて読む" in a["body"]:
            print(f"- {name[:44]}: すでに入っている → 触らない")
            continue
        if SEP not in a["body"]:
            print(f"- {name[:44]}: 英語要約の区切りが見つからない → 飛ばす")
            continue
        blk, rel = build_block(a, arts, i)
        if not blk:
            print(f"- {name[:44]}: 似た記事が2本未満（タグの重なり {len(rel)}本）→ 飛ばす")
            continue
        done += 1
        print(f"✓ {name[:44]}")
        print(f"    {blk.splitlines()[1]}")
        for b in rel:
            print(f"    ・{b['title'][:40]}")
        if not GO:
            continue
        new_body = a["body"].replace(SEP, blk + "\n\n" + SEP, 1)
        # 正本（CMO/outputs）とキューの両方を同じ内容にする
        for target in (os.path.join(ROOT, "CMO/outputs", os.path.basename(qp)), qp):
            if not os.path.exists(target):
                continue
            t = open(target, encoding="utf-8").read()
            if "あわせて読む" in t:
                continue
            bm = re.search(r"(##\s*本文.*?\n```\n)(.+?)(\n```)", t, re.S)
            if not bm:
                print(f"    ⚠️ {os.path.relpath(target, ROOT)}: 本文ブロックが見つからない")
                continue
            open(target, "w", encoding="utf-8").write(
                t[:bm.start(2)] + new_body + t[bm.end(2):])
    print()
    if GO:
        print(f"== 結果: {done}本に入れた ==")
        print("※ 字数が増えるので `body_stats.py --sync` を忘れずに")
    else:
        print(f"== DRY: {done}本に入る。`--go` で書き込む ==")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
