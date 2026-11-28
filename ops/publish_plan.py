#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""**公開する前に、何が出て何が止まるかを先に出す。** 読むだけ（何も変えない・何も投稿しない）。

なぜ要るか（2026-11-26）:
  11-25・11-26 と**2日続けて「公開 0 件 / 失敗 1 件」**になった。
  理由はどちらも同じで、キューに1本だけ入っていた記事が**題材トークン重複ゲート**で
  止まっていた（意図した重複なので `--dup` が要る）。
  ★★**止まることは、キューを見ただけでは分からない。** publisher を動かして初めて分かる。
  しかも **publisher を動かすにはブラウザと note のログインが要る**ので、
  **オーナーの Mac で実行するまで結果が読めない**。
  ★★★**その判定だけを、ネットもブラウザも使わずに先回りして出す**のがこの道具。

  ⚠️**ゲートは一切いじらない。** publisher の `topic_conflict()` を**そのまま借りて**、
  同じ答えを先に表示するだけ。公開の可否を変える力は持たない。

見るもの（publisher が公開時に見るのと同じ順）:
  ① 既に公開済みか（published_registry.json のタイトル一致）
  ② `drafts/published/` に同名があるか（二重公開ガード）
  ③ 題材トークンの重複（`topic_conflict()`＝publisher 本体から借りる）
  ④ 見出し画像（`thumbnails/<stem>.jpg` があり、`_verified.txt` に載っているか）
  ⑤ マガジン指定（`- マガジン:` の行）
  ⑥ ハッシュタグの数（5個未満は reach が落ちる）
  ⑦ 本文の字数（10,000字未満）

出すもの:
  - キューの1本ずつに「出る / 止まる（理由）」
  - **最後に、打つべきコマンドを1行**（`--dup` が要るかどうかまで込み）
  - 在庫のうち「あと写真1枚で出せる」本数

使い方:
  python3 ops/publish_plan.py              # キューを見る
  python3 ops/publish_plan.py --stock      # 在庫（未公開・未投入）も一覧で出す
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, "CDO/outputs/note_publisher")
REG = os.path.join(PUB, "published_registry.json")
THUMBS = os.path.join(PUB, "thumbnails")
VERIFIED = os.path.join(THUMBS, "_verified.txt")
AWAIT = os.path.join(THUMBS, "_await_photo.txt")
QUEUE = os.path.join(ROOT, "drafts/queue")
PUBLISHED = os.path.join(ROOT, "drafts/published")
ARTICLES = os.path.join(ROOT, "CMO/outputs")


def _load_topic_conflict():
    """publisher 本体から `topic_conflict()` だけを借りる。

    ★丸ごと import すると playwright が要る（このコンテナには無い）ので、
      **必要な定義の範囲だけを切り出して実行する**。
      `ops/topic_check.py --title` と同じやり方で、**公開時とまったく同じ判定**になる。
    """
    path = os.path.join(PUB, "publish_to_note.py")
    src = open(path, encoding="utf-8").read()
    from pathlib import Path as _P
    ns = {"re": re, "os": os, "json": json, "Path": _P,
          "unicodedata": unicodedata, "__file__": path}
    for a, b in (("REGISTRY_PATH = ", "def _ensure_"),
                 ("def _norm_title(", "def _slug"),
                 ("def load_registry(", "def save_registry("),
                 ("TOPIC_STOPWORDS = {", "def _publish_one(")):
        if a not in src:
            continue
        i = src.index(a)
        j = src.index(b, i) if b in src[i:] else len(src)
        exec(src[i:j], ns)
    if "topic_conflict" not in ns:
        raise RuntimeError("topic_conflict を取り出せなかった")
    return ns["topic_conflict"]


def _read(path):
    return open(path, encoding="utf-8").read()


def _lines(path):
    if not os.path.exists(path):
        return set()
    return {ln.strip() for ln in _read(path).splitlines()
            if ln.strip() and not ln.strip().startswith("#")}


