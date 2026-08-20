#!/usr/bin/env python3
"""publisher の出力から note の公開URLを1つだけ取り出し、妥当性を検証して返す。

  cat out.txt | python3 ops/_note_url.py

正しく取れたときだけ URL を1行出力し、終了コード0。取れなければ何も出さずに1。

なぜ検証まで持つか：2026-08-21のテストで、公開に失敗した出力に含まれる
`https://note.com/notes/`（IDが空）を「URLが取れた」と誤認し、その壊れたリンクを
記事本文に埋めて公開しようとした。URLらしき文字列と、実際に開けるURLは別物なので、
ID部分の長さまで見て初めて「取れた」と判定する。
"""
import json, pathlib, re, sys

MIN_ID = 6  # note のキーは十数文字。数文字しか取れていないのは抽出ミス。
CANON = re.compile(r"https://note\.com/([A-Za-z0-9_-]+)/n/(n[0-9a-zA-Z]{%d,})" % MIN_ID)
NOTES = re.compile(r"https://(?:editor\.)?note\.com/notes/(n[0-9a-zA-Z]{%d,})" % MIN_ID)


def author_from_registry() -> str | None:
    p = pathlib.Path(__file__).resolve().parent.parent / "CDO/outputs/note_publisher/published_registry.json"
    try:
        for e in json.loads(p.read_text(encoding="utf-8")):
            m = CANON.search(e.get("url", "") or "")
            if m:
                return m.group(1)
    except Exception:
        pass
    return None


def extract(text: str) -> str | None:
    m = CANON.search(text)
    if m:
        return f"https://note.com/{m.group(1)}/n/{m.group(2)}"
    # 編集画面のURLしか出ていない場合は、著者IDを台帳から補って正規の形に組み直す
    m = NOTES.search(text)
    if m:
        author = author_from_registry()
        if author:
            return f"https://note.com/{author}/n/{m.group(1)}"
    return None


if __name__ == "__main__":
    url = extract(sys.stdin.read())
    if not url:
        sys.exit(1)
    print(url)
