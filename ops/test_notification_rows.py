#!/usr/bin/env python3
"""通知欄の行から「返すべきコメント」だけを取り出せているかを確かめる。

なぜ要るか（2026-11-17・cowork 2026-11-16_001 の指摘）:
  通知欄の巡回には2つの穴があった。どちらも **返信を1回投げたら取り返しがつかない** 種類。

  ① **「あなたのコメントに返信しました」まで READY にしていた。**
     これは *よその記事に自分が書いたコメント* への返信で、ここに返すと**追撃**になる。
     cowork が毎回 SKIP で止めていたが、止めるのは道具の側の仕事。
  ② **通知の行に本文が入っていないことがある。** そのとき
     `body or text.strip()` で **行全体（「さんがあなたの記事にコメントしました」）を
     本文として DRAFT にしていた**。その文面のまま返信しかけた。

  どちらも「落とすほうに倒す」で直した。取りこぼしは記事側の巡回が拾えるが、
  **偽の本文で返信するほうは拾えない。**

使い方: python3 ops/test_notification_rows.py   （全部通れば終了0）
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]
                       / "CDO/outputs/note_publisher"))
import fetch_comments_from_notifications as F  # noqa: E402

PARSE_CASES = [
    # (名前, 通知1行の文面, 本文が取れるべきか)
    ("本文がある行は通す",
     "立山 剣\nペンネームは富山から取りました", True),
    ("本文が無い行＝説明文だけなら落とす",
     "立山 剣\nさんがあなたの記事にコメントしました", False),
    ("短い説明文だけでも落とす",
     "だれか\nがコメントしました", False),
    ("名前しか無い行も落とす",
     "だれか", False),
    ("説明文のあとに本文が続くなら通す",
     "だれか\nがコメントしました: うちでも同じようにしています", True),
]

SKIP_CASES = [
    # (通知1行の文面, 落とすべきか)
    ("Aさんがあなたのコメントに返信しました", True),
    ("Cさんがあなたの返信に返信しました", True),
    ("Dさんがスキしました", True),
    ("Eさんがフォローしました", True),
    # ★これだけは残す＝返すべき相手
    ("Bさんがあなたの記事にコメントしました", False),
]


def main() -> int:
    bad = 0
    for name, text, want_body in PARSE_CASES:
        _, body = F.parse_row(text)
        got = body is not None
        if got != want_body:
            print(f"NG  {name}: 本文={'取れた' if got else '取れない'} / "
                  f"期待={'取れる' if want_body else '取れない'} ({body!r})")
            bad += 1
        else:
            print(f"OK  {name}")

    for text, want_skip in SKIP_CASES:
        got = any(w in text for w in F.SKIP_WORDS)
        if got != want_skip:
            print(f"NG  SKIP判定: {text} → {'落とした' if got else '通した'} / "
                  f"期待={'落とす' if want_skip else '通す'}")
            bad += 1
        else:
            print(f"OK  SKIP判定: {text} → {'落とす' if got else '通す'}")

    print(f"\n{'全部通った' if not bad else str(bad) + '件 失敗'}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
