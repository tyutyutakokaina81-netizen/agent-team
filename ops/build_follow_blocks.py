#!/usr/bin/env python3
"""各記事に付ける「フォロー導線＋あわせて読む3本」を作る。

なぜ（2026-10-02 に数えて分かったこと）:
  公開210本のうち **他記事へのリンクがあるのは10本(4%)／フォローの一言があるのは7本(3%)**。
  ほとんどの記事が行き止まりで、読んだ人が次へ行く道も、フォローする理由も無い。
  フッターを作る仕組み（CDO/outputs/note_footer/gen_footers.py）は 2026-06-07 からあるのに
  **一度も記事に適用されていなかった**。マガジン196本・英語141本と同じ型＝作って終わっていた。

作り:
  ・「あわせて読む」は **タグの重なり**で選ぶ（同じ題材圏の記事に送る）。同日・自分自身は除く。
  ・CTA はカテゴリ別に複数持ってローテーションする（同じ文が並ぶとテンプレに見える＝A5）。
  ・公開済みの記事だけを対象にする（リンク切れを作らない）。

出力: ops/follow_blocks.tsv （NID <TAB> stem <TAB> 本文に足すブロック）
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join(ROOT, "CDO/outputs/note_publisher/published_registry.json")
OUT = os.path.join(ROOT, "ops/follow_blocks.tsv")

CTA = {
    "食": [
        "富山の台所で毎日起きていることを書いています。よければフォローしてください。",
        "住んでいる町の食べものの話を、一日ずつ書き足しています。気に入ったらフォローを。",
        "次はどの食べものにするか決めていません。フォローしておくと、そのうち届きます。",
    ],
    "暮らし": [
        "この土地のふつうの暮らしを、一日ずつ書いています。よければフォローしてください。",
        "名所ではなく、毎日見ているものの話を書いています。気に入ったらフォローを。",
        "同じ調子で続けるので、こういう話が好きならフォローしておいてください。",
    ],
    "風景": [
        "高岡・富山の、観光案内に載らない景色を書き続けています。よければフォローを。",
        "住んでいる人の目線で、この土地の風景を書いています。気に入ったらフォローしてください。",
        "次の季節のことも書きます。フォローしておくと届きます。",
    ],
    "その他": [
        "富山から、ふつうのものの話を毎日書いています。よければフォローしてください。",
        "名所ではなく、毎日見ているもののことを書いています。気に入ったらフォローを。",
        "同じ調子で続けます。こういう話が好きならフォローしておいてください。",
    ],
}


def kind_of(cat: str) -> str:
    """カテゴリ名から CTA の種類を決める。

    ★2026-10-07: **「非食」が「食」に一致していた**（`"食" in cat`）。
      28本の記事がカテゴリに「非食」と書いており、全部「食」として扱われていた。
      風除室（玄関の話）に『富山の台所で毎日起きていることを書いています』が付いて気づいた。
      **中身に合わない CTA は、それ自体がテンプレ**（A5）なので、先に打ち消し語を外す。
    """
    c = (cat or "").replace("非食", "")
    return ("食" if "食" in c else
            "風景" if any(w in c for w in ("風景", "気象", "自然")) else
            "暮らし" if any(w in c for w in ("暮らし", "住まい")) else "その他")


def load_articles():
    reg = json.load(open(REG, encoding="utf-8"))
    urls, out = {}, []
    for r in reg:
        if not r.get("unpublished") and r.get("url"):
            urls[r["title"]] = r["url"]
    for p in sorted(glob.glob(os.path.join(ROOT, "CMO/outputs/*note記事*.md"))):
        t = open(p, encoding="utf-8").read()
        tm = re.search(r"##\s*タイトル.*?\n```\n(.+?)\n```", t, re.S)
        bm = re.search(r"##\s*本文.*?\n```\n(.+?)\n```", t, re.S)
        if not tm or not bm:
            continue
        title = tm.group(1).strip().splitlines()[0].strip()
        url = urls.get(title)
        if not url:
            continue
        gm = re.search(r"##\s*ハッシュタグ.*?\n```\n(.+?)\n```", t, re.S)
        tags = {x.lstrip("#").lower() for x in re.findall(r"#\S+", gm.group(1))} if gm else set()
        cm = re.search(r"-\s*カテゴリ:\s*(.+)", t)
        kind = kind_of(cm.group(1) if cm else "")
        out.append({"path": p, "stem": os.path.basename(p)[:-3], "title": title,
                    "url": url, "tags": tags, "kind": kind,
                    "nid": re.search(r"/n/(n[0-9a-f]+)", url).group(1),
                    "date": os.path.basename(p)[:10], "body": bm.group(1)})
    return out


GENERIC = {"japan", "toyama", "高岡", "富山", "暮らし", "日本の日常", "note200本"}


# 「あわせて読む」に出さないもの＝売り物と総合ガイド。読み物の流れを切るため。
_NOSHOW = ("【", "保存版", "¥", "完璧ガイド", "モデルコース", "まるごと一冊")


def _month(d):
    try:
        return int(d[5:7])
    except Exception:
        return 0


def related(a, arts, n=3):
    """タグの重なりで選び、**季節の近さ**を足して並べる。

    2026-10-02 実測: タグの重なりだけだと、鱒寿司の記事に『ガラス美術館』が並んだ。
    初期の記事はタグが大まかで、重なりが1個しかないと題材が離れたものに当たる。
    同じ時期の記事は季節のものが揃っていて、読んだ流れで次に行きやすい。
    """
    am = _month(a["date"])
    scored = []
    for b in arts:
        if b["nid"] == a["nid"] or b["date"] == a["date"]:
            continue
        if any(x in b["title"] for x in _NOSHOW):
            continue
        share = (a["tags"] & b["tags"]) - GENERIC
        if not share:
            continue
        bm = _month(b["date"])
        gap = min(abs(am - bm), 12 - abs(am - bm)) if am and bm else 6
        score = len(share) * 10 + max(0, 6 - gap)
        scored.append((score, b))
    scored.sort(key=lambda x: -x[0])
    return [b for _, b in scored[:n]]


def main():
    arts = load_articles()
    rows, skipped = [], 0
    for i, a in enumerate(arts):
        if "あわせて読む" in a["body"]:
            skipped += 1
            continue
        rel = related(a, arts)
        if len(rel) < 2:
            skipped += 1
            continue
        cta = CTA[a["kind"]][i % len(CTA[a["kind"]])]
        lines = ["――――――――――", cta, "", "あわせて読む"]
        for b in rel:
            lines.append(f"・{b['title']}")
            lines.append(b["url"])
        rows.append((a["nid"], a["stem"], "\n".join(lines)))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("# NID\tstem\tブロック（\\n は改行）\n")
        for nid, stem, blk in rows:
            one = blk.replace("\n", "\\n")
            f.write(nid + "\t" + stem + "\t" + one + "\n")
    print(f"公開記事 {len(arts)}本")
    print(f"  ブロックを作った : {len(rows)}本 → {os.path.relpath(OUT, ROOT)}")
    print(f"  作らなかった     : {skipped}本（すでにある／似た記事が2本未満）")
    if rows:
        print("\n--- 例 ---")
        print(rows[0][2])
    return 0


if __name__ == "__main__":
    sys.exit(main())