def parse(path):
    """記事から、公開の可否に関わるところだけ取り出す。"""
    s = _read(path)
    m = re.search(r"##\s*タイトル\s*\n+```\s*\n(.+?)\n```", s, re.S)
    title = m.group(1).strip() if m else ""
    m = re.search(r"##\s*本文\s*\n+```\s*\n(.*?)\n```", s, re.S)
    body = m.group(1) if m else ""
    m = re.search(r"##\s*ハッシュタグ\s*\n+```\s*\n(.*?)\n```", s, re.S)
    tags = re.findall(r"#\S+", m.group(1)) if m else []
    mag = re.search(r"^\s*-\s*マガジン\s*[:：]\s*(.+)$", s, re.M)
    return {
        "title": title,
        "body": body,
        "tags": tags,
        "magazine": mag.group(1).strip() if mag else "",
        "has_english": "【English】" in body,
    }


def judge(path, pubtitles, verified, conflict):
    """1本について、publisher が止めるかどうかを先に出す。"""
    stem = os.path.splitext(os.path.basename(path))[0]
    a = parse(path)
    stop, warn = [], []

    if not a["title"]:
        stop.append("タイトルブロックが読めない（`## タイトル` の ``` が無い）")
    elif a["title"] in pubtitles:
        stop.append("既に公開済み（published_registry.json にタイトルがある）")

    if os.path.exists(os.path.join(PUBLISHED, os.path.basename(path))):
        stop.append("drafts/published に同名がある（二重公開ガードでキューから外される）")

    dup = None
    if a["title"]:
        hit = conflict(a["title"])
        if hit:
            entry, shared = hit
            name = entry.get("title") if isinstance(entry, dict) else str(entry)
            dup = (str(name), sorted(shared))
            stop.append(f"題材トークン重複『{'/'.join(dup[1])}』→ 既公開「{dup[0][:40]}」"
                        f"（`--dup` を付ければ出る）")

    jpg = os.path.join(THUMBS, stem + ".jpg")
    if not os.path.exists(jpg):
        warn.append("見出し画像が無い（note 既定の画像で公開される。"
                    "⚠️ただし**あとから付けられる**＝`bash ops/fix_header_images.sh`。"
                    "2026-11-28 に実測＝`ops/header_image_todo.tsv` の **131本が DONE** になっている。"
                    "付けられないのは『画像が無いとき』であって、『公開したあと』ではない）")
    elif stem not in verified:
        warn.append("画像はあるが `_verified.txt` に無い＝未検品。publisher は使わない")

    if not a["magazine"]:
        warn.append("マガジン指定が無い（どのマガジンにも入らずに公開される）")
    if len(a["tags"]) < 5:
        warn.append(f"タグが {len(a['tags'])} 個（5個未満は発見経路が落ちる）")
    if "#毎日note" not in a["tags"]:
        warn.append("`#毎日note` が無い")
    if len(a["body"]) < 10000:
        warn.append(f"本文 {len(a['body']):,} 字（10,000字未満）")
    if not a["has_english"]:
        warn.append("本文ブロックに【English】が無い＝note 上は日本語だけで公開される")

    return {"stem": stem, "title": a["title"], "stop": stop, "warn": warn, "dup": dup}


