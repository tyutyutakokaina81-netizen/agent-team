#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cw_fetch.py — CrowdWorks 公開案件をターミナルから取得する（zero-dep）。
  ※ owner のローカルマシン（ネット可）で実行する想定。code container は A1 で外部不可。
使い方:
  python3 tools/cw_fetch.py "AI ライティング"
  python3 tools/cw_fetch.py "英語 翻訳" --max 20
出力: 新着案件のタイトル＋URL（タイトルが拾えた範囲）。
取得できない場合（ログイン必須/JS描画）はブラウザ版を使う旨を表示。
"""
import sys, re, html, urllib.request, urllib.parse

DEFAULT_KW = "AI ライティング"

def fetch(keyword: str):
    q = urllib.parse.urlencode({"order": "new", "search[keywords]": keyword})
    url = "https://crowdworks.jp/public/jobs/search?" + q
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Safari/537.36",
        "Accept-Language": "ja,en;q=0.8",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read().decode("utf-8", "ignore"), url
    except Exception as e:
        return None, f"{url}  ({e})"

def parse(body: str):
    seen = {}
    # /public/jobs/<id> へのリンクとアンカーテキストを抽出
    for m in re.finditer(r'href="(/public/jobs/(\d+))"[^>]*>(.*?)</a>', body, re.S):
        jid, text = m.group(2), m.group(3)
        text = re.sub(r"<[^>]+>", "", text)
        text = html.unescape(text).strip()
        if text and jid not in seen and len(text) > 4:
            seen[jid] = text
    return seen

def main():
    args = [a for a in sys.argv[1:]]
    mx = 15
    if "--max" in args:
        i = args.index("--max")
        try:
            mx = int(args[i + 1]); del args[i:i + 2]
        except Exception:
            del args[i:i + 1]
    kw = args[0] if args else DEFAULT_KW

    print(f"\n===== CrowdWorks 新着: 「{kw}」 =====")
    body, info = fetch(kw)
    if not body:
        print("取得失敗（ログイン必須 or 通信制限の可能性）。")
        print("→ ブラウザで開いてください: " + info)
        return
    jobs = parse(body)
    if not jobs:
        print("案件が拾えませんでした（JS描画/ログイン必須の可能性）。")
        print("→ ブラウザ版を使ってください: " + info)
        return
    for i, (jid, title) in enumerate(list(jobs.items())[:mx], 1):
        print(f"{i:2}. {title}")
        print(f"    https://crowdworks.jp/public/jobs/{jid}")
    print(f"\n気になる番号のURLを開いて、タイトル/説明/予算/納期を貼ってください。")

if __name__ == "__main__":
    main()
