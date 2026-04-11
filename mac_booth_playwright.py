#!/usr/bin/env python3
"""
mac_booth_playwright.py — Playwright で BOOTH に自動出品
既存のセッションクッキーを使い、ブラウザを操作して出品する
"""
import asyncio
import json
import sys
from pathlib import Path

SESSION_FILE = Path(__file__).parent / ".sessions" / "booth_session.json"
DIST_DIR = Path(__file__).parent / "projects/2026-04-08_月30万自動化/C_テンプレ販売/dist"

PRODUCTS = [
    {
        "title": "フリーランス収支管理スプレッドシート【Googleスプレッドシート・確定申告対応】",
        "description": "フリーランスの収入・経費・案件を1枚で管理できるスプレッドシートテンプレートです。\n\n【含まれるもの】\n・Excel ファイル（.xlsx）※Googleスプレッドシートでもそのまま使えます\n・4シート構成：収入 / 経費 / 案件管理 / 年間サマリー\n\n【できること】\n✅ 収入を入力すると月別・年間サマリーを自動生成\n✅ 案件ごとの実質時給を自動計算\n✅ 経費を科目別（通信費・交通費等）に自動集計\n✅ 確定申告の準備資料として活用できる\n\n【返金について】\nデジタルコンテンツの性質上、返金はお受けできません。",
        "price": "980",
        "tags": "フリーランス,スプレッドシート,確定申告,収支管理,テンプレート",
        "file": DIST_DIR / "vol1_freelance_cashflow.xlsx",
    },
    {
        "title": "SNS投稿カレンダー【投稿テーマ50選付き・Googleスプレッドシート対応】",
        "description": "Instagram・X・Facebookを一括管理できる月次カレンダーです。\n\n【含まれるもの】\n・Excel ファイル（.xlsx）※Googleスプレッドシート対応\n・2シート構成：月次カレンダー / 投稿テーマ50選\n\n【できること】\n✅ 月別カレンダーで投稿予定を管理\n✅ 複数SNSを一覧管理（Instagram/X/Facebook/TikTok）\n✅ 投稿テーマ50選でネタ切れ知らず\n\n【返金について】\nデジタルコンテンツの性質上、返金はお受けできません。",
        "price": "680",
        "tags": "SNS,Instagram,投稿管理,カレンダー,スプレッドシート",
        "file": DIST_DIR / "vol2_sns_calendar.xlsx",
    },
    {
        "title": "飲食店オーナー向けAIプロンプト集20選【ChatGPT・Claude対応｜SNS投稿文が30秒で完成】",
        "description": "飲食店のSNS投稿に特化したAIプロンプトを20個収録したテキストファイルです。\n\n【収録プロンプト20選】\n新メニュー紹介 / 季節限定メニュー / スタッフ紹介 / お客様の声 / 食材こだわり紹介\n営業時間のお知らせ / イベント告知 / テイクアウト告知 / ランチ紹介 / 周年記念 など\n\n【使い方】\nChatGPT・Claude・Gemini 全てに使えます。[ ] の部分を書き換えて貼るだけ。\n\n【返金について】\nデジタルコンテンツの性質上、返金はお受けできません。",
        "price": "1980",
        "tags": "飲食店,ChatGPT,AIプロンプト,SNS,Instagram,集客",
        "file": Path(__file__).parent / "projects/2026-04-08_月30万自動化/C_テンプレ販売/vol3_restaurant_prompts.txt",
    },
    {
        "title": "【3点セット32%OFF】フリーランス独立スターターパック｜収支管理+SNSカレンダー+プロンプト集",
        "description": "Vol.1〜3の3点セットです。単品合計¥3,660 → ¥2,480（32%OFF）\n\n【セット内容】\n1. フリーランス収支管理スプレッドシート（単品¥980）\n2. SNS投稿カレンダー（単品¥680）\n3. 飲食店向けAIプロンプト集20選（単品¥1,980）\n\n一度購入すれば永久に使い回せます。\n\n【返金について】\nデジタルコンテンツの性質上、返金はお受けできません。",
        "price": "2480",
        "tags": "フリーランス,副業,セット,テンプレート,AIプロンプト",
        "file": DIST_DIR / "vol1_freelance_cashflow.xlsx",
    },
]


