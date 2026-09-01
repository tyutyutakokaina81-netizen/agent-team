#!/usr/bin/env python3
"""note コメント自動返信の「仕分け」ヘルパー（依存ゼロ）。

役割：pending.tsv の新着コメントを replies.tsv と突き合わせ（dedup）、
危険なものを自動で HOLD 分類し、安全なものは status=DRAFT にして
「code が個別に返信文を書く対象」を出す。返信文の生成は code(LLM) が担当。

使い方：
  python3 ops/draft_comment_replies.py            # 仕分けプレビュー（書き込まない）
  python3 ops/draft_comment_replies.py --write     # replies.tsv へ新規行を追記(DRAFT/HOLD*)
  ↑ --write 後、code が DRAFT 行の reply_text を書いて status=READY に更新 → cowork が投稿。
"""
import os, sys, csv, re, argparse, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PENDING = os.path.join(ROOT, "ops", "comments", "pending.tsv")
REPLIES = os.path.join(ROOT, "ops", "comments", "replies.tsv")

SPAM = ("http://", "https://", "www.", "ビットコイン", "投資", "副業", "稼げ", "follow me", "check my", "無料プレゼント", "DM")
CRITICISM = ("最低", "つまらない", "嘘", "うそ", "間違", "がっかり", "ひどい", "不快", "炎上", "disappointing", "wrong", "boring", "hate", "terrible")
SENSITIVE = ("政治", "宗教", "選挙", "戦争", "religion", "politic")
# 事実確認が要りそうな疑問（確証なく断定するとA5違反）→ 慎重に HOLD-uncertain 候補
UNCERTAIN_Q = ("何時", "料金", "いくら", "予約", "営業", "定休", "アクセス", "住所", "電話", "how much", "what time", "open", "reservation", "address")

def detect_lang(t):
    if re.search(r"[぀-ゟ゠-ヿ一-鿿]", t):  # かな/カナ/漢字
        return "ja"
    if re.search(r"[A-Za-z]", t):
        return "en"
    return "other"

def classify(text, lang):
    low = text.lower()
    if any(s.lower() in low for s in SPAM):
        return "HOLD-spam"
    if any(c.lower() in low for c in CRITICISM):
        return "HOLD-criticism"
    if any(s.lower() in low for s in SENSITIVE):
        return "HOLD-sensitive"
    if lang == "other":
        return "HOLD-nonJP-nonEN"
    if ("?" in text or "？" in text) and any(q.lower() in low for q in UNCERTAIN_Q):
        return "HOLD-uncertain"
    return "DRAFT"   # 安全＝code が個別に返信文を書く

def read_tsv(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    pending = read_tsv(PENDING)
    replies = read_tsv(REPLIES)
    done_ids = {r["comment_id"] for r in replies if r.get("comment_id")}

    new = [c for c in pending if c.get("comment_id") and c["comment_id"] not in done_ids]
    if not new:
        print("新着コメントなし（pending.tsv に未処理行がない／全て replies.tsv 済）。")
        return

    rows = []
    counts = {}
    for c in new:
        lang = c.get("lang") or detect_lang(c.get("text", ""))
        st = classify(c.get("text", ""), lang)
        counts[st] = counts.get(st, 0) + 1
        rows.append({"comment_id": c["comment_id"], "article": c.get("article", ""),
                     "lang": lang, "status": st, "reply_text": "",
                     "posted_url": "", "updated_at": datetime.datetime.now().isoformat(timespec="seconds")})

    print(f"新着 {len(new)} 件 → 仕分け: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    for r, c in zip(rows, new):
        print(f"  [{r['status']:<16}] {r['comment_id']} ({r['lang']}) {c.get('text','')[:50]}")
    draft_n = sum(1 for r in rows if r["status"] == "DRAFT")
    print(f"\n→ DRAFT {draft_n} 件は code が個別に reply_text を書いて READY に。HOLD* は owner 確認へ。")

    if not args.write:
        print("[プレビュー] 書き込みなし。反映するには --write。")
        return

    exists = os.path.exists(REPLIES) and os.path.getsize(REPLIES) > 0
    with open(REPLIES, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, delimiter="\t",
                           fieldnames=["comment_id", "article", "lang", "status", "reply_text", "posted_url", "updated_at"])
        if not exists:
            w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"[書込] {REPLIES} に {len(rows)} 行追記。")

if __name__ == "__main__":
    main()
