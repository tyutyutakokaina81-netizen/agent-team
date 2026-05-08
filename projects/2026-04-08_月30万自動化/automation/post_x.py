"""
post_x.py — X に告知ツイート 3 種を投稿（半自動）

実行方法:
  python3 post_x.py 1     # ツイート 1 のみ
  python3 post_x.py all   # 3 つすべて

永続プロファイル方式（_browser.py）でログイン状態を維持する。
ポストボタン押下は人手（規約遵守）。連続投稿は 30 秒間隔。
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _browser import open_browser  # noqa: E402

# CMO の下書き（CMO/outputs/2026-05-08_x_announcements_vol2_vol3.md より）
TWEETS = [
    """SNSの投稿に毎日悩んでいませんか？

「月初の30分で1ヶ月分の投稿計画が完成する」スプレッドシートを公開しました。

✅ Instagram・X・Facebook 一括管理
✅ 投稿テーマ50選つき（5カテゴリ）
✅ ハッシュタグ雛形・CSV雛形も同梱

¥680 でコピーして使えます。
[note URL を入れてください]

#SNS運用 #フリーランス""",

    """飲食店オーナーさんへ。

「Instagramの文章、毎回考えるのしんどい」を解決するプロンプト集を公開しました。

新メニュー紹介・季節限定・スタッフ紹介・口コミ紹介…
20シーンぶん、ChatGPT/Claudeに貼るだけで30秒で投稿文ができます。

¥1,980（一度買えば何度でも）
[note URL を入れてください]

#飲食店 #SNS集客""",

    """1人で事業を回す人向けに、コピペで使える業務テンプレを順次公開しています。

📊 Vol.1 収支管理スプレッドシート ¥980
📅 Vol.2 SNS投稿カレンダー ¥680
🍽️ Vol.3 飲食店向けプロンプト集 ¥1,980

近日：Vol.4 バンドルパック（悩み別3セット）

note でまとめて見れます👇
[note クリエイターページ URL]""",
]


def post_one(text: str, idx: int):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[ERROR] pip install playwright && playwright install chromium")
        sys.exit(1)

    with sync_playwright() as p:
        ctx = open_browser(p)
        page = ctx.new_page()
        page.goto("https://x.com/compose/post")
        try:
            page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception:
            pass

        print(f"\n[X] ツイート {idx} エディタを開きました")
        print("─" * 50)
        print(text)
        print("─" * 50)

        typed = False
        for sel in [
            "div[role='textbox'][contenteditable='true']",
            "div[data-testid='tweetTextarea_0']",
        ]:
            try:
                el = page.query_selector(sel)
                if el:
                    el.click()
                    page.keyboard.type(text)
                    typed = True
                    break
            except Exception:
                continue

        if not typed:
            print("  ⚠️  入力欄が見つかりません（手動で貼り付けてください）")

        print("\n  ✅ 入力完了。note URL を [ ] 部分に貼り直し、")
        print("     画像があれば添付して、「ポストする」を押してください。")
        print("  Enter を押したらブラウザを閉じます...")
        input()

        ctx.close()


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "all":
        indices = [1, 2, 3]
    elif cmd.isdigit() and 1 <= int(cmd) <= len(TWEETS):
        indices = [int(cmd)]
    else:
        print("使い方: python3 post_x.py {1|2|3|all}")
        sys.exit(1)

    for n, i in enumerate(indices, 1):
        post_one(TWEETS[i - 1], i)
        if n < len(indices):
            print(f"\n  次の投稿まで 30 秒待機します（連投回避）...")
            time.sleep(30)


if __name__ == "__main__":
    main()
