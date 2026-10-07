#!/usr/bin/env python3
"""見出し画像のクレジット行を**読める形に直し、英語要約の前へ移す**。

なぜ（2026-10-07）:
  オーナー「英語表記にエラーが出てる」。公開ページを読んだら、**英文の最後が
  パーセント符号の壁**になっていた——
  `…File:%E5%A4%A7%E9%89%84%E7%A0%B2%E5%A4%A7%E8%B1%86%E3%81%AE%E7%A8%B2%E6%9E%B6%E6%8E%9B%E3%81%91.jpg`。
  Commons の出典URLは日本語ファイル名が符号化されるため。英語で読んでいる人には
  文字化けか不具合に見える。しかも**日本語のクレジットで英文が終わる**形だった。

やること（どちらも表示の問題で、出典の情報は1文字も減らさない）:
  1. 出典URLをパーセント符号から戻す（Wikimedia 側は同じページを開く）
  2. クレジット行を**日本語パートの最後＝英語要約の直前**へ移す

使い方:
  python3 ops/fix_credit_lines.py          # 何が変わるか見るだけ
  python3 ops/fix_credit_lines.py --go     # 書き込む
"""
import glob
import os
import re
import sys
from urllib.parse import unquote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GO = "--go" in sys.argv
SEP = "――――――――――\n【English】"
CREDIT = re.compile(r"（見出し画像：[^（）]*(?:（[^（）]*）[^（）]*)*）")


def readable(u: str) -> str:
    try:
        d = unquote(u)
        return d if d.isprintable() else u
    except Exception:
        return u


def fix_one(path):
    t = open(path, encoding="utf-8").read()
    m = re.search(r"(##\s*本文.*?\n```\n)(.+?)(\n```)", t, re.S)
    if not m:
        return None
    body = m.group(2)
    cm = CREDIT.search(body)
    if not cm:
        return None
    line = cm.group(0)
    # 1) URL を戻す
    new_line = re.sub(r"https?://\S+", lambda x: readable(x.group(0)), line)
    decoded = new_line != line
    # 2) 位置を直す
    rest = body[:cm.start()] + body[cm.end():]
    rest = re.sub(r"\n{3,}", "\n\n", rest).rstrip() + "\n" if rest.endswith("\n") else rest
    moved = False
    if SEP in rest:
        after_sep = body.find(SEP) >= 0 and cm.start() > body.find(SEP)
        if after_sep:
            moved = True
        new_body = rest.replace(SEP, new_line + "\n\n" + SEP, 1)
    else:
        new_body = rest.rstrip() + "\n\n" + new_line
    if not decoded and not moved:
        return None
    return (t[:m.start(2)] + new_body + t[m.end(2):], decoded, moved, new_line)


def main():
    files = sorted(glob.glob(os.path.join(ROOT, "CMO/outputs/*note記事*.md")))
    n_dec = n_mov = 0
    changed = []
    for f in files:
        r = fix_one(f)
        if not r:
            continue
        new_text, decoded, moved, line = r
        n_dec += 1 if decoded else 0
        n_mov += 1 if moved else 0
        changed.append((os.path.basename(f)[:-3], decoded, moved))
        if GO:
            open(f, "w", encoding="utf-8").write(new_text)
    for name, d, mv in changed[:12]:
        tags = []
        if d:
            tags.append("URLを戻した")
        if mv:
            tags.append("英文の前へ移した")
        print(f"  {name[:46]} … {' / '.join(tags)}")
    if len(changed) > 12:
        print(f"  ほか {len(changed) - 12}本")
    print(f"\n対象 {len(files)}本 / 直すもの {len(changed)}本"
          f"（URLを戻す {n_dec} / 位置を移す {n_mov}）")
    if GO:
        print("== 書き込んだ ==")
        print("※ 公開済みの記事は note 側にも反映が要る: bash ops/update_article.sh")
    else:
        print("== DRY: `--go` で書き込む ==")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
