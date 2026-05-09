"""
post_x.py — X に告知ツイートを投稿（属性ベースの寛容なセレクタ）

実行方法:
  python3 post_x.py 1 | 2 | 3 | all
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _browser import open_browser  # noqa: E402

URL_STORE = Path(__file__).parent / ".published_urls.json"
DEBUG_DIR = Path(__file__).parent / "_debug"
DEBUG_DIR.mkdir(exist_ok=True)


def _load_urls() -> dict:
    if URL_STORE.exists():
        try:
            return json.loads(URL_STORE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _profile_url(urls: dict) -> str:
    for u in urls.values():
        try:
            parts = u.replace("https://", "").replace("http://", "").split("/")
            if len(parts) >= 2 and parts[0] == "note.com":
                return f"https://note.com/{parts[1]}"
        except Exception:
            continue
    return "https://note.com/"


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


def _find_text_input(page) -> object | None:
    """X のツイート入力欄を寛容に探す"""
    candidates = [
        "div[role='textbox'][contenteditable='true']",
        "div[data-testid='tweetTextarea_0']",
        "div[aria-label*='ポスト']",
        "div[aria-label*='Post']",
        "div[aria-label*='ツイート']",
    ]
    for sel in candidates:
        try:
            els = page.query_selector_all(sel)
            for el in els:
                if el.is_visible():
                    return el
        except Exception:
            continue
    # 最終手段：すべての contenteditable を探して最初の visible
    try:
        for el in page.query_selector_all("[contenteditable='true']"):
            if el.is_visible():
                return el
    except Exception:
        pass
    return None


def _click_post_button(page) -> str | None:
    """X のポストボタンを寛容に探してクリック"""
    candidates_attr = [
        "[data-testid='tweetButton']",
        "[data-testid='tweetButtonInline']",
        "button[data-testid*='Button']",
    ]
    for sel in candidates_attr:
        try:
            for el in page.query_selector_all(sel):
                if el.is_visible() and el.is_enabled():
                    el.click()
                    return f"{sel}"
        except Exception:
            continue
    # テキストでも探す
    for sel in ["button", "[role='button']"]:
        try:
            for el in page.query_selector_all(sel):
                if not el.is_visible() or not el.is_enabled():
                    continue
                txt = (el.inner_text() or "").strip()
                if txt in ("ポストする", "ポスト", "Post", "投稿する"):
                    el.click()
                    return f"{sel} [{txt}]"
        except Exception:
            continue
    return None


def post_one(text: str, idx: int):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[ERROR] pip install playwright && playwright install chromium")
        sys.exit(1)

    with sync_playwright() as p:
        ctx = open_browser(p)
        page = ctx.new_page()
        page.goto("https://x.com/compose/post", timeout=30000)
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

        print(f"\n[X] ツイート {idx}")
        print(f"     URL: {page.url}")
        print(f"     title: {page.title()}")

        # 入力欄を探す（最大 30 秒）
        input_el = None
        for _ in range(15):
            input_el = _find_text_input(page)
            if input_el:
                break
            time.sleep(2)

        try:
            page.screenshot(path=str(DEBUG_DIR / f"x_{idx}_pre.png"))
        except Exception:
            pass

        if not input_el:
            print("  ⚠️  入力欄が見つかりません。ブラウザで手動投稿してから Enter...")
            input()
            ctx.close()
            return

        try:
            input_el.click()
            page.keyboard.type(text)
            print(f"  ✓ 本文入力（{len(text)} 文字）")
        except Exception as e:
            print(f"  ⚠️  入力失敗: {e}")
            input("  手動入力後 Enter...")
            ctx.close()
            return

        time.sleep(2)
        try:
            page.screenshot(path=str(DEBUG_DIR / f"x_{idx}_typed.png"))
        except Exception:
            pass

        # 5 秒カウントダウン
        print("\n  ⏰ 5 秒後に「ポストする」を自動クリック（Ctrl+C で中止可）")
        for i in range(5, 0, -1):
            print(f"     {i}...", end="\r", flush=True)
            time.sleep(1)
        print("     ポスト実行  ")

        result = _click_post_button(page)
        if not result:
            print("  ⚠️  ポストボタンが見つかりません。")
            print(f"     ブラウザで「ポストする」を押してから Enter...")
            try:
                page.screenshot(path=str(DEBUG_DIR / f"x_{idx}_no_button.png"))
            except Exception:
                pass
            input()
        else:
            print(f"  ✓ クリック → {result}")
            time.sleep(4)

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
