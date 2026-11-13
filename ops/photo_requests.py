#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""写真待ちの記事を、オーナーが見て撮れる1枚のリストにして出す。

なぜ生成するのか（2026-11-13）:
写真待ちは 11本まで増え、**公開をいちばん止めているのがここ**になった。
「何を撮ればいいか」は `thumbnails/_await_photo.txt` のコメントに書いてあるが、
**巡回の記録と混ざっていて読めない**（どの語で何巡して何が来たか、が大半）。
かといってリストを手で別に書くと、このリポジトリで何度もやっている
**「2つの場所が食い違う」**失敗をまた作る。だから `_await_photo.txt` を唯一の正本にして、
そこから**撮るものと注意だけ**を抜き出して出す。

使い方:
  python3 ops/photo_requests.py              # 画面に出す
  python3 ops/photo_requests.py --write      # ops/photo_requests.md に書き出す
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "CDO/outputs/note_publisher/thumbnails/_await_photo.txt")
OUT = os.path.join(ROOT, "ops/photo_requests.md")


def parse(path):
    """各記事stemの直前にある **#撮: / #避: / #備: / #保留:** の行だけを読む。

    ★2026-11-13: 最初は「直前の連続コメントを全部拾う」作りにしたが、**取り違えた**。
      このファイルのコメントは巡回の記録が大半で、しかも写真待ちを解除した記事の
      残骸（「（旧）」）が間に挟まるため、**こたつ向けの指示が風除室の下に付いた**。
      人が読むために書かれた自由文は、機械が正しく割り当てられない。
      **間違った指示を自信ありげに出すと、オーナーの時間を無駄にする**ので、
      `_await_photo.txt` 側に**機械が読む行**を足して、そこだけを読む形に変えた。
      （正本は `_await_photo.txt` のまま＝2か所に同じことを書かない）
    """
    items, buf = [], {}
    for raw in open(path, encoding="utf-8").read().splitlines():
        s = raw.strip()
        if not s:
            continue
        for k in ("撮", "避", "備", "保留"):
            if s.startswith(f"#{k}:"):
                buf.setdefault(k, []).append(s.split(":", 1)[1].strip())
                break
        else:
            if s.startswith("#"):
                continue
            items.append((s, buf))
            buf = {}
    return items


def render(items):
    shoot = [(s, b) for s, b in items if "保留" not in b]
    hold = [(s, b) for s, b in items if "保留" in b]
    L = ["# 写真おねがいリスト（自動生成）", "",
         "> `CDO/outputs/note_publisher/thumbnails/_await_photo.txt` から生成。",
         "> **このファイルは直接編集しない**（上書きされる）。中身を直すなら",
         "> `_await_photo.txt` の `#撮:` `#避:` の行を直す。",
         "> 生成: `python3 ops/photo_requests.py --write`", "",
         f"**{len(shoot)}本**。どれも**1枚あれば公開できる**。",
         "撮ったら: `bash ops/use_my_photo.sh <写真> <記事名の一部>`", "",
         "どれにも共通の注意（A4・却下型）:", "",
         "- 人の顔（とくに子ども）／個人名が読める物／表札・郵便物・宛名",
         "- 店名・業者名・電話番号・商品の箱や袋の銘柄",
         "- 政治的な掲示物／絵画・イラスト／加工・合成した画像", ""]
    for i, (stem, b) in enumerate(shoot, 1):
        name = stem.split("_note記事_", 1)[-1] if "_note記事_" in stem else stem
        L += [f"## {i}. {name.split('_')[0]}", "", f"`{stem}`", ""]
        for x in b.get("撮", ["（撮るものの指定が `_await_photo.txt` に無い）"]):
            L.append(f"- **撮る**: {x}")
        for x in b.get("避", []):
            L.append(f"- ⚠️ **写さない**: {x}")
        for x in b.get("備", []):
            L.append(f"- 備考: {x}")
        L.append("")
    if hold:
        L += ["---", "", "## 保留（写真依頼ではない）", ""]
        for stem, b in hold:
            L.append(f"- `{stem}` — {b['保留'][0]}")
        L.append("")
    return "\n".join(L)


def main():
    if not os.path.exists(SRC):
        print(f"見つからない: {SRC}", file=sys.stderr)
        return 1
    items = parse(SRC)
    text = render(items)
    if "--write" in sys.argv:
        with open(OUT, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"書き出した: {OUT}（{len(items)}本）")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