def main() -> int:
    conflict = _load_topic_conflict()
    reg = json.load(open(REG, encoding="utf-8")) if os.path.exists(REG) else []
    pubtitles = {e.get("title", "") for e in reg if isinstance(e, dict)}
    verified = _lines(VERIFIED)

    files = sorted(glob.glob(os.path.join(QUEUE, "*.md")))
    print("=" * 72)
    print(f"公開の下見（読むだけ・何も変えません）  キュー {len(files)} 本")
    print("=" * 72)

    if not files:
        print("\nキューが空です。公開できるものはありません。")
    results = []
    for f in files:
        r = judge(f, pubtitles, verified, conflict)
        results.append(r)
        print(f"\n── {r['stem']}")
        print(f"   題名: {r['title']}")
        if r["stop"]:
            print("   ✗ 止まる:")
            for x in r["stop"]:
                print(f"      - {x}")
        else:
            print("   ✓ 出ます")
        for x in r["warn"]:
            print(f"   ⚠ {x}")

    goes = [r for r in results if not r["stop"]]
    dups = [r for r in results if r["dup"] and len(r["stop"]) == 1]
    hard = [r for r in results if r["stop"] and not (r["dup"] and len(r["stop"]) == 1)]

    print("\n" + "-" * 72)
    print(f"そのまま出る: {len(goes)} 本 / `--dup` を付ければ出る: {len(dups)} 本 / "
          f"直さないと出ない: {len(hard)} 本")

    print("\n【打つコマンド（オーナーの Mac）】")
    if not files:
        print("   （キューが空なので、打っても『公開対象がありません』になります）")
    elif dups:
        print("   cd ~/agent-team-run && git pull && bash ops/publish_today.sh --dup")
        print("   ※ `--dup` が要るのは次の記事です。**意図した重複かどうかを必ず確かめてから**打つこと:")
        for r in dups:
            print(f"      - {r['stem']}")
            print(f"        共有トークン『{'/'.join(r['dup'][1])}』／既公開「{r['dup'][0][:50]}」")
        print("   ⚠️ `--dup` は**その便の全記事**に効きます。キューに他の記事がある日は、")
        print("      その記事の重複ゲートも一緒に外れることを承知のうえで打ってください。")
    else:
        print("   cd ~/agent-team-run && git pull && bash ops/publish_today.sh")

    # 在庫＝未公開で、まだキューに入れていないもの
    #
    # ⚠️★★**直近30日ぶんだけ数える。** `ops/check_requirements.py` の **R21 と同じ窓**に揃えた。
    #   揃える理由: **それより古い記事は、公開済みかどうかをタイトル照合で判定できない。**
    #   8月までは**公開のときに note 側で題名を直していた**ので、
    #   md の `## タイトル` と台帳のタイトルが一致しない。照合すると「未公開」に見えてしまう。
    #   実測（2026-11-26）: 窓を外すと **181本**と出るが、うち **150本は5〜8月の公開済み**だった。
    #   ★**数え方を間違えた数字を出すくらいなら、窓を切って「ここまでしか見ていない」と言うほうがいい。**
    import datetime
    cut = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
    pubd = {os.path.splitext(f)[0] for f in os.listdir(PUBLISHED)} if os.path.isdir(PUBLISHED) else set()
    qstems = {r["stem"] for r in results}
    awaiting = _lines(AWAIT)
    stock, one_photo = [], []
    for p in sorted(glob.glob(os.path.join(ARTICLES, "*note記事*.md"))):
        stem = os.path.splitext(os.path.basename(p))[0]
        if stem[:10] < cut or stem in pubd or stem in qstems:
            continue
        a = parse(p)
        if not a["title"] or a["title"] in pubtitles:
            continue
        stock.append(stem)
        if stem not in verified:
            one_photo.append(stem)

    print("\n【在庫】")
    print(f"   未公開でキューに入っていない記事: {len(stock)} 本"
          f"（直近30日＝{cut} 以降。R21 と同じ窓。"
          f"それより古いものは題名が変わっていて公開済みか判定できない）")
    print(f"   うち見出し画像が未確定: {len(one_photo)} 本"
          f"（{len(awaiting & set(stock))} 本は `ops/photo_requests.md` に撮り方を書いてあります）")
    if "--stock" in sys.argv:
        for s in stock:
            mark = "写真待ち" if s in awaiting else ("画像なし" if s in one_photo else "画像あり")
            print(f"      [{mark}] {s}")
    print("\n   ★ 写真が1枚届くごとに1本出せます: bash ops/use_my_photo.sh <写真> <記事名の一部>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
