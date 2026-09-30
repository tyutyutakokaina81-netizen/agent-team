#!/usr/bin/env python3
"""サムネを1本却下する。**却下に必要なことを全部やる**（手順を人が覚えない）。

なぜ要るのか（2026-09-30）:
  却下は毎回この6手順だった——md5を取る／理由を台帳に追記する／jpgを消す／
  記事を限るならスコープを付ける／同じ画像のコピーを一掃する／末尾改行を確かめる。
  手でやっていて、実際に次を取りこぼした:
    - 末尾改行を忘れて、次の追記が前の行にくっついた（2026-09-23）
    - **元のファイル名を書き忘れた**。173件の却下のうち名前が残っているのは5件だけで、
      **台帳から名前フィルタを育てられない**状態になっていた（2026-09-30 に測って判明）
    - 全角括弧を含む文字列を正規表現で囲って入れ子で止まった（2026-09-29）
  道具にすれば、覚えていなくても毎回同じことができる。

記録するもの:
  md5 <TAB> 理由 <TAB> only:<stem>[,<stem>] <TAB> file:<Commonsのファイル名>
  4列目を足したのが今回の要点。**あとで「どういう名前のものが来たか」を数えられる**。

使い方:
  python3 ops/reject_thumb.py <stem> "<理由>"                 # 全記事で不可
  python3 ops/reject_thumb.py <stem> "<理由>" --only a,b,c    # その記事だけ不可
  python3 ops/reject_thumb.py <stem> "<理由>" --dry           # 何もせず見るだけ
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THUMB = ROOT / "CDO/outputs/note_publisher/thumbnails"
LEDGER = THUMB / "_rejected_hashes.tsv"
PROV = THUMB / "_provenance.json"
VERIFIED = THUMB / "_verified.txt"


def _verified_stems() -> set[str]:
    if not VERIFIED.exists():
        return set()
    return {l.strip() for l in VERIFIED.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")}


def _source_name(stem: str) -> str:
    """その記事に今あたっている画像の、取得元ファイル名。無ければ空。"""
    try:
        v = json.loads(PROV.read_text(encoding="utf-8")).get(stem)
    except Exception:
        return ""
    return (v.get("file") or "") if isinstance(v, dict) else ""


def _append(line: str) -> None:
    """末尾改行を確かめてから足す（改行が無いと前の行にくっつく）。"""
    txt = LEDGER.read_text(encoding="utf-8") if LEDGER.exists() else ""
    if txt and not txt.endswith("\n"):
        txt += "\n"
    LEDGER.write_text(txt + line.rstrip("\n") + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stem")
    ap.add_argument("reason")
    ap.add_argument("--only", default="", help="この記事だけで不可にする（カンマ区切り）")
    ap.add_argument("--dry", action="store_true", help="何もせず、やることだけ出す")
    a = ap.parse_args()

    jpg = THUMB / f"{a.stem}.jpg"
    if not jpg.exists():
        print(f"✗ jpg が無い: {jpg.name}")
        return 1
    if a.stem in _verified_stems():
        print(f"✗ {a.stem} は **採用済み**（_verified.txt にある）。"
              "却下するならまず _verified から外すこと（採用と却下が食い違ったまま進まない）")
        return 1

    md5 = hashlib.md5(jpg.read_bytes()).hexdigest()
    src = _source_name(a.stem)
    today = datetime.date.today().isoformat()
    reason = f"{a.reason}（{today}）"
    cols = [md5, reason]
    cols.append(f"only:{a.only}" if a.only else "")
    cols.append(f"file:{src}" if src else "")
    while cols and not cols[-1]:
        cols.pop()
    line = "\t".join(cols)

    # 同じ画像が他の記事にも配られていないか
    same = [p.stem for p in THUMB.glob("*.jpg")
            if p != jpg and hashlib.md5(p.read_bytes()).hexdigest() == md5]
    ver = _verified_stems()
    same_used = [s for s in same if s in ver]

    print(f"■ 却下する: {a.stem}")
    print(f"  md5   : {md5}")
    print(f"  取得元: {src or '（記録なし）'}")
    print(f"  範囲  : {'この記事だけ（' + a.only + '）' if a.only else '全記事'}")
    if same:
        print(f"  同じ画像が他に {len(same)}本: {', '.join(s[:30] for s in same[:3])}")
    if same_used:
        print(f"  ⚠ そのうち **採用済みが {len(same_used)}本** あります: {', '.join(same_used)}")
        print("     全記事で不可にすると、その記事の見出しも消えます。--only で範囲を限るか、"
              "先に _verified から外してください。")
        if not a.only and not a.dry:
            print("  → 中止しました（--only を付けるか、先に採用を取り消すこと）")
            return 1
    if a.dry:
        print("\nDRY-RUN: 何もしていません")
        return 0

    _append(line)
    jpg.unlink()
    print(f"\n✅ 台帳に記録し、{jpg.name} を消しました")

    # 範囲内の同じ画像のコピーも消す（取得側が飛ばして取り直せなくなるため）
    scope = {x.strip() for x in a.only.split(",") if x.strip()} if a.only else None
    n = 0
    for s in same:
        if s in ver:
            continue
        if scope is not None and s not in scope:
            continue
        (THUMB / f"{s}.jpg").unlink()
        n += 1
        print(f"   コピーも削除: {s}")
    if n:
        print(f"   （{n}件）")
    print("\n次: git add -f してから commit & push（thumbnails/ は .gitignore 済）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
