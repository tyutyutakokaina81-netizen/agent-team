#!/usr/bin/env python3
"""
auto_note_publish.py — note.com に記事を自動投稿

前提:
  pip install playwright && playwright install chromium
  初回: python3 auto_note_publish.py --setup  でセッション保存
"""

import json
import sys
import time
from pathlib import Path

SESSION_FILE = Path(__file__).parent / ".sessions" / "note_session.json"
ARTICLE_FILE = Path(__file__).parent / "CMO/outputs/2026-04-10_vol1_note_free_article.md"
URL_CACHE = Path(__file__).parent / ".sessions" / "note_article_urls.json"

# 記事の本文（タイトルと本文を分けて抽出）
def load_article():
    text = ARTICLE_FILE.read_text(encoding="utf-8")
    # タイトル抽出: ``` の中の最初のテキスト
    lines = text.split("\n")
    title = ""
    body_lines = []
    in_body = False
    code_count = 0

    for line in lines:
        if "## タイトル" in line:
            continue
        if "## 本文" in line:
            in_body = True
            continue
        if in_body:
            if line.strip() == "```":
                code_count += 1
                if code_count == 2:
                    break
                continue
            if code_count == 1:
                body_lines.append(line)
        elif "```" in line and not title:
            continue
        elif not title and not in_body:
            # タイトルブロック内
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and not stripped.startswith(">") and not stripped == "```":
                title = stripped

    body = "\n".join(body_lines).strip()
    return title, body


def setup_session():
    """初回ログイン: ブラウザを開いてユーザーが手動ログイン → セッション保存"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("pip install playwright && playwright install chromium")
        sys.exit(1)

    SESSION_FILE.parent.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto("https://note.com/login")
        print("ブラウザでnote.comにログインしてください。")
        print("ログイン完了後、Enterを押してください...")
        input()
        ctx.storage_state(path=str(SESSION_FILE))
        browser.close()
    print(f"✅ セッション保存: {SESSION_FILE}")


def publish_article():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("pip install playwright && playwright install chromium")
        sys.exit(1)

    if not SESSION_FILE.exists():
        print("❌ セッションなし → python3 auto_note_publish.py --setup を先に実行")
        sys.exit(1)

    title, body = load_article()
    if not title or not body:
        print("❌ 記事の読み込み失敗")
        sys.exit(1)

    print(f"タイトル: {title[:50]}...")
    storage = json.loads(SESSION_FILE.read_text(encoding="utf-8"))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=100)
        ctx = browser.new_context(storage_state=storage, viewport={"width": 1280, "height": 900})
        page = ctx.new_page()

        # 新規記事作成
        print("note.com を開いています...")
        page.goto("https://note.com/notes/new", wait_until="networkidle", timeout=30000)
        time.sleep(3)

        # タイトル入力
        for sel in ["[data-placeholder='タイトル']", ".title-input", "h1[contenteditable]", "input[placeholder*='タイトル']"]:
            el = page.query_selector(sel)
            if el:
                el.click()
                page.keyboard.type(title)
                time.sleep(0.5)
                break

        # 本文エリアをクリックしてフォーカス
        time.sleep(1)
        for sel in ["[data-placeholder='本文を書く']", ".public-DraftEditor-content", "[contenteditable='true']"]:
            els = page.query_selector_all(sel)
            if len(els) >= 2:
                els[-1].click()
                break
            elif els:
                els[0].click()
                break

        time.sleep(0.5)

        # 本文を段落ごとに入力（contenteditable対応）
        paragraphs = body.split("\n\n")
        for i, para in enumerate(paragraphs):
            if para.strip():
                page.keyboard.type(para.replace("\n", " "))
            if i < len(paragraphs) - 1:
                page.keyboard.press("Enter")
                page.keyboard.press("Enter")
            time.sleep(0.1)

        time.sleep(2)

        # 公開ボタン
        published_url = None
        for sel in ["button:has-text('公開')", "button:has-text('投稿')", ".publish-button"]:
            btn = page.query_selector(sel)
            if btn:
                btn.click()
                time.sleep(2)
                break

        # 公開確認ダイアログ
        for sel in ["button:has-text('公開する')", "button:has-text('今すぐ公開')", "button:has-text('投稿する')"]:
            btn = page.query_selector(sel)
            if btn:
                btn.click()
                time.sleep(4)
                break

        # URL取得
        current_url = page.url
        if "note.com" in current_url and "/n/" in current_url:
            published_url = current_url
            print(f"✅ 公開完了: {published_url}")

            # URL保存
            URL_CACHE.parent.mkdir(exist_ok=True)
            urls = {}
            if URL_CACHE.exists():
                urls = json.loads(URL_CACHE.read_text())
            urls["vol1_free_article"] = published_url
            URL_CACHE.write_text(json.dumps(urls, ensure_ascii=False, indent=2))
        else:
            print(f"⚠️  URL取得失敗。現在のURL: {current_url}")
            print("   手動で公開してURLをコピーしてください")

        ctx.storage_state(path=str(SESSION_FILE))
        browser.close()

    return published_url


if __name__ == "__main__":
    if "--setup" in sys.argv:
        setup_session()
    else:
        publish_article()
