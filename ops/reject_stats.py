#!/usr/bin/env python3
"""却下台帳から「どういう名前のものが来たか」を数える。

なぜ要るのか（2026-09-30）:
  却下は 173件たまっていたのに、**取得元のファイル名が残っているのは5件だけ**だった。
  そのため「名前で弾けたはずのものが何件あったか」を測れず、
  `NON_PHOTO_HINTS` や `UNUSABLE_NAME_HINTS` を**勘で足す**しかなかった。
  `ops/reject_thumb.py` が 4列目に `file:` を残すようにしたので、
  これから先はここで数えられる。数が増えたら、その語をフィルタに足す。

使い方: python3 ops/reject_stats.py
"""

from __future__ import annotations

import collections
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "CDO/outputs/note_publisher/thumbnails/_rejected_hashes.tsv"


def main() -> int:
    if not LEDGER.exists():
        print(f"台帳が無い: {LEDGER}")
        return 1
    total = with_name = 0
    words: collections.Counter[str] = collections.Counter()
    names = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        total += 1
        cols = line.split("\t")
        src = next((c[5:] for c in cols[2:] if c.startswith("file:")), "")
        if not src:
            continue
        with_name += 1
        names.append(src)
        # 語に割って数える（英字は小文字化、日本語はそのまま）
        for w in re.findall(r"[A-Za-z]{3,}|[ぁ-んァ-ヶ一-龥]{2,}", src):
            words[w.lower()] += 1

    print(f"却下 {total}件 ／ 取得元の名前が残っているもの {with_name}件")
    if with_name == 0:
        print("\n名前が残っている却下がまだありません。"
              "\n`ops/reject_thumb.py` で却下すると 4列目に file: が入ります。"
              "\nそれが溜まってから、ここで語の傾向を見てフィルタに足します。")
        return 0
    print(f"\n── よく出る語（フィルタ追加の候補）──")
    for w, c in words.most_common(25):
        if c >= 2:
            print(f"  {w:24} {c}件")
    print(f"\n── 名前の一覧 ──")
    for n in names:
        print(f"  {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
