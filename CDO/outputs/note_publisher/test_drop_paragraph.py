#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""drop_paragraph.verify() を型ごとに試す。

なぜ要るか: この関数が**保存してよいかどうかの唯一の歯止め**で、
code は note に繋げない（A1）ので**ブラウザ側は実機でしか試せない**。
せめて判定だけは、ここで全部の外れ方を試しておく。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import importlib.util

_spec = importlib.util.spec_from_file_location(
    "_dp", str(Path(__file__).resolve().parent / "drop_paragraph.py"))
_dp = importlib.util.module_from_spec(_spec)
# publish_to_note を読み込ませずに verify だけ取り出す
import types
sys.modules.setdefault("publish_to_note", types.ModuleType("publish_to_note"))
sys.modules.setdefault("_note_safety", types.ModuleType("_note_safety"))
_spec.loader.exec_module(_dp)
verify = _dp.verify

HEAD = "彼岸の中日に墓へ行く。これは家によってまるで違う。" * 2
TAIL = "だから、年に何度行くかは家によって違う。" * 2
CRED = "（見出し画像：Higanbana.jpg ／ 撮影 X ／ CC BY-SA 4.0）"

ok = 0
fail = []

def case(name, before, after, target, needle, want_problem):
    global ok
    got = verify(before, after, target, needle)
    hit = bool(got)
    if hit == want_problem:
        ok += 1
    else:
        fail.append((name, got))

# ① 狙いどおり：末尾のクレジット段落だけ消えた → 問題なし
before = HEAD + "\n" + TAIL + "\n" + CRED
after = HEAD + "\n" + TAIL
case("狙いどおり消えた", before, after, CRED, "見出し画像：", False)

# ② 消えていない → 問題あり
case("消えていない", before, before, CRED, "見出し画像：", True)

# ③ 消しすぎた（クレジット＋直前の段落も巻き添え）→ 問題あり
case("消しすぎた", before, HEAD, CRED, "見出し画像：", True)

# ④ 全文が吹き飛んだ → 問題あり
case("全部消えた", before, "", CRED, "見出し画像：", True)

# ⑤ 冒頭が壊れた（先頭が削れた）→ 問題あり
case("冒頭が壊れた", before, HEAD[10:] + "\n" + TAIL, CRED, "見出し画像：", True)

# ⑥ 真ん中の段落を消す（冒頭と末尾は残る）→ 問題なし
MID = "水をかけて、花を挿す。" * 3
before6 = HEAD + "\n" + MID + "\n" + TAIL
after6 = HEAD + "\n" + TAIL
case("真ん中を消す", before6, after6, MID, "水をかけて", False)

# ⑦ 空白・改行の違いだけなら通す（エディタは空段落を畳む）
after7 = HEAD + "\n\n\n" + TAIL + "\n"
case("空行の違いは通す", before, after7, CRED, "見出し画像：", False)

# ⑧ 狙った段落は消えたが、別のところも8字消えた → 問題あり
after8 = (HEAD + "\n" + TAIL)[:-8]
case("余分に8字消えた", before, after8, CRED, "見出し画像：", True)

# ⑨ 段落の取り方が合っておらず、target が元の本文に無い → 問題あり
case("targetが本文に無い", before, HEAD + "\n" + TAIL, "どこにも無い段落", "見出し画像：", True)

# ⑩ **この道具が実際に使われる形**＝本文の末尾のクレジット行を消す。
#    端だけ見る判定だとここで誤判定する（2026-11-14 にこのテストが捕まえた）。
case("末尾の段落を消す(実例)", before, HEAD + "\n" + TAIL, CRED, "見出し画像：", False)

print(f"通った: {ok}/10")
for n, g in fail:
    print(f"  ✗ {n}: {g}")
sys.exit(1 if fail else 0)
