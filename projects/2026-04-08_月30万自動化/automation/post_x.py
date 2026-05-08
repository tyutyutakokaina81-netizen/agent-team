"""
post_x.py — X に告知ツイート 3 種を投稿（半自動）

実行方法:
  python3 post_x.py 1     # ツイート 1 のみ
  python3 post_x.py all   # 3 つすべて

注: X は自動投稿に対する規約が厳しい。本スクリプトは
「人間がブラウザを見ながら最終ボタンを押す半自動」運用。
連続投稿は時間を空ける（スクリプト内で 30 秒待機）。
"""

import json
import sys
import time
from pathlib import Path

SESSION_FILE = Path(__file__).parent / ".sessions" / "x_session.json"

# CMO の下書き（CMO/outputs/2026-05-08_x_announcements_vol2_vol3.md より）
TWEETS = [
    # 1: Vol.2 公開当日朝
    """SNSの投稿に毎日悩んでいませんか？

「月初の30分で1ヶ月分の投稿計画が完成する」スプレッドシートを公開しました。

✅ Instagram・X・Facebook 一括管理
✅ 投稿テーマ50選つき（5カテゴリ）
✅ ハッシュタグ雛形・CSV雛形も同梱

¥680 でコピーして使えます。
[note URL を入れてください]

#SNS運用 #フリーランス""",

    # 2: Vol.3 公開翌朝
    """飲食店オーナーさんへ。

「Instagramの文章、毎回考えるのしんどい」を解決するプロンプト集を公開しました。

新メニュー紹介・季節限定・スタッフ紹介・口コミ紹介…
20シーンぶん、ChatGPT/Claudeに貼るだけで30秒で投稿文ができます。

¥1,980（一度買えば何度でも）
[note URL を入れてください]

#飲食店 #SNS集客""",

    # 3: シリーズ告知（公開3日目）
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

    if not SESSION_FILE.exists():
        print(f"[ERROR] セッション未保存: {SESSION_FILE}")
        print("  python3 00_session_setup.py x を先に実行してください")
        sys.exit(1)

    storage = json.loads(SESSION_FILE.read_text(encoding="utf-8"))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=80)
        context = browser.new_context(
            storage_state=storage,
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()
        page.goto("https://x.com/compose/post")
        try:
            page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception:
            pass

        print(f"\n[X] ツイート {idx} エディタを開きました")
        print("─" * 50)
        print(text)
        print("─" * 50)

        # 投稿入力欄に本文をタイプ
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

        # セッション更新
        storage = context.storage_state()
        SESSION_FILE.write_text(
            json.dumps(storage, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        browser.close()


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "all":
        indices = [1, 2, 3]
    elif cmd.isdigit() and 1 <= int(cmd) <= len(TWEETS):
        indices = [int(cmd)]
    else:
        print("使い方: python3 post_x.py {1|2|3|all}")
        sys.exit(1)

    for i in indices:
        post_one(TWEETS[i - 1], i)
        if len(indices) > 1 and i < len(indices):
            print(f"\n  次の投稿まで 30 秒待機します（連投回避）...")
            time.sleep(30)


if __name__ == "__main__":
    main()
