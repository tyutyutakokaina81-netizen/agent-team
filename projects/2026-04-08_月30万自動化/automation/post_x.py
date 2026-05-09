"""
post_x.py — X に告知ツイート 3 種を投稿（完全自動）

実行方法:
  python3 post_x.py 1     # ツイート 1 のみ
  python3 post_x.py all   # 3 つすべて

note 公開時に保存された URL を自動的に [note URL を入れてください] へ置換。
ポストボタンも自動クリック（5 秒カウントダウン後・Ctrl+C で中止可能）。
連続投稿は 30 秒間隔。
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _browser import open_browser  # noqa: E402

URL_STORE = Path(__file__).parent / ".published_urls.json"


def _load_urls() -> dict:
    if URL_STORE.exists():
        try:
            return json.loads(URL_STORE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _profile_url(urls: dict) -> str:
    """note クリエイターページ URL を URL ストアの note 記事 URL から推定"""
    for u in urls.values():
        # https://note.com/<creator>/n/<id> から creator ページ URL を作る
        try:
            parts = u.replace("https://", "").replace("http://", "").split("/")
            if len(parts) >= 2 and parts[0] == "note.com":
                return f"https://note.com/{parts[1]}"
        except Exception:
            continue
    return "https://note.com/"


# CMO の下書き
TWEETS_TEMPLATE = [
    """SNSの投稿に毎日悩んでいませんか？

「月初の30分で1ヶ月分の投稿計画が完成する」スプレッドシートを公開しました。

✅ Instagram・X・Facebook 一括管理
✅ 投稿テーマ50選つき(5カテゴリ)
✅ ハッシュタグ雛形・CSV雛形も同梱

¥680 でコピーして使えます。
{vol2_url}

#SNS運用 #フリーランス""",

    """飲食店オーナーさんへ。

「Instagramの文章、毎回考えるのしんどい」を解決するプロンプト集を公開しました。

新メニュー紹介・季節限定・スタッフ紹介・口コミ紹介…
20シーンぶん、ChatGPT/Claudeに貼るだけで30秒で投稿文ができます。

¥1,980(一度買えば何度でも)
{vol3_url}

#飲食店 #SNS集客""",

    """1人で事業を回す人向けに、コピペで使える業務テンプレを順次公開しています。

📊 Vol.1 収支管理スプレッドシート ¥980
📅 Vol.2 SNS投稿カレンダー ¥680
🍽️ Vol.3 飲食店向けプロンプト集 ¥1,980

近日：Vol.4 バンドルパック(悩み別3セット)

note でまとめて見れます👇
{profile_url}""",
]


def _resolve_tweet(idx: int) -> str:
    urls = _load_urls()
    return TWEETS_TEMPLATE[idx - 1].format(
        vol2_url=urls.get("vol2", "[note URL を入れてください]"),
        vol3_url=urls.get("vol3", "[note URL を入れてください]"),
        profile_url=_profile_url(urls),
    )


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

        # 入力欄に自動タイプ
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
            print("  貼り付け＋ポスト後に Enter...")
            input()
            ctx.close()
            return

        time.sleep(1.5)

        # ─── 5 秒カウントダウン後にポストボタンをクリック ───
        print("\n  ⏰ 5 秒後に「ポストする」を自動クリック（Ctrl+C で中止可）")
        for i in range(5, 0, -1):
            print(f"     {i}...", end="\r", flush=True)
            time.sleep(1)
        print("     ポスト実行  ")

        posted = False
        for sel in [
            "[data-testid='tweetButton']",
            "[data-testid='tweetButtonInline']",
            "button:has-text('ポストする')",
            "button:has-text('Post')",
        ]:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible() and btn.is_enabled():
                    btn.click()
                    posted = True
                    print(f"  ✓ ポストボタンをクリック ({sel})")
                    break
            except Exception:
                continue

        if not posted:
            print("  ⚠️  ポストボタンが見つかりません/押せません")
            print("  手動でポストして Enter...")
            input()
        else:
            time.sleep(4)
            print("  ✅ ポスト完了")

        ctx.close()


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "all":
        indices = [1, 2, 3]
    elif cmd.isdigit() and 1 <= int(cmd) <= len(TWEETS_TEMPLATE):
        indices = [int(cmd)]
    else:
        print("使い方: python3 post_x.py {1|2|3|all}")
        sys.exit(1)

    for n, i in enumerate(indices, 1):
        text = _resolve_tweet(i)
        post_one(text, i)
        if n < len(indices):
            print(f"\n  次の投稿まで 30 秒待機します（連投回避）...")
            time.sleep(30)


if __name__ == "__main__":
    main()
