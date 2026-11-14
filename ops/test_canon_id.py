#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""draft_comment_replies.canon_id() を試す。

なぜ要るか（2026-11-14）: 同じコメントが `nXXXX` / `api_nXXXX` / `ntf_<別ハッシュ>` の
3通りの id で入ってきて、突合が素通りしていた。実害＝**POSTED 済みのコメントが
READY で再登録され、読者に二重返信する**ところだった（replies.tsv で実際に発生）。
この関数が突合の唯一の要なので、形ごとに試しておく。
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from draft_comment_replies import canon_id

BASE = "https://note.com/safe_canna441/n/n28531e463029"
NOTICE = BASE + "?from=notice&scrollpos=comment&c=nc6efb9aa5a1b2"

cases = [
    ("素のid はそのまま",        "nc3ff48a1f708f", BASE,   "nc3ff48a1f708f"),
    ("api_ は接頭辞を外す",      "api_nc3ff48a1f708f", BASE, "nc3ff48a1f708f"),
    ("ntf_ は URL の c= を使う", "ntf_bc52dc6064b77d2a", NOTICE, "nc6efb9aa5a1b2"),
    ("ntf_ で c= が無ければ素に戻せない＝そのまま（別物扱いのほうが安全）",
                                 "ntf_bc52dc6064b77d2a", BASE, "ntf_bc52dc6064b77d2a"),
    ("api_ と ntf_ は同じ値に畳まれる(1)", "api_nc6efb9aa5a1b2", BASE, "nc6efb9aa5a1b2"),
    ("api_ と ntf_ は同じ値に畳まれる(2)", "ntf_bc52dc6064b77d2a", NOTICE, "nc6efb9aa5a1b2"),
    ("空でも落ちない",            "", BASE, ""),
    ("URL が空でも落ちない",      "api_nXYZ", "", "nXYZ"),
]
fail = []
for name, cid, url, want in cases:
    got = canon_id(cid, url)
    if got != want:
        fail.append((name, cid, got, want))
print(f"通った: {len(cases)-len(fail)}/{len(cases)}")
for n, c, g, w in fail:
    print(f"  ✗ {n}: canon_id({c!r}) → {g!r} / 期待 {w!r}")
sys.exit(1 if fail else 0)
