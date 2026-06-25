#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""アフィリエイトID(A8の a8mat)を全ページ一括で"自分のID"に差し替えるツール（収益化の確実化）。

背景：apps/toyama-guide の各記事には A8経由の収益リンクが直接埋め込まれている。
  ・じゃらん    … a8mat=1CCUH0+929KAA+14CS+64RJ5     （約70箇所）
  ・楽天        … a8mat=1U7G8Q+5LTYUQ+2HOM+686ZL     （約49箇所）
これらが owner 本人のA8 IDでないと、クリックされても報酬は別人に入る。
手で全ファイル直すのは大変なので、このツールが「現在のID → 新しいID」を**完全一致で安全に**一括置換する。

使い方（まずドライラン＝確認のみ。--apply で確定）：
  python3 tools/set_affiliate_id.py --show                       # 現在のIDと出現数
  python3 tools/set_affiliate_id.py --jalan  "NEW+A8MAT+ID+HERE"  # 確認のみ
  python3 tools/set_affiliate_id.py --jalan  "NEW+A8MAT+ID+HERE" --apply
  python3 tools/set_affiliate_id.py --rakuten "NEW+A8MAT+ID+HERE" --apply

owner がやること：A8管理画面で自分の「じゃらん」「楽天」プロモーションリンクを開き、
URL内の  a8mat=◯◯◯◯  の ◯◯◯◯ をコピーして code に伝えるだけ。code が反映して push。
"""
import argparse, glob, re, sys

GUIDE = "apps/toyama-guide"
# 現在埋め込まれている既知のID（完全一致で置換するため固定）
CURRENT = {
    "jalan":   "1CCUH0+929KAA+14CS+64RJ5",
    "rakuten": "1U7G8Q+5LTYUQ+2HOM+686ZL",
}
A8MAT_RE = re.compile(r'a8mat=([0-9A-Z]+\+[0-9A-Z]+\+[0-9A-Z]+\+[0-9A-Z]+)')

def files():
    return sorted(glob.glob(f"{GUIDE}/*.html"))

def show():
    counts = {}
    for f in files():
        for m in A8MAT_RE.findall(open(f, encoding="utf-8").read()):
            counts[m] = counts.get(m, 0) + 1
    print("== 現在埋め込まれている A8 a8mat（出現数）==")
    for k, v in sorted(counts.items(), key=lambda x: -x[1]):
        who = next((name for name, val in CURRENT.items() if val == k), "?")
        print(f"  {v:4}  {k}   [{who}]")

def replace(old, new, apply):
    if not re.fullmatch(r'[0-9A-Z]+\+[0-9A-Z]+\+[0-9A-Z]+\+[0-9A-Z]+', new):
        print(f"✗ a8mat の形式が不正: {new}（例 1ABCDE+FGHIJK+1AB+23CD4）", file=sys.stderr); sys.exit(1)
    total = touched = 0
    for f in files():
        s = open(f, encoding="utf-8").read()
        n = s.count("a8mat=" + old)
        if n:
            total += n; touched += 1
            if apply:
                open(f, "w", encoding="utf-8").write(s.replace("a8mat=" + old, "a8mat=" + new))
    print(f"  {old} → {new} : {total}箇所 / {touched}ファイル" +
          ("（書込み済）" if apply else "（ドライラン：--apply で確定）"))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--jalan", help="じゃらんの新しい a8mat")
    ap.add_argument("--rakuten", help="楽天の新しい a8mat")
    ap.add_argument("--apply", action="store_true", help="実際に書き換え（無いとドライラン）")
    a = ap.parse_args()
    if a.show or (not a.jalan and not a.rakuten):
        show()
        if not (a.jalan or a.rakuten):
            return
    if a.jalan:
        replace(CURRENT["jalan"], a.jalan, a.apply)
    if a.rakuten:
        replace(CURRENT["rakuten"], a.rakuten, a.apply)

if __name__ == "__main__":
    main()
