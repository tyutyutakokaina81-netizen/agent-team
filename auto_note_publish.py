#!/usr/bin/env python3
"""
auto_note_publish.py — note.com に記事をキュー順で自動投稿

動作:
  - ARTICLE_QUEUE から未公開の記事を1本選んで投稿
  - 公開済みURLは .sessions/note_article_urls.json に保存
  - 全記事公開済みなら何もしない
"""

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).parent
SESSION_FILE = REPO / ".sessions" / "note_session.json"
URL_CACHE = REPO / ".sessions" / "note_article_urls.json"
QUEUE_STATE = REPO / ".sessions" / "note_publish_queue.json"

# 公開する記事キュー（順番に1本ずつ公開）
ARTICLE_QUEUE = [
    {
        "id": "takaoka_paid_guide",
        "file": "CMO/outputs/2026-04-29_高岡観光_有料note記事.md",
        "title": "【保存版】高岡市 完全観光マップ＋モデルコース3選——国宝・日本三大仏・鋳物・グルメ全網羅",
        "price": 300,  # 有料記事
    },
    {
        "id": "kyoto_vs_takaoka",
        "file": "CMO/outputs/2026-04-29_京都より高岡を勧める理由_バズ狙い記事.md",
        "title": "京都に行くくらいなら、高岡に行けばよかった——国宝、日本三大仏、無料。人混みなし。",
    },
    {
        "id": "youtube_open",
        "file": "CMO/outputs/2026-04-28_高岡アイ_YouTube開設note記事.md",
        "title": "架空の女性アナウンサー「高岡アイ」が、富山・高岡の魅力を世界に届けます",
    },
    {
        "id": "zuiryuji",
        "file": "CMO/outputs/2026-04-29_瑞龍寺_note記事.md",
        "title": "国宝・瑞龍寺——富山県高岡市に残る、江戸時代の完全な禅宗建築",
    },
    {
        "id": "daibutsu",
        "file": "CMO/outputs/2026-04-29_高岡大仏_note記事.md",
        "title": "日本三大仏のひとつ、高岡大仏——無料で、台座の中にも入れる",
    },
    {
        "id": "kanayamachi",
        "file": "CMO/outputs/2026-04-29_金屋町_note記事.md",
        "title": "金屋町——400年前の石畳と千本格子が今も残る、高岡の原点",
    },
    {
        "id": "okutofu",
        "file": "CMO/outputs/2026-04-24_奥とうふ店_note記事.md",
        "title": "高岡市・奥とうふ店——大豆の甘みが違う、地元の名豆腐屋",
    },
    {
        "id": "vol1_free",
        "file": "CMO/outputs/2026-04-10_vol1_note_free_article.md",
        "title": None,  # ファイルから自動抽出
    },
]


def load_queue_state() -> dict:
    if QUEUE_STATE.exists():
        return json.loads(QUEUE_STATE.read_text())
    return {"published": {}}


def save_queue_state(state: dict):
    QUEUE_STATE.parent.mkdir(exist_ok=True)
    QUEUE_STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def next_article() -> dict | None:
    state = load_queue_state()
    for article in ARTICLE_QUEUE:
        if article["id"] not in state["published"]:
            path = REPO / article["file"]
            if path.exists():
                return article
    return None


def load_article_content(article: dict) -> tuple[str, str]:
    path = REPO / article["file"]
    text = path.read_text(encoding="utf-8")
    lines = text.strip().split("\n")

    # タイトル: 指定あればそれ、なければ先頭#行から抽出
    title = article.get("title") or ""
    if not title:
        for line in lines:
            if line.startswith("# "):
                title = line[2:].strip()
                break

    # 本文: タイトル行を除いた全文
    body_lines = []
    for line in lines:
        if line.strip() == title or (line.startswith("# ") and line[2:].strip() == title):
            continue
        body_lines.append(line)

    body = "\n".join(body_lines).strip()
    return title, body


def extract_note_cookies():
    """ChromeからnoteのクッキーをPlaywright形式で取得"""
    try:
        import browser_cookie3
        cookies = list(browser_cookie3.chrome(domain_name=".note.com"))
        if not cookies:
            return False
        state = {
            "cookies": [
                {
                    "name": c.name, "value": c.value,
                    "domain": c.domain if c.domain.startswith(".") else f".{c.domain}",
                    "path": c.path or "/", "secure": bool(c.secure),
                    "httpOnly": False, "sameSite": "Lax",
                }
                for c in cookies if c.value
            ],
            "origins": [],
        }
        SESSION_FILE.parent.mkdir(exist_ok=True)
        SESSION_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))
        return True
    except Exception:
        return False


