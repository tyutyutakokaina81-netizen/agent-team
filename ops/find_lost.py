#!/usr/bin/env python3
"""**自動バックアップの merge に捨てられたファイルの候補を出す（戻しはしない）。**

なぜ（2026-10-21）:
  Mac の「自動バックアップ」が毎晩 18:09〜18:11 に
  `merge: sync with origin before auto-backup` を作る。この merge は
  **origin 側で増えたファイルを、自分の側に合わせて捨てる**。
  履歴には残る（`--is-ancestor` は通る）のに**中身だけ消える**ので気づきにくい。
  確認済み: `76ff01f`(10-19 18:09) が `_await_photo.txt` を消した。
  同じ merge が 10-09 / 10-13 / 10-14 / 10-19 / 10-20 にある。
  これまでに記事5本・サムネ5枚・R43/R44・R46・workflow の1ステップ・run_request が消えた。

★**一括復元は付けない。2回つくって2回とも誤った。**
  1回目 `git log -m --diff-filter=D` … 両方の親から見た削除が出て、
        **意図的に消したファイルまで**復活させた（95件・取り消した）。
  2回目 `git diff <merge>^2 <merge>` … 親の順番の読みが甘く、やはり同じ95件を戻した（取り消した）。
  **「消された」のか「自分が消した」のかを、履歴だけから機械が判別しきれていない。**
  だからここは**候補を出すまで**。戻すのは1本ずつ `git checkout <コミット> -- <パス>` で選ぶ。

使い方: python3 ops/find_lost.py
"""
from __future__ import annotations

import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARK = "merge: sync with origin before auto-backup"


def git(*a):
    return subprocess.run(["git", "-c", "core.quotepath=false", *a], cwd=ROOT,
                          capture_output=True, text=True, timeout=60).stdout


def main():
    merges = [l.split()[0] for l in git("log", "-n200", "--pretty=%H %s").splitlines() if MARK in l]
    print(f"自動バックアップの merge: {len(merges)}件")
    lost = {}
    for m in merges:
        for p in {x.strip() for x in
                  git("log", "-m", "--diff-filter=D", "--name-only", "--pretty=format:", "-1", m).splitlines()
                  if x.strip()}:
            if not os.path.exists(os.path.join(ROOT, p)):
                lost.setdefault(p, m)
    if not lost:
        print("候補なし")
        return 0
    print(f"\n**いま存在しない候補: {len(lost)}件**（意図的に消したものも混ざる。必ず中身を見て選ぶこと）")
    for p, m in sorted(lost.items())[:40]:
        print(f"  {m[:7]}  {p}")
    if len(lost) > 40:
        print(f"  … ほか {len(lost)-40}件")
    print("\n戻すとき: git checkout <消される前のコミット> -- <パス>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