def load_cookies():
    if not SESSION_FILE.exists():
        print("❌ セッションファイルなし。mac_auto_cookie.py を先に実行してください")
        sys.exit(1)
    data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    cookie_str = data.get("cookie", "")
    cookies = []
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            cookies.append({
                "name": k.strip(),
                "value": v.strip(),
                "domain": ".booth.pm",
                "path": "/",
            })
    return cookies


async def publish_all():
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        import subprocess
        print("Playwright をインストール中...")
        subprocess.run([sys.executable, "-m", "pip", "install", "playwright",
                       "--break-system-packages", "-q"], check=False)
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=False)
        from playwright.async_api import async_playwright

    cookies = load_cookies()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context()
        await ctx.add_cookies(cookies)

        page = await ctx.new_page()

        # BOOTHにアクセスして確認
        await page.goto("https://manage.booth.pm/items", wait_until="networkidle", timeout=30000)

        # ログインチェック
        if "sign_in" in page.url or "login" in page.url:
            print("❌ セッション無効。mac_auto_cookie.py を再実行してください")
            await browser.close()
            return

        print(f"✅ ログイン確認: {page.url}")

        # 「新しい商品を作る」ボタンを探す
        new_item_url = None
        for selector in [
            "a[href*='/items/new']",
            "a:has-text('新しい商品')",
            "a:has-text('商品を追加')",
            "a:has-text('Add item')",
            ".new-item",
        ]:
            el = page.locator(selector).first
            if await el.count() > 0:
                href = await el.get_attribute("href")
                if href:
                    new_item_url = href if href.startswith("http") else f"https://manage.booth.pm{href}"
                    print(f"  新規作成URL: {new_item_url}")
                    break

        if not new_item_url:
            # ページのリンクを全部表示して確認
            links = await page.eval_on_selector_all("a[href*='item']", "els => els.map(e => e.href)")
            print("  見つかったitemリンク:")
            for l in links[:10]:
                print(f"    {l}")
            await browser.close()
            return

        success = 0
        for i, product in enumerate(PRODUCTS, 1):
            print(f"\n[{i}/{len(PRODUCTS)}] {product['title'][:40]}...")

            await page.goto(new_item_url, wait_until="networkidle", timeout=30000)

            try:
                # 商品名
                await page.fill("input[name*='name'], input[placeholder*='商品名']", product["title"])

                # 説明文
                await page.fill(
                    "textarea[name*='description'], textarea[placeholder*='説明']",
                    product["description"]
                )

                # 価格
                await page.fill("input[name*='price'], input[placeholder*='価格']", product["price"])

                # ファイルアップロード
                file_path = product.get("file")
                if file_path and Path(file_path).exists():
                    file_input = page.locator("input[type='file']").first
                    if await file_input.count() > 0:
                        await file_input.set_input_files(str(file_path))

                # 公開設定（on_sale）
                for sel in [
                    "input[value='on_sale']",
                    "label:has-text('公開')",
                    "select[name*='status'] option[value='on_sale']",
                ]:
                    el = page.locator(sel).first
                    if await el.count() > 0:
                        await el.click()
                        break

                # 保存ボタン
                for sel in [
                    "button[type='submit']",
                    "input[type='submit']",
                    "button:has-text('保存')",
                    "button:has-text('出品')",
                ]:
                    btn = page.locator(sel).first
                    if await btn.count() > 0:
                        await btn.click()
                        await page.wait_for_load_state("networkidle", timeout=15000)
                        break

                if "items/new" not in page.url:
                    print(f"  ✅ 出品完了: {page.url}")
                    success += 1
                else:
                    print(f"  ⚠️  要確認: {page.url}")

            except Exception as e:
                print(f"  ❌ エラー: {e}")

        await browser.close()

    print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  完了: {success}/{len(PRODUCTS)} 件")
    print(f"  確認: https://manage.booth.pm/items")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  BOOTH 自動出品（Playwright版）")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    asyncio.run(publish_all())
