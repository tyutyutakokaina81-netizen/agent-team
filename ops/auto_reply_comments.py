#!/usr/bin/env python3
"""コメントへの返信文を**機械的に組み立てる**（LLM を待たずに自動で進む）。

なぜ（2026-10-07）:
  自動返信は以前からの要件なのに、実際には「code(LLM) が1件ずつ書く」設計で止まっていた。
  つまり**人（または Claude）が見るまで1件も返信されない**＝自動ではない。
  しかも**投稿するスクリプトがそもそも存在しなかった**ので、READY にしても出ていかなかった。
  ここを埋める。

設計（A5＝テンプレ禁止を構造で守る）:
  - **相手の言葉を必ず1つ引き取る**。コメント本文から名詞句を1つ取り出して返信に入れる。
    取り出せない短すぎるコメントは READY にしない（中身を見ていない返信を出さない）。
  - **記事の題材を入れる**。どの記事への返信かが文面から分かるようにする。
  - **書き出しを回す**。同じ日に同じ書き出しが並ばないよう、comment_id から決める。
  - **安全でない型は自動で出さない**＝質問・批判・指摘・機微・スパムは HOLD。
    質問に機械で答えると、確かめていないことを書くことになる（A1/A5）。
  - 英語のコメントには英語で返す。

使い方:
  python3 ops/auto_reply_comments.py          # 下書きを作って見せるだけ
  python3 ops/auto_reply_comments.py --go     # ops/comments/replies.tsv に書く
"""
import csv
import datetime
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PENDING = os.path.join(ROOT, "ops/comments/pending.tsv")
REPLIES = os.path.join(ROOT, "ops/comments/replies.tsv")
REG = os.path.join(ROOT, "CDO/outputs/note_publisher/published_registry.json")
GO = "--go" in sys.argv
# 1回に自動で出す上限。**残りは人（か Claude）が中身を読んで書く**。
#   機械の返信は「礼」止まりなので、数を出すほど薄さが並ぶ。
MAX_AUTO = 3

# 自動で返さないもの。ここは**広めに取る**（迷ったら人に回す）。
HOLD = {
    "spam": ("http://", "https://", "www.", "ビットコイン", "投資", "副業", "稼げ",
             "follow me", "check my", "無料プレゼント", "DM", "相互フォロー"),
    "criticism": ("最低", "つまらない", "嘘", "うそ", "間違", "違います", "がっかり", "ひどい",
                  "不快", "誤り", "wrong", "boring", "hate", "terrible", "incorrect"),
    "sensitive": ("政治", "宗教", "選挙", "戦争", "religion", "politic", "差別"),
    "question": ("ですか", "ますか", "でしょうか", "教えて", "どこで", "いくら", "何円",
                 "?", "？", "how ", "where ", "what ", "why ", "which ", "can i", "do you"),
}

JA_OPEN = [
    "読んでくださってありがとうございます。",
    "コメントありがとうございます。",
    "ありがとうございます。",
]
EN_OPEN = [
    "Thank you for reading.",
    "Thanks for the comment.",
    "Thank you — glad it reached you.",
]
JA_CLOSE = [
    "地元だと当たり前すぎて誰も説明しないので、ありがたいです。",
    "同じ調子で続けるので、よければまた覗いてみてください。",
    "ふつうのものばかり書いています。",
]
EN_CLOSE = [
    "Nobody here explains these things, because everyone grew up with them.",
    "I write one of these most days, mostly about ordinary things in Takaoka.",
    "It is all very ordinary material, which is the point.",
]

# 「褒め言葉」は引き取る語にしない。相手が何に反応したかを示さないため。
PRAISE = {"fascinating", "interesting", "amazing", "wonderful", "lovely", "beautiful",
          "great", "awesome", "excellent", "おもしろい", "面白い", "素敵", "素晴らしい"}

# 相手が「自分の土地・家ではこうだ」と言っている型。返す言葉が変わる。
OWN_PLACE = ("うちの方", "うちでは", "こちらでは", "地元では", "私の", "実家",
             "where i", "in my", "we have", "we call", "over here", "my family")


def _is_own_place(text: str) -> bool:
    low = (text or "").lower()
    return any(w in low or w in (text or "") for w in OWN_PLACE)


def load_registry_titles():
    try:
        reg = json.load(open(REG, encoding="utf-8"))
    except Exception:
        return {}
    out = {}
    for r in reg:
        m = re.search(r"/n/(n[0-9a-f]{12})", r.get("url", "") or "")
        if m:
            out[m.group(1)] = (r.get("title") or "").strip()
    return out


def classify(text: str) -> str:
    low = (text or "").lower()
    for kind, words in HOLD.items():
        for w in words:
            if w in low or w in (text or ""):
                return "HOLD-" + kind
    return "OK"


def pick_phrase(text: str, subject: str = "") -> str | None:
    """相手の言葉から、返信に引き取る語を1つ取る。取れなければ None。

    **ここが None のものは返信しない**＝中身を見ていない返信を出さないための歯止め。
    ★2026-10-07: 最初の版は「Fascinating」のような**褒め言葉**を拾い、
      題材と同じ語（消雪パイプの記事に「消雪パイプ」）も拾って、同じ語が2回出る文になった。
      褒め言葉と題材そのものは除く。
    """
    t = re.sub(r"\s+", " ", text or "").strip()
    if len(t) < 8:
        return None
    cands = re.findall(r"[一-龥ァ-ヶー]{2,10}", t)
    stop = {"this", "that", "very", "really", "thank", "thanks", "about", "from",
            "with", "your", "have", "been", "were", "what", "would", "could"}
    cands += [w for w in re.findall(r"[A-Za-z]{4,12}", t) if w.lower() not in stop]
    bad = {"ありがとう", "コメント", "記事", "note"}
    out = []
    for c in cands:
        if c in bad or c.lower() in PRAISE:
            continue
        if subject and (c in subject or subject in c):
            continue
        out.append(c)
    return max(out, key=len) if out else None


