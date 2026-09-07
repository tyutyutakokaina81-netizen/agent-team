#!/usr/bin/env python3
"""記事本文の文字数を**1か所で**数えるための共有モジュール兼CLI。

背景（CQO指摘・中2 / D4の再発）:
記事メタの「文字数」を毎回その場で数えていたため、**2日で基準が変わっていた**。
- 2026-09-07/08 の2本: `len(body)`（改行込み）= copy_body.py の表示と同じ基準
- 2026-09-09 の2本: 空白・改行を除いた数（約30字ずれる）
数え方が漂うと「メタと実測が一致しているか」を機械で確かめられない。
**正本は copy_body.py と同じ `len(body)`**（noteに貼り付けられる文字列そのものの長さ）とし、
記事メタもこの関数で書く。

使い方:
  python3 CDO/outputs/note_publisher/body_stats.py <記事.md> [...]        # 実測を表示
  python3 CDO/outputs/note_publisher/body_stats.py --sync <記事.md> [...] # メタの字数を実測に書き換える
  python3 CDO/outputs/note_publisher/body_stats.py --check CMO/outputs/*.md  # 不一致を一覧（0件なら終了0）
"""
import re
import sys
from pathlib import Path

BODY_RE = re.compile(r"##\s*本文.*?\n```\n(.+?)\n```", re.S)
# 「- 文字数: 本文 約 1,152 字」のような行
META_RE = re.compile(r"(- 文字数: 本文 約 )([\d,]+)( 字)")


def extract_body(text: str) -> str | None:
    """publisher / copy_body.py と同一の正規表現で本文を取り出す。"""
    m = BODY_RE.search(text)
    return m.group(1) if m else None


def body_len(text: str) -> int | None:
    """本文の文字数（改行込みの len）。copy_body.py の表示と同じ基準＝これを正本とする。"""
    b = extract_body(text)
    return None if b is None else len(b)


def meta_len(text: str) -> int | None:
    m = META_RE.search(text)
    return int(m.group(2).replace(",", "")) if m else None


def sync(path: Path) -> tuple[int | None, int | None, bool]:
    """メタの字数を実測へ書き換える。(実測, 旧メタ, 変更したか) を返す。"""
    text = path.read_text(encoding="utf-8")
    actual, meta = body_len(text), meta_len(text)
    if actual is None or not META_RE.search(text):
        return actual, meta, False
    new = META_RE.sub(lambda m: f"{m.group(1)}{actual:,}{m.group(3)}", text, count=1)
    if new != text:
        path.write_text(new, encoding="utf-8")
        return actual, meta, True
    return actual, meta, False


def main() -> int:
    args = sys.argv[1:]
    mode = "show"
    if args and args[0] in ("--sync", "--check"):
        mode, args = args[0][2:], args[1:]
    if not args:
        print(__doc__)
        return 2
    bad = 0
    for a in args:
        p = Path(a)
        text = p.read_text(encoding="utf-8")
        actual, meta = body_len(text), meta_len(text)
        if actual is None:
            print(f"  -   本文ブロックなし: {p.name}")
            continue
        if mode == "sync":
            actual, old, changed = sync(p)
            print(f"  {'更新' if changed else '据置'} {p.name}: メタ {old} → 実測 {actual}")
        else:
            ok = (meta == actual)
            if not ok:
                bad += 1
            print(f"  {'OK ' if ok else 'NG '} {p.name}: メタ {meta} / 実測 {actual}")
    if mode == "check":
        print(f"=== 結果: 不一致 {bad} 件 ===")
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
