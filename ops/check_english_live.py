#!/usr/bin/env python3
"""公開済み記事の note 本文（ログアウトAPI）に、md の英語要約が本当に入っているかを見る。

2026-11-04 作成。english_backfill_done.tsv の UPDATED が、保存修正(b7f77662)より前は
note に保存されていなかった（inbox 2026-10-25_005 ①）。「英文がある」では判定しない＝
フォロー導線の "For English readers" フッターに当たって誤判定する。append_english.py と
同じく**その記事の要約の単語**がライブ本文にあるかで見る。

使い方:
  python3 ops/check_english_live.py <NID> <md>      # 1本。入っていれば exit 0
  python3 ops/check_english_live.py --recheck       # done 台帳の UPDATED/SKIP を全部実測して
                                                     # ops/english_live_recheck.tsv を作り直す
"""
import json, os, re, subprocess, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                                "CDO/outputs/note_publisher"))
from append_english import english_block  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def live_text(nid: str):
    out = subprocess.run(["curl", "-s", "--max-time", "20",
                          f"https://note.com/api/v3/notes/{nid}"],
                         capture_output=True, text=True).stdout
    d = json.loads(out)["data"]
    body = re.sub(r"<[^>]+>", " ", d.get("body") or "")
    return d.get("status"), re.sub(r"\s+", " ", body)


def has_english(nid: str, md: str) -> str:
    blk = english_block(open(md, encoding="utf-8").read())
    if not blk:
        return "NO_MD_ENGLISH"
    st, cur = live_text(nid)
    if st != "published":
        return f"NOT_PUBLISHED:{st}"
    if "【English】" in cur:
        return "LIVE_OK"
    probe = re.findall(r"[A-Za-z]{4,}", blk)[:8]
    if len(probe) >= 5 and sum(1 for w in probe if w in cur) >= len(probe) - 1:
        return "LIVE_OK"
    return "NOT_LIVE"


def md_by_title():
    m = {}
    d = os.path.join(ROOT, "CMO/outputs")
    for f in os.listdir(d):
        if not f.endswith(".md"):
            continue
        t = open(os.path.join(d, f), encoding="utf-8").read()
        tm = re.search(r"##\s*タイトル.*?\n```\n(.+?)\n```", t, re.S)
        if tm:
            m.setdefault(tm.group(1).strip().splitlines()[0].strip(), os.path.join("CMO/outputs", f))
    return m


def recheck() -> int:
    by_t = md_by_title()
    rows = {}
    for l in open(os.path.join(ROOT, "ops/english_backfill_done.tsv"), encoding="utf-8"):
        c = l.rstrip("\n").split("\t")
        if l.startswith("#") or len(c) < 4:
            continue
        rows[c[0]] = c  # 同じ NID は最後の行を使う
    out = []
    for nid, c in rows.items():
        if c[1] not in ("UPDATED", "SKIP"):
            continue
        md = by_t.get(c[3].strip())
        try:
            r = has_english(nid, os.path.join(ROOT, md)) if md else "NO_MD"
        except Exception as e:  # noqa: BLE001
            r = f"ERR:{type(e).__name__}"
        out.append((nid, r, c[1], c[3]))
        time.sleep(0.4)
    with open(os.path.join(ROOT, "ops/english_live_recheck.tsv"), "w", encoding="utf-8") as f:
        f.write("# 英語要約のライブ照合（ログアウトAPI本文に md の要約の単語があるか）"
                + time.strftime("%Y-%m-%d %H:%M") + "\n")
        for o in out:
            f.write("\t".join(o) + "\n")
    from collections import Counter
    print(Counter(o[1].split(":")[0] for o in out))
    return 0


if __name__ == "__main__":
    if "--recheck" in sys.argv:
        sys.exit(recheck())
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    r = has_english(sys.argv[1], sys.argv[2])
    print(r)
    sys.exit(0 if r == "LIVE_OK" else 1)