def short_subject(title: str) -> str:
    """記事タイトルから題材だけを取る（『：』『— 』の前後で切る）。"""
    t = re.split(r"[：:—]", title or "", 1)[0].strip()
    return t[:24] if t else ""


# ★2026-10-07（2度目の作り直し）:
#   「相手の言葉を1つ拾って返信に入れる」方式を**捨てた**。実際に動かしたら
#   消雪パイプの記事に「『富山』のところに触れてもらえるとは」、
#   ginkgo の記事に「"collect" is the part I would not have expected」と出た。
#   **personal に見えて中身が無い**＝テンプレより悪い。しかも機械は「どこに驚いたか」を知らない。
#   機械が本当に書けるのは「読んでくれたことへの礼」と「土地で違うと知った驚き」だけなので、
#   そこに留める。**短くする**（長い返信は中身の無さが目立つ）。
#   同じ文が並ぶのは comment_id で回して避け、さらに**1日3件まで**に絞る（下の MAX_AUTO）。
JA_THANKS = [
    "読んでくださってありがとうございます。地元だと当たり前すぎて誰も説明しないので、こういう反応はありがたいです。",
    "ありがとうございます。ふつうのものばかり書いているので、届いていると知れてうれしいです。",
    "コメントありがとうございます。毎日こんな調子で書いています。よければまた覗いてみてください。",
]
JA_OWNPLACE = [
    "土地によって違うんですね。知りませんでした、ありがとうございます。",
    "そちらではそうなんですね。同じものに別のやり方があるのは、書いていてよく出てきます。",
    "教えていただいてありがとうございます。自分の家のことしか知らないので、助かります。",
]
EN_THANKS = [
    "Thank you for reading. Nobody here explains these things, because everyone grew up with them — so it is good to hear it read as new.",
    "Thanks very much. I write one of these most days, mostly about ordinary things in Takaoka.",
    "Thank you. It is all very ordinary material, which is rather the point.",
]
EN_OWNPLACE = [
    "Interesting that it works differently where you are. Thank you for telling me.",
    "Good to know — I only really know how my own household does it.",
    "That is a difference I did not know about. Thanks for adding it.",
]


def build(lang: str, phrase: str, subject: str, seed: int, own_place: bool) -> str:
    """返信文を組み立てる。**書けることだけ書く。**"""
    if lang == "en":
        pool = EN_OWNPLACE if own_place else EN_THANKS
    else:
        pool = JA_OWNPLACE if own_place else JA_THANKS
    return pool[seed % len(pool)]


def load_done():
    done = set()
    if os.path.exists(REPLIES):
        with open(REPLIES, encoding="utf-8") as fh:
            for r in csv.reader(fh, delimiter="\t"):
                if r and not r[0].startswith("comment_id"):
                    done.add(r[0])
    return done


def main():
    if not os.path.exists(PENDING):
        print("pending.tsv が無い。先に `bash ops/comments_now.sh`")
        return 0
    titles = load_registry_titles()
    done = load_done()
    now = datetime.datetime.now().isoformat(timespec="seconds")
    rows, skipped = [], []
    with open(PENDING, encoding="utf-8") as fh:
        for r in csv.reader(fh, delimiter="\t"):
            if not r or r[0].startswith("comment_id") or r[0] in done:
                continue
            cid, art = r[0], (r[1] if len(r) > 1 else "")
            lang = r[3] if len(r) > 3 else "ja"
            text = r[4] if len(r) > 4 else ""
            kind = classify(text)
            nid = (re.search(r"/n/(n[0-9a-f]{12})", art) or [None, ""])[1] if "/n/n" in art else ""
            subject = short_subject(titles.get(nid, ""))
            if kind != "OK":
                rows.append([cid, art, lang, kind, "", "", now])
                skipped.append((cid, kind, text[:40]))
                continue
            if len(re.sub(r"\\s+", "", text or "")) < 6:
                rows.append([cid, art, lang, "HOLD-tooshort", "", "", now])
                skipped.append((cid, "HOLD-tooshort", text[:40]))
                continue
            if sum(1 for r in rows if r[3] == "READY") >= MAX_AUTO:
                rows.append([cid, art, lang, "HOLD-overflow", "", "", now])
                skipped.append((cid, "HOLD-overflow", text[:40]))
                continue
            phrase = ""
            seed = int(hashlib.md5(cid.encode()).hexdigest()[:6], 16)
            reply = build(lang, phrase, subject, seed, _is_own_place(text))
            rows.append([cid, art, lang, "READY", reply, "", now])
            print(f"READY [{lang}] {subject or '記事不明'}")
            print(f"   相手: {text[:50]}")
            print(f"   返信: {reply}")
    for cid, kind, t in skipped:
        print(f"{kind:<16} 自動では返さない: {t}")
    if not rows:
        print("新しく返すものは無い")
        return 0
    if not GO:
        print(f"\nDRY: {len(rows)}件。`--go` で replies.tsv に書く")
        return 0
    head = not os.path.exists(REPLIES) or os.path.getsize(REPLIES) == 0
    with open(REPLIES, "a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        if head:
            w.writerow(["comment_id", "article", "lang", "status", "reply_text", "posted_url", "updated_at"])
        w.writerows(rows)
    ready = sum(1 for r in rows if r[3] == "READY")
    print(f"\n書いた: READY {ready}件 / 保留 {len(rows) - ready}件 → {REPLIES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
