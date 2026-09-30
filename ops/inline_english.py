#!/usr/bin/env python3
"""記事mdに書いてある英語要約を、公開される「## 本文」ブロックの中へ入れる。

なぜ必要か（2026-09-30 に判明）:
  publisher は `## 本文` 直下の ``` ブロックだけを note に貼る。
  英語要約は `## English Summary` セクション＝**ブロックの外**に書いていたため、
  9/1 以降の60本は **note 上では日本語だけ**で公開されていた。
  8月までは本文の末尾に `【English】` として入れていた（＝公開されていた）。
  North Star が「海外読者に読まれる」なので、これは最大の取りこぼし。

使い方:
  python3 ops/inline_english.py                 # 対象を出すだけ（何も書かない）
  python3 ops/inline_english.py --go            # md を書き換える
  python3 ops/inline_english.py --go --only 2026-10-04
"""
import argparse, glob, re, sys

SEP = "――――――――――"
BODY_RE = re.compile(r"(##\s*本文.*?\n```\n)(.+?)(\n```)", re.S)
EN_HEAD = (r"(?:##\s*(?:English Summary|英語要約|English \(for overseas readers\))"
           r"|\U0001F30F\s*For English readers)\s*\n")
SENT = re.compile(r"\b(?:[A-Za-z][A-Za-z'\-,\.]*\s+){7,}[A-Za-z]")


def strip_credit(body: str) -> str:
    """英文の有無を見るとき、見出し画像クレジット行（URL入り）を行ごと外す。
    ※全角括弧の入れ子があるので `（見出し画像：[^）]*）` では取り切れない（過去に踏んだ）。"""
    keep = [l for l in body.split("\n")
            if "見出し画像" not in l and not l.strip().startswith("http")]
    return "\n".join(keep)


def extract_en(text: str):
    """英語要約セクションから (見出し, 本文) を取り出す。"""
    m = re.search(EN_HEAD + r"(.*?)(?=\n##\s|\n---\s*\n|\Z)", text, re.S)
    if not m:
        return None
    chunk = m.group(1).strip()
    lines = [l.strip() for l in chunk.split("\n") if l.strip()]
    if not lines:
        return None
    title, rest = "", lines
    if lines[0].startswith("**") and lines[0].endswith("**"):
        title = lines[0].strip("*").strip()
        rest = lines[1:]
    para = "\n\n".join(l.lstrip("> ").strip() for l in rest)
    if not SENT.search(para):
        return None
    return title, para


def inline(text: str):
    bm = BODY_RE.search(text)
    if not bm:
        return None, "本文ブロックが無い"
    body = bm.group(2)
    if SENT.search(strip_credit(body)):
        return None, "すでに本文に英文がある"
    en = extract_en(text)
    if not en:
        return None, "英語要約が読めない"
    title, para = en
    block = SEP + "\n【English】" + (title + "\n\n" if title else "") + para

    lines = body.split("\n")
    # 末尾の見出し画像クレジット行より前に入れる（クレジットは本文の最後に置く約束）
    at = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip() and "見出し画像" not in lines[i]:
            at = i + 1
            break
    new = "\n".join(lines[:at] + ["", block] + lines[at:])
    return text[:bm.start(2)] + new + text[bm.end(2):], "OK"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--go", action="store_true", help="実際に md を書き換える")
    ap.add_argument("--only", default="", help="ファイル名の部分一致で絞る")
    a = ap.parse_args()

    done = skipped = 0
    for p in sorted(glob.glob("CMO/outputs/*note記事*.md")):
        if a.only and a.only not in p:
            continue
        text = open(p, encoding="utf-8").read()
        new, why = inline(text)
        if new is None:
            if why != "すでに本文に英文がある":
                print(f"skip {p.split('/')[-1][:52]} … {why}")
                skipped += 1
            continue
        print(f"{'書き換え' if a.go else '対象  '} {p.split('/')[-1][:52]}")
        if a.go:
            open(p, "w", encoding="utf-8").write(new)
            # 公開済みの記事は md を直しても note は変わらない。**どれを直したか**を残して
            # ops/build_english_todo.py が note 側の追記対象を作れるようにする。
            with open("ops/english_inlined.tsv", "a", encoding="utf-8") as fp:
                fp.write(p + "\n")
        done += 1
    print(f"\n{'書き換えた' if a.go else '対象'}: {done}本 / 読めず飛ばした: {skipped}本")
    if not a.go and done:
        print("→ 実行するには --go を付ける")


if __name__ == "__main__":
    sys.exit(main())
