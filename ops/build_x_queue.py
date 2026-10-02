#!/usr/bin/env python3
"""X の投稿キューを素材から作り直す。**各ツイートに note の URL を入れる。**

なぜ必要か（2026-10-02 に数えて分かったこと）:
  ・キューにあった未投稿42本のうち、**note へのリンクが入っているものは0本**だった。
    X に出しても誰も note に来ない＝流入導線として成立していなかった。
  ・素材は `EN/outputs/x_tweets/` に253本あるのに、**キューには43本しか入っていなかった**。
    素材からキューへ流す経路がそもそも無く、新しい記事はいつまでも X に出なかった。

作り:
  ・1記事＝**1ツイート**（素材の「A. Single tweet」＋ note の URL）。
    2ツイートのスレッドにすると、手で投稿するとき返信をつなぐ操作が要る。1本なら貼って出すだけ。
  ・URL は**公開記録から引いた実URL**をそのまま書く。未公開の記事は入れない（リンク切れを作らない）。
  ・**新しい記事から**並べる。古い記事の告知より、いま読めるもののほうが踏まれる。
  ・すでに [POSTED] のスレッドは**そのまま残す**（投稿済みの記録を消さない）。
  ・280字を超えるものは入れない（x_poster が投稿前に落とすので、入れても無駄になる）。

使い方:
  python3 ops/build_x_queue.py          # 何本になるか見るだけ
  python3 ops/build_x_queue.py --go     # ops/x_queue.txt を書き換える
"""
import argparse
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAT = os.path.join(ROOT, "EN/outputs/x_tweets")
ART = os.path.join(ROOT, "CMO/outputs")
REG = os.path.join(ROOT, "CDO/outputs/note_publisher/published_registry.json")
QUEUE = os.path.join(ROOT, "ops/x_queue.txt")
MAXLEN = 280

HEADER = """# X投稿キュー（owner/cowork がX認証を入れて `python3 ops/x_poster.py --go` で先頭1スレッドを投稿）
# 区切り: === slug ===  / その下 1行=1ツイート / 投稿済みは自動で [POSTED] が付く
#
# ★2026-10-02 作り直し（ops/build_x_queue.py）。
#   それまでのキューは **note へのリンクが1本も入っていなかった**（未投稿42本すべて）。
#   X に出しても note に来ないので、流入導線として成立していなかった。
#   いまは **1記事=1ツイート（本文＋note の実URL）**。素材 EN/outputs/x_tweets/ から作る。
#   作り直すとき: python3 ops/build_x_queue.py --go
#   作り直す前のキューは ops/_x_queue_before_rebuild.txt に残してある。
"""


def published_urls():
    out = {}
    for r in json.load(open(REG, encoding="utf-8")):
        if not r.get("unpublished") and r.get("url"):
            out[r["title"]] = r["url"]
    return out


def article_title(stem: str):
    p = os.path.join(ART, stem if stem.endswith(".md") else stem + ".md")
    if not os.path.exists(p):
        return None
    m = re.search(r"##\s*タイトル.*?\n```\n(.+?)\n```", open(p, encoding="utf-8").read(), re.S)
    return m.group(1).strip().splitlines()[0].strip() if m else None


def keep_posted():
    """いまのキューから [POSTED] のスレッドを原文のまま取り出す。"""
    if not os.path.exists(QUEUE):
        return [], set()
    blocks, cur, slugs = [], None, set()
    for line in open(QUEUE, encoding="utf-8"):
        m = re.match(r"^===\s*(.+?)\s*===\s*$", line.strip())
        if m:
            if cur and "[POSTED]" in cur[0]:
                blocks.append(cur)
            cur = [line.rstrip("\n")]
            if "[POSTED]" in m.group(1):
                slugs.add(m.group(1).replace("[POSTED]", "").strip())
        elif cur is not None and line.strip():
            cur.append(line.rstrip("\n"))
    if cur and "[POSTED]" in cur[0]:
        blocks.append(cur)
    return blocks, slugs


_CJK = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")


