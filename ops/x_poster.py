#!/usr/bin/env python3
"""X（旧Twitter）自動投稿ツール（owner/cowork 側で実行・依存は tweepy のみ）。

★重要な前提
- **code(Claude Code)は A1 で外部ネット不可のため、これを実行しない**。owner/cowork の環境で実行する。
- 認証情報は **環境変数からのみ** 読む（リポジトリに絶対に置かない＝機密4系統ルール）。
    X_API_KEY / X_API_SECRET / X_ACCESS_TOKEN / X_ACCESS_SECRET  （OAuth 1.0a・投稿に必要）
- **¥0原則**：X API の Free tier（書き込み上限あり・2026時点で月間の上限が小さい）で運用する想定。
  上限・料金は変わるので**実行前に公式で要確認**。上限超過や有料化が必要になったら owner 判断。
- **アカウント安全**：1回の実行で**1スレッドのみ**投稿（連投しない）。280字超はエラーで止める。
  投稿間隔は手動運用（cron を短くしない）。凍結リスクを避ける。

## 使い方
  1) スレッドを ops/x_queue.txt に用意（フォーマットは下記／crosspostテンプレからコピペ可）
  2) 確認（投稿しない・既定）:  python3 ops/x_poster.py
  3) 先頭1スレッドを投稿:        X_API_KEY=... X_API_SECRET=... X_ACCESS_TOKEN=... X_ACCESS_SECRET=... \
                                  python3 ops/x_poster.py --go
  4) 投稿済みは ops/logs/x_posted.tsv に記録し、queueの当該スレッドは done 印を付ける

## ops/x_queue.txt フォーマット
  - スレッド区切り: 行頭 `=== <slug> ===`
  - その下に 1行=1ツイート（空行は無視）。番号(1/ 2/ 等)は付けても付けなくてもよい。
  - 投稿済みスレッドは区切り行を `=== <slug> [POSTED] ===` にして二重投稿を防ぐ。
"""
import os, sys, re, argparse, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "ops", "x_queue.txt")
LOG   = os.path.join(ROOT, "ops", "logs", "x_posted.tsv")
MAXLEN = 280

def parse_threads(path):
    if not os.path.exists(path):
        return []
    threads, cur = [], None
    for line in open(path, encoding="utf-8"):
        m = re.match(r"^===\s*(.+?)\s*===\s*$", line.strip())
        if m:
            if cur:
                threads.append(cur)
            label = m.group(1)
            cur = {"label": label, "posted": "[POSTED]" in label, "tweets": []}
            cur["slug"] = label.replace("[POSTED]", "").strip()
        elif cur is not None:
            t = line.strip()
            if t:
                cur["tweets"].append(t)
    if cur:
        threads.append(cur)
    return threads

def validate(threads):
    problems = []
    for th in threads:
        for i, tw in enumerate(th["tweets"], 1):
            if len(tw) > MAXLEN:
                problems.append(f"{th['slug']} tweet#{i}: {len(tw)}字 > {MAXLEN}")
    return problems

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--go", action="store_true", help="実際に投稿（既定はDRY-RUN）")
    ap.add_argument("--queue", default=QUEUE)
    args = ap.parse_args()

    threads = parse_threads(args.queue)
    pending = [t for t in threads if not t["posted"] and t["tweets"]]
    print(f"スレッド総数 {len(threads)} / 未投稿 {len(pending)}")
    probs = validate(pending)
    for p in probs:
        print("  [警告・280字超]", p)

    if not pending:
        print("投稿対象なし。ops/x_queue.txt に `=== slug ===` 形式でスレッドを追加してください。")
        return

    target = pending[0]  # 安全のため1回1スレッドのみ
    print(f"\n--- 次に投稿するスレッド: {target['slug']}（{len(target['tweets'])}ツイート）---")
    for i, tw in enumerate(target["tweets"], 1):
        flag = "  ⚠️超過" if len(tw) > MAXLEN else ""
        print(f"  [{i}] ({len(tw)}字){flag} {tw}")

    if not args.go:
        print("\n[DRY-RUN] 投稿しません。投稿するには認証を環境変数に入れて --go を付けて再実行。")
        return

    if any(len(tw) > MAXLEN for tw in target["tweets"]):
        print("\n✗ 280字超のツイートがあるため中止。文面を分割してください。")
        sys.exit(1)

    creds = {k: os.environ.get(k, "") for k in
             ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")}
    if not all(creds.values()):
        print("\n✗ 認証情報が環境変数に無い（X_API_KEY/X_API_SECRET/X_ACCESS_TOKEN/X_ACCESS_SECRET）。中止。")
        sys.exit(1)

    try:
        import tweepy  # owner/cowork 側で `pip install tweepy`
    except ImportError:
        print("\n✗ tweepy 未インストール。`pip install tweepy` を実行してください。")
        sys.exit(1)

    client = tweepy.Client(consumer_key=creds["X_API_KEY"], consumer_secret=creds["X_API_SECRET"],
                           access_token=creds["X_ACCESS_TOKEN"], access_token_secret=creds["X_ACCESS_SECRET"])
    reply_to, posted_ids = None, []
    for i, tw in enumerate(target["tweets"], 1):
        try:
            resp = client.create_tweet(text=tw, in_reply_to_tweet_id=reply_to)
            tid = resp.data["id"]
            reply_to = tid
            posted_ids.append(tid)
            print(f"  ✅ tweet#{i} posted id={tid}")
        except Exception as e:
            print(f"  ✗ tweet#{i} 失敗: {e}（ここで停止）")
            break

    if posted_ids:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()}\t{target['slug']}\t{','.join(map(str,posted_ids))}\n")
        # queue の当該スレッドを [POSTED] にマーク
        txt = open(args.queue, encoding="utf-8").read()
        txt = txt.replace(f"=== {target['slug']} ===", f"=== {target['slug']} [POSTED] ===", 1)
        open(args.queue, "w", encoding="utf-8").write(txt)
        print(f"\n記録: {LOG} / queueを[POSTED]にマーク。次回は次のスレッドが対象。")

if __name__ == "__main__":
    main()