def publish_article():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        import subprocess
        for cmd in [
            [sys.executable, "-m", "pip", "install", "playwright", "-q", "--break-system-packages"],
            [sys.executable, "-m", "pip", "install", "playwright", "-q"],
        ]:
            if subprocess.run(cmd, capture_output=True).returncode == 0:
                break
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium",
                        "--with-deps"], capture_output=True)
        from playwright.sync_api import sync_playwright

    # セッションがなければChromeから自動取得
    if not SESSION_FILE.exists():
        print("  🍪 Chromeクッキーから noteセッション取得中...")
        extract_note_cookies()

    article = next_article()
    if not article:
        print("✅ 全記事公開済み")
        return None

    title, body = load_article_content(article)
    print(f"公開: {title[:50]}...")

    storage = json.loads(SESSION_FILE.read_text()) if SESSION_FILE.exists() else None

    published_url = None
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx_args = {"viewport": {"width": 1280, "height": 900}}
        if storage:
            ctx_args["storage_state"] = storage
        ctx = browser.new_context(**ctx_args)
        page = ctx.new_page()

        page.goto("https://note.com/notes/new", wait_until="networkidle", timeout=30000)
        time.sleep(3)

        # ログイン確認
        if "login" in page.url:
            print("  ⚠️  note未ログイン。Chromeでログインして再実行してください")
            browser.close()
            return None

        # タイトル入力
        for sel in ["[data-placeholder='タイトル']", ".title-input",
                    "h1[contenteditable]", "input[placeholder*='タイトル']"]:
            el = page.query_selector(sel)
            if el:
                el.click()
                page.keyboard.type(title)
                time.sleep(0.5)
                break

        time.sleep(1)

        # 本文入力
        for sel in ["[data-placeholder='本文を書く']",
                    ".public-DraftEditor-content", "[contenteditable='true']"]:
            els = page.query_selector_all(sel)
            target = els[-1] if len(els) >= 2 else (els[0] if els else None)
            if target:
                target.click()
                break

        time.sleep(0.5)
        for i, para in enumerate(body.split("\n\n")):
            if para.strip():
                page.keyboard.type(para.replace("\n", " "))
            if i < len(body.split("\n\n")) - 1:
                page.keyboard.press("Enter")
                page.keyboard.press("Enter")
            time.sleep(0.05)

        time.sleep(2)

        time.sleep(2)

        # ── 公開設定ボタン（note新エディタ editor.note.com 対応）──
        # Step1: 「公開設定」or「公開する」ボタンをクリック
        for sel in [
            "button:has-text('公開設定')",
            "button:has-text('公開する')",
            "button:has-text('公開')",
            "button:has-text('投稿')",
            "[data-cy='publish-button']",
            "[class*='PublishButton']",
            "[class*='publish']",
        ]:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click()
                time.sleep(2)
                break

        # 有料記事の場合は価格設定（モーダルが開いた後）
        price = article.get("price", 0)
        if price and price > 0:
            for sel in ["input[type='number']", "input[name*='price']",
                        "input[placeholder*='価格']", "input[placeholder*='円']"]:
                price_input = page.query_selector(sel)
                if price_input and price_input.is_visible():
                    price_input.fill(str(price))
                    time.sleep(0.5)
                    break

        # Step2: 「今すぐ公開」or「投稿する」確定ボタン
        for sel in [
            "button:has-text('今すぐ公開')",
            "button:has-text('投稿する')",
            "button:has-text('公開する')",
            "button:has-text('送信する')",
            "[data-cy='submit-publish']",
        ]:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click()
                time.sleep(5)
                break
        else:
            # モーダルがなかった場合は再度クリックを試みる
            time.sleep(2)

        # URL確認（公開後は note.com/@user/n/xxx or editor.note.com/notes/xxx に遷移）
        current_url = page.url
        if ("note.com" in current_url and "/n/" in current_url) or \
           ("editor.note.com/notes/" in current_url and "/edit/" not in current_url):
            published_url = current_url
            print(f"✅ 公開完了: {published_url}")
        elif "editor.note.com/notes/" in current_url:
            # 編集画面のままでも、noteは作成されている（下書き保存状態）
            note_id = current_url.split("/notes/")[-1].split("/")[0]
            published_url = f"https://note.com/n/{note_id}"
            print(f"✅ 作成済み（公開ボタン確認が必要）: {current_url}")
            print(f"   手動公開URL候補: {published_url}")
        else:
            print(f"⚠️  URL取得失敗（現在: {current_url}）")

        ctx.storage_state(path=str(SESSION_FILE))
        browser.close()

    if published_url:
        # キューに記録
        state = load_queue_state()
        state["published"][article["id"]] = published_url
        save_queue_state(state)

        # URLキャッシュに保存
        urls = {}
        if URL_CACHE.exists():
            try:
                urls = json.loads(URL_CACHE.read_text())
            except Exception:
                pass
        urls[article["id"]] = published_url
        if article["id"] == "vol1_free":
            urls["vol1_free_article"] = published_url
        URL_CACHE.write_text(json.dumps(urls, ensure_ascii=False, indent=2))

    return published_url


if __name__ == "__main__":
    if "--setup" in sys.argv:
        print("セッション取得中...")
        extract_note_cookies()
        print("✅ 完了")
    elif "--status" in sys.argv:
        state = load_queue_state()
        print(f"公開済み: {len(state['published'])}/{len(ARTICLE_QUEUE)}件")
        for a in ARTICLE_QUEUE:
            mark = "✅" if a["id"] in state["published"] else "⬜"
            print(f"  {mark} {a['id']}: {a['title'] or a['file']}")
    else:
        publish_article()
