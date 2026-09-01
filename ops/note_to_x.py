#!/usr/bin/env python3
"""note公開 → 対応するXスレッドを自動投稿する連動（owner/cowork側で実行）。

★前提
- **code は外部投稿不可(A1)**。これは cowork/owner の環境（note公開デーモンの直後）で実行する。
- 認証は環境変数のみ（X_API_KEY/X_API_SECRET/X_ACCESS_TOKEN/X_ACCESS_SECRET）。リポジトリに置かない。
- **¥0**＝X API Free tier前提（月間上限あり）。**アカウント安全**＝1呼び出し=1記事=1スレッドのみ、280字超は中止。

## 使い方（note公開デーモンが公開できた記事ごとに1回呼ぶ）
  python3 ops/note_to_x.py --article "<公開したmdの basename>" [--note-url "<note記事URL>"]     # DRY-RUN
  python3 ops/note_to_x.py --article "..." --note-url "https://note.com/.../n/nXXXX" --go        # 投稿

やること：
  1) 記事名 → Xスレッド slug（KEY_MAP）に対応づけ、ops/x_queue.txt の未投稿スレッドを取り出す。
  2) --note-url があれば最終ツイートに追記（280字以内なら結合、超えるなら単独の最終ツイート）。
  3) --go でXへ投稿（返信チェーン）。投稿後 x_queue を [POSTED] に更新し ops/logs/x_posted.tsv に記録。
  4) 対応スレッドが無い/投稿済みなら skip（＝二重投稿しない）。
"""
import os, sys, re, argparse, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "ops", "x_queue.txt")
LOG   = os.path.join(ROOT, "ops", "logs", "x_posted.tsv")
MAXLEN = 280

# 記事名の部分一致 → x_queue の slug（具体語を先に）
KEY_MAP = [
    ("彼岸花", "higanbana"), ("曼珠沙華", "higanbana"),
    ("コスモス", "cosmos"), ("秋桜", "cosmos"),
    ("水道水", "tap-water"),
    ("新米", "new-rice"),
    ("二百十日", "nihyakutoka"),
    ("田んぼ", "rice-fields-thread"), ("稲", "rice-fields-thread"),
    ("コロッケ", "croquette-thread"),
    ("氷見", "himi-thread"),
    ("高岡", "takaoka-thread"),
    ("2日", "two-day-thread"), ("完璧ガイド", "two-day-thread"),
    ("8月", "august-thread"),
]

def slug_for(article):
    for key, slug in KEY_MAP:
        if key in article:
            return slug
    return None

def parse_threads(text):
    threads, cur = [], None
    for line in text.split("\n"):
        m = re.match(r"^===\s*(.+?)\s*===\s*$", line.strip())
        if m:
            if cur: threads.append(cur)
            label = m.group(1)
            cur = {"label": label, "slug": label.replace("[POSTED]", "").strip(),
                   "posted": "[POSTED]" in label, "tweets": []}
        elif cur is not None and line.strip():
            cur["tweets"].append(line.strip())
    if cur: threads.append(cur)
    return threads

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--article", required=True, help="公開したmdのbasename（例 2026-09-01_note記事_彼岸花_...md）")
    ap.add_argument("--note-url", default="")
    ap.add_argument("--go", action="store_true")
    args = ap.parse_args()

    slug = slug_for(args.article)
    if not slug:
        print(f"skip: 記事名から対応slugを特定できず → {args.article}（KEY_MAPに追加が必要）")
        return
    text = open(QUEUE, encoding="utf-8").read()
    threads = {t["slug"]: t for t in parse_threads(text)}
    th = threads.get(slug)
    if not th:
        print(f"skip: x_queue に slug='{slug}' のスレッドが無い（記事のXスレッドを x_queue.txt に追加してください）")
        return
    if th["posted"]:
        print(f"skip: slug='{slug}' は既に[POSTED]（二重投稿しない）")
        return

    tweets = list(th["tweets"])
    if args.note_url:
        if tweets and len(tweets[-1] + " " + args.note_url) <= MAXLEN:
            tweets[-1] = tweets[-1] + " " + args.note_url
        else:
            tweets.append(args.note_url)

    print(f"記事 '{args.article}' → slug='{slug}'（{len(tweets)}ツイート）")
    for i, tw in enumerate(tweets, 1):
        flag = "  ⚠️280超" if len(tw) > MAXLEN else ""
        print(f"  [{i}] ({len(tw)}字){flag} {tw}")

    if any(len(tw) > MAXLEN for tw in tweets):
        print("✗ 280字超のツイートあり → 中止（文面を分割）。")
        sys.exit(1)
    if not args.go:
        print("[DRY-RUN] 投稿しません。--go と認証で投稿。")
        return

    creds = {k: os.environ.get(k, "") for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")}
    if not all(creds.values()):
        print("✗ 認証情報が環境変数に無い（X_API_KEY/SECRET/ACCESS_TOKEN/SECRET）→ 中止。")
        sys.exit(1)
    try:
        import tweepy
    except ImportError:
        print("✗ tweepy 未インストール（pip install tweepy）→ 中止。")
        sys.exit(1)

    client = tweepy.Client(consumer_key=creds["X_API_KEY"], consumer_secret=creds["X_API_SECRET"],
                           access_token=creds["X_ACCESS_TOKEN"], access_token_secret=creds["X_ACCESS_SECRET"])
    reply_to, posted = None, []
    for i, tw in enumerate(tweets, 1):
        try:
            resp = client.create_tweet(text=tw, in_reply_to_tweet_id=reply_to)
            reply_to = resp.data["id"]; posted.append(reply_to)
            print(f"  ✅ #{i} id={reply_to}")
        except Exception as e:
            print(f"  ✗ #{i} 失敗: {e}（停止）"); break
    if posted:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat(timespec='seconds')}\t{slug}\t{args.article}\t{','.join(map(str,posted))}\n")
        open(QUEUE, "w", encoding="utf-8").write(
            text.replace(f"=== {slug} ===", f"=== {slug} [POSTED] ===", 1))
        print(f"記録: {LOG} / x_queue を[POSTED]に。")

if __name__ == "__main__":
    main()
