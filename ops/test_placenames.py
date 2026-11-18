#!/usr/bin/env python3
"""ファイル名の地名判定を確かめる（`ops/placenames.py`）。

なぜ要るか（2026-11-19）:
  この判定は **R30（採用後の検査）** と **取得側（fetch_thumbnails_wikimedia）** の
  **両方から使われる**。片方で直して片方で壊す、が起きやすい場所。

  とくに守りたいのは **「開示していれば通す」** ほう。
  ここを雑に作ると**ちゃんと断っている記事まで落ちる**＝検査が嘘をつく側の失敗で、
  2026-11-13 に実際に起きている（おやき＝ファイル名が `Nagano`、本文は漢字の「長野」で
  14回出てくるのに、ローマ字と漢字を突き合わせていなかったため BROKEN になった）。

使い方: python3 ops/test_placenames.py   （全部通れば終了0）
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

_spec = importlib.util.spec_from_file_location(
    "placenames", str(pathlib.Path(__file__).resolve().parent / "placenames.py"))
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)

CASES = [
    # (名前, ファイル名, 記事のstem, 本文, 落とすべきか)
    ("駅名は落とす",
     "File:生麦駅の踏切 (53817289866).jpg", "2026-10-29_note記事_踏切", "", True),
    ("路線名＋駅名も落とす",
     "File:木次線「三井野原駅」の駅舎と線路（2020年8月）.jpg", "2026-10-29_note記事_踏切", "", True),
    ("町名は落とす",
     "File:牛たん 名掛丁.jpg", "2026-10-26_note記事_厚揚げ", "", True),
    ("地区名(ローマ字)も落とす",
     "File:Anmitsu by jetalone in Akasaka, Tokyo.jpg", "2026-08-12_note記事_あんみつ", "", True),
    ("施設名も落とす",
     "File:丸尾カルシウム 白沙荘.jpg", "2026-10-30_note記事_物置", "", True),

    # ★ここから下は「落としてはいけない」側。こちらのほうが事故が重い。
    ("記事名に地名があれば通す",
     "File:Himi Fishing Port.jpg", "2026-07-11_note記事_氷見の干物", "", False),
    ("本文に漢字で書いてあれば、ファイル名がローマ字でも通す",
     "File:Nozawana-Oyaki-Nagano.JPG", "2026-10-xx_おやき", "長野のおやきの話。長野では…", False),
    ("「撮影地は県外」と断ってあれば通す",
     "File:Swan with train／ 白鳥飛来と学園都市線 - panoramio.jpg",
     "2026-10-26_note記事_白鳥", "（見出し画像：… ／ ※撮影地は富山県外）", False),
    ("地名が入っていなければ通す",
     "File:焼き餃子 (2597379807).jpg", "2026-10-27_note記事_宇都宮の餃子", "", False),
    ("業者名だけなら通す（町名が無い）",
     "File:伊予蒲鉾 ディープライス じゃこ天 20250403 01.jpg",
     "2026-10-30_note記事_じゃこ天", "愛媛のじゃこ天の話。", False),
    ("富山は地元なので地名として数えない",
     "File:富山 ますのすし.jpg", "2026-07-30_note記事_鱒寿司", "", False),
]


def main() -> int:
    bad = 0
    for name, fn, stem, body, want_drop in CASES:
        got = P.mismatched_place(fn, stem, body)
        dropped = got is not None
        if dropped != want_drop:
            print(f"NG  {name}: {'落とした' if dropped else '通した'}"
                  f"（期待={'落とす' if want_drop else '通す'}）→ {got!r}  [{fn}]")
            bad += 1
        else:
            print(f"OK  {name}" + (f" → {got}" if got else ""))
    print(f"\n{'全部通った' if not bad else str(bad) + '件 失敗'}  （地名 {len(P.ALL_PLACES)} 語）")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
