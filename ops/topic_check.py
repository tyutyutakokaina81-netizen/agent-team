#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""題材が既出かどうかを調べる。**記事を書く前に必ず通す。**

なぜ要るか（2026-11-14）:
10-24 の食枠に**銀杏**を選びかけたが、**ファイル名の grep では0件なのに公開済み**だった。
ファイル名が `ぎんなん`（ひらがな）で `nf705ce597b9f` として出ていた。
**grep 1回で「無い」と判断すると、同じ題材を二度書く。**
同じ引き直しで 里芋・れんこん・鮭・かまぼこ・白えび・卵焼き・納豆・こんにゃく・
白ねぎ・かぼちゃ も既出と分かった。

見るところは3つ。どれか1つでも当たれば既出の疑いとして出す:
  ① CMO/outputs のファイル名
  ② published_registry.json の**公開済みタイトル**（ファイル名と綴りが違うことがある）
  ③ 本文に何本出てくるか（主題かどうかの手がかり。多い＝よそで詳しく書いている可能性）

使い方:
  python3 ops/topic_check.py おでん 味噌汁 報恩講
  python3 ops/topic_check.py --kana おでん      # 漢字/ひらがな/カタカナを自動で足す
"""
import glob
import json
import os
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join(ROOT, "CDO/outputs/note_publisher/published_registry.json")


def kana_variants(w):
    """ひらがな⇄カタカナを行き来した綴りを足す。漢字は変換できないので、呼ぶ側が渡す。"""
    out = {w}
    hira = "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in w)
    kata = "".join(chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c for c in w)
    out.add(hira)
    out.add(kata)
    return sorted(out)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    use_kana = "--kana" in sys.argv
    if not args:
        print(__doc__)
        return 1
    titles = []
    if os.path.exists(REG):
        titles = [e.get("title", "") for e in json.load(open(REG, encoding="utf-8"))
                  if isinstance(e, dict)]
    files = [os.path.basename(f) for f in glob.glob(os.path.join(ROOT, "CMO/outputs/*note記事*.md"))]
    bodies = glob.glob(os.path.join(ROOT, "CMO/outputs/*note記事*.md"))

    for w in args:
        words = kana_variants(w) if use_kana else [w]
        th = [t for t in titles if any(x in t for x in words)]
        fh = [f for f in files if any(x in f for x in words)]
        nb = 0
        for b in bodies:
            try:
                if any(x in open(b, encoding="utf-8").read() for x in words):
                    nb += 1
            except OSError:
                pass
        mark = "×既出" if (th or fh) else "○空き"
        print(f"{mark}  {w}  （綴り: {'/'.join(words)}）")
        print(f"        公開タイトル {len(th)}件 / ファイル名 {len(fh)}件 / 本文に出てくる記事 {nb}本")
        for t in th[:3]:
            print(f"          公開: {t[:62]}")
        for f in fh[:3]:
            if not any(f[:-3] in t for t in th):
                print(f"          file: {f[:62]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
