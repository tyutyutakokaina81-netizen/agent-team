#!/usr/bin/env python3
"""`_cowork_growth.py` の「再訪しない台帳」の回帰テスト（依存ゼロ・playwright 不要）。

なぜ要るのか（2026-11-19）:
  discover() が除外していたのは手書きの `TARGETS` だけで、**過去にフォローした人は
  どこにも記録されていなかった**。その結果、今朝の便は 14人試して 12人が
  already-following ＝**1便14枠のうち12枠を再訪で捨てていた**。
  直したので、次に誰かが「台帳を毎回作り直す」「err も記録する」などに変えてしまわないよう、
  **壊れたら分かる形**にしておく。

走らせ方: python3 ops/test_followed_handles.py
"""

from __future__ import annotations

import io
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "CDO/outputs/note_publisher/_cowork_growth.py"


def _load_funcs(tsv: Path):
    """playwright を import せずに、台帳まわりの関数だけ取り出して動かす。"""
    src = io.open(SRC, encoding="utf-8").read()
    seg = src[src.index("def _repo_root()"):src.index("# 厳選:")]
    ns: dict = {"Path": Path, "__file__": str(SRC), "print": lambda *a, **k: None}
    exec(compile(seg, "<growth>", "exec"), ns)
    ns["FOLLOWED_TSV"] = tsv          # 本物の台帳は触らない
    return ns


def main() -> int:
    ok = True

    def check(cond: bool, label: str) -> None:
        nonlocal ok
        print(("OK  " if cond else "NG  ") + label)
        if not cond:
            ok = False

    with tempfile.TemporaryDirectory() as d:
        tsv = Path(d) / "followed_handles.tsv"

        ns = _load_funcs(tsv)
        check(ns["load_followed"]() == set(), "台帳が無くても落ちない（空集合で続く）")

        tsv.write_text("# コメント行は読み飛ばす\n\nalready_there\t2026-11-01\tfollowed\n",
                       encoding="utf-8")
        ns = _load_funcs(tsv)
        check(ns["load_followed"]() == {"already_there"}, "コメント行と空行を読み飛ばす")

        n = ns["save_followed"]([
            {"author": "pressed",  "follow": "followed"},
            {"author": "clicked1", "follow": "clicked"},
            {"author": "dup",      "follow": "already-following"},
            {"author": "nobtn",    "follow": "no-author-follow-btn"},
            {"author": "flaky",    "follow": "err:og: - element is not visible"},
            {"author": "already_there", "follow": "already-following"},
            {"author": "",         "follow": "followed"},
        ])
        got = ns["load_followed"]()
        check(n == 4, f"追記は4件（押せた2・既フォロー1・ボタン無し1）／実際 {n}件")
        check("flaky" not in got, "★err は記録しない＝一時的な失敗は次便で再挑戦する")
        check("" not in got, "空のハンドルは書かない")
        check(sorted(got) == ["already_there", "clicked1", "dup", "nobtn", "pressed"],
              "既存行を壊さず追記だけする")

        # 2回走らせても増えない（冪等）
        before = len(ns["load_followed"]())
        ns["save_followed"]([{"author": "pressed", "follow": "followed"}])
        check(len(ns["load_followed"]()) == before, "同じ相手を二度書かない")

    # 本物のコードが台帳をリポジトリ直下の ops/ に置いているか（段数の数え間違い対策）
    ns2 = _load_funcs(ROOT / "ops" / "followed_handles.tsv")
    src = io.open(SRC, encoding="utf-8").read()
    # ※docstring の中には説明として parents[2] の話が書いてあるので、
    #   「文字列が出てこないこと」ではなく **台帳のパスの組み立て方** を見る。
    check("FOLLOWED_TSV = _repo_root() /" in src,
          "★台帳のパスを段数で数えていない（最初に parents[2]＝CDO/ と書いて間違えた）")
    check(ns2["_repo_root"]() == ROOT, "_repo_root() が ops/ を持つ親を返す")

    print("\n" + ("全部通った" if ok else "★落ちた項目がある"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