def _fix_tags(tags: str, art_text: str) -> str:
    """素材のタグをそのまま使わない。**実際に数えたら歪んでいた**（2026-10-02）。

    ・`#JapaneseFood` が 174本中113本に付いていて、**ひまわりの記事にも付いていた**。
      生成側が既定で足しているだけで、記事の中身を見ていない。食でない記事に食のタグを
      付けると、そのタグを追っている人に関係のないものが届く。
    ・`#TWG系` のように**日本語混じりの壊れたタグ**が混ざっていた。英語読者向けの投稿なので外す。
    ・大文字小文字違いの重複（#Japan と #japan）も1つにする。
    """
    cat = re.search(r"-\s*カテゴリ:\s*(.+)", art_text)
    is_food = "食" in (cat.group(1) if cat else "")
    bm = re.search(r"##\s*本文.*?\n```\n(.+?)\n```", art_text, re.S)
    body = bm.group(1) if bm else art_text
    is_toyama = any(w in body for w in ("富山", "高岡", "氷見"))

    out, seen = [], set()
    for t in re.findall(r"#\S+", tags):
        if _CJK.search(t):
            continue
        if not is_food and t.lower() in ("#japanesefood", "#japanfood"):
            continue
        if t.lower() in seen:
            continue
        seen.add(t.lower())
        # 表記ゆれを揃える（#japan と #Japan が混ざっていた）
        out.append({"#japan": "#Japan", "#toyama": "#Toyama",
                    "#japanesefood": "#JapaneseFood"}.get(t.lower(), t))
    if not any(t.lower() == "#japan" for t in out):
        out.insert(0, "#Japan")
    if is_toyama and not any(t.lower() == "#toyama" for t in out):
        out.append("#Toyama")
    return " ".join(out[:4])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--go", action="store_true")
    a = ap.parse_args()

    urls = published_urls()
    posted_blocks, posted_slugs = keep_posted()

    # ★2026-10-02: 素材ファイル（EN/outputs/x_tweets/）が無い記事はキューに乗らなかった。
    #   今日書いた記事（案内記事・案山子）は公開済みなのに X に出ない状態だった。
    #   いまはどの記事も本文に `【English】` を持っているので、**素材が無ければ本文から作る**。
    #   素材より短く切るだけだが、**出ないよりはるかにいい**。
    done_stems = set()

    rows, skipped = [], {"未公開": 0, "記事なし": 0, "長すぎ": 0, "投稿済み": 0}
    for p in sorted(glob.glob(os.path.join(MAT, "*.md")), reverse=True):
        t = open(p, encoding="utf-8").read()
        am = re.search(r"- Article: `(.+?)`", t)
        sm = re.search(r"##\s*A\.\s*Single tweet.*?\n```\n(.+?)\n```", t, re.S)
        if not am or not sm:
            skipped["記事なし"] += 1
            continue
        stem = am.group(1)[:-3] if am.group(1).endswith(".md") else am.group(1)
        title = article_title(stem)
        if not title:
            skipped["記事なし"] += 1
            continue
        url = urls.get(title)
        if not url:
            skipped["未公開"] += 1
            continue
        slug = stem.replace("_note記事_", "_")[:40]
        if slug in posted_slugs:
            skipped["投稿済み"] += 1
            continue
        art_text = open(os.path.join(ART, stem + ".md"), encoding="utf-8").read()
        body = sm.group(1).strip()
        # 素材の末尾にタグ行がある。URL はタグより前に置く（タグが行末だと切れて見えることがある）
        lines = [x for x in body.split("\n") if x.strip()]
        tags = lines[-1] if lines and lines[-1].lstrip().startswith("#") else ""
        text = " ".join(lines[:-1] if tags else lines).strip()
        tags = _fix_tags(tags, art_text)
        tail = f" {url}" + (f" {tags.strip()}" if tags else "")
        budget = MAXLEN - len(tail)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > budget:
            # URL を足すと溢れる分は**文の切れ目で切る**（36本あった。落とすと36本ぶん出せなくなる）。
            cut = text[:budget]
            end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
            if end > budget * 0.5:
                text = cut[:end + 1]
            else:
                sp = cut.rfind(" ")
                text = (cut[:sp] if sp > 0 else cut).rstrip(" ,;:—-") + "…"
        tweet = (text + tail).strip()
        if len(tweet) > MAXLEN:
            skipped["長すぎ"] += 1
            continue
        rows.append((slug, tweet))
        done_stems.add(stem)

    # 素材が無い公開記事を、本文の【English】から補う
    from_body = 0
    for ap in sorted(glob.glob(os.path.join(ART, "*note記事*.md")), reverse=True):
        stem = os.path.basename(ap)[:-3]
        if stem in done_stems:
            continue
        t = open(ap, encoding="utf-8").read()
        title = article_title(stem)
        url = urls.get(title) if title else None
        if not url:
            continue
        slug = stem.replace("_note記事_", "_")[:40]
        if slug in posted_slugs:
            continue
        bm = re.search(r"##\s*本文.*?\n```\n(.+?)\n```", t, re.S)
        if not bm or "【English】" not in bm.group(1):
            continue
        en = bm.group(1).split("【English】", 1)[1]
        # 1行目は英語の見出し。本文の最初のまとまりを使う
        paras = [x.strip() for x in en.split("\n") if x.strip() and "見出し画像" not in x]
        body_en = " ".join(paras[1:]) if len(paras) > 1 else " ".join(paras)
        body_en = re.sub(r"\s+", " ", body_en).strip()
        tail = f" {url} #Japan"
        budget = MAXLEN - len(tail)
        if len(body_en) > budget:
            cut = body_en[:budget]
            end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
            if end > budget * 0.5:
                body_en = cut[:end + 1]
            else:
                sp = cut.rfind(" ")
                body_en = (cut[:sp] if sp > 0 else cut).rstrip(" ,;:—-") + "…"
        tweet = (body_en + tail).strip()
        if len(tweet) > MAXLEN or len(body_en) < 40:
            continue
        rows.append((slug, tweet))
        from_body += 1

    print(f"素材 {len(glob.glob(os.path.join(MAT, '*.md')))}本")
    print(f"  → 素材が無く本文の【English】から作った: {from_body}本")
    print(f"  → キューに入れる        : {len(rows)}本（すべて note の実URL入り）")
    print(f"  → 入れない（未公開）    : {skipped['未公開']}本")
    print(f"  → 入れない（記事なし）  : {skipped['記事なし']}本")
    print(f"  → 入れない（280字超）   : {skipped['長すぎ']}本")
    print(f"  → すでに投稿済み        : {skipped['投稿済み']}本")
    print(f"  残す投稿済みスレッド     : {len(posted_blocks)}本")

    if not a.go:
        print("\n書き換えるには --go を付ける")
        return 0

    with open(QUEUE, "w", encoding="utf-8") as f:
        f.write(HEADER)
        for b in posted_blocks:
            f.write("\n" + "\n".join(b) + "\n")
        for slug, tweet in rows:
            f.write(f"\n=== {slug} ===\n{tweet}\n")
    print(f"\n✅ {QUEUE} を書き換えました")
    return 0


if __name__ == "__main__":
    sys.exit(main())
