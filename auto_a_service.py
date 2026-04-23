#!/usr/bin/env python3
"""
auto_a_service.py — CW/Lancers にSEOライティングサービスを自動出品

前提:
  pip install playwright && playwright install chromium
  .sessions/crowdworks_session.json が存在すること
"""

import json
import time
import sys
from pathlib import Path

PIPELINE_DIR = Path(__file__).parent / "projects/2026-04-08_月30万自動化/D_エクセル入力スクレイピング"
SESSION_FILE = PIPELINE_DIR / ".sessions" / "crowdworks_session.json"

SERVICE = {
    "title": "【SEO記事】キーワード選定〜納品まで一括対応｜月20本実績・上位表示特化ライター",
    "description": """━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ こんな方におすすめ
━━━━━━━━━━━━━━━━━━━━━━━━━━
・ブログ・メディアのSEO記事を外注したい
・キーワード選定から任せたい
・文字数に対してコスパの良いライターを探している
・アフィリエイトサイトの記事を大量発注したい

━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 対応できる記事ジャンル
━━━━━━━━━━━━━━━━━━━━━━━━━━
・副業・フリーランス・転職
・Webマーケティング・SEO・SNS
・お金・節約・投資（入門〜中級）
・ライフスタイル・健康・美容
・ITツール・SaaS・AI活用

━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 納品物に含まれるもの
━━━━━━━━━━━━━━━━━━━━━━━━━━
・本文（指定文字数）
・タイトル3案（SEO最適化済み）
・メタディスクリプション
・見出し構成（h2/h3）
・内部リンク設置指示（URLをご提供の場合）

━━━━━━━━━━━━━━━━━━━━━━━━━━
⏱ 対応スピード
━━━━━━━━━━━━━━━━━━━━━━━━━━
・3,000字：翌日納品
・5,000字：2日以内
・継続契約（月5本〜）：優先対応・専用Slackチャンネル設置

━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 料金プラン
━━━━━━━━━━━━━━━━━━━━━━━━━━
■ ライト（3,000字）   ¥8,000
■ スタンダード（5,000字） ¥12,000
■ プレミアム（8,000字）  ¥18,000
■ 月次契約（5本〜）   1本あたり10%OFF

※ キーワード選定込みの場合は+¥2,000
※ 競合調査レポート付きの場合は+¥3,000

━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 ご依頼の流れ
━━━━━━━━━━━━━━━━━━━━━━━━━━
① ご依頼・ヒアリング（サイトURL・キーワード・トーン）
② 構成案の提出（1〜2営業日）→ご確認
③ 本文執筆・納品
④ 無料修正1回

━━━━━━━━━━━━━━━━━━━━━━━━━━
❓ よくある質問
━━━━━━━━━━━━━━━━━━━━━━━━━━
Q. AI生成は使いますか？
A. 構成・調査にAIを活用し、最終的に人間がリライト・監修したオリジナルコンテンツを納品します。

Q. 修正は何回できますか？
A. 初回無料1回。2回目以降は¥2,000/回。

Q. 月10本以上の大量発注は対応可能ですか？
A. 可能です。月10本以上は別途お見積もりいたします。""",
    "price": "8000",
    "category_hint": "ライティング",
}


def post_cw_service(page) -> bool:
    """CW サービス出品フォームを自動入力・送信"""
    print("  → CW サービス出品ページを開きます...")
    page.goto("https://crowdworks.jp/services/new", wait_until="networkidle", timeout=30000)
    time.sleep(2)

    # カテゴリ選択（ライティング）
    for sel in [
        "a:has-text('ライティング')",
        "label:has-text('ライティング')",
        "input[value*='writing']",
    ]:
        el = page.query_selector(sel)
        if el:
            el.click()
            time.sleep(1)
            break

    # タイトル
    for sel in [
        "input[name*='title']",
        "input[name*='name']",
        "input[placeholder*='タイトル']",
        "#service_title",
    ]:
        el = page.query_selector(sel)
        if el:
            el.fill(SERVICE["title"])
            time.sleep(0.3)
            break

    # 説明文
    for sel in [
        "textarea[name*='description']",
        "textarea[name*='body']",
        "#service_description",
        "textarea",
    ]:
        el = page.query_selector(sel)
        if el:
            el.fill(SERVICE["description"])
            time.sleep(0.3)
            break

    # 料金
    for sel in [
        "input[name*='price']",
        "input[placeholder*='金額']",
        "#service_price",
    ]:
        el = page.query_selector(sel)
        if el:
            el.fill(SERVICE["price"])
            time.sleep(0.3)
            break

    # 送信
    for sel in [
        "button[type='submit']",
        "input[type='submit']",
        "button:has-text('出品')",
        "button:has-text('登録')",
        "button:has-text('送信')",
    ]:
        btn = page.query_selector(sel)
        if btn:
            btn.click()
            time.sleep(4)
            print(f"  ✅ CW サービス出品送信完了")
            print(f"     現在URL: {page.url}")
            return True

    # フォールバック: 手動用にURLをコピー
    import subprocess
    subprocess.run("pbcopy", input=SERVICE["description"].encode("utf-8"))
    import subprocess as sp
    sp.run(["open", "https://crowdworks.jp/services/new"])
    print("  ⚠️  自動送信未完了 → ブラウザを開いて手動で送信してください")
    print("     説明文はクリップボードにコピー済みです（Cmd+V で貼り付け）")
    return False


def run():
    if not SESSION_FILE.exists():
        print("❌ セッションファイルなし")
        print(f"   {PIPELINE_DIR}/pipeline/00_session_setup.py を実行してください")
        sys.exit(1)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ Playwright未インストール")
        print("   pip install playwright && playwright install chromium")
        sys.exit(1)

    storage = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  SEOライティング サービス自動出品")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=200)
        ctx = browser.new_context(
            storage_state=storage,
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()

        ok = post_cw_service(page)

        ctx.storage_state(path=str(SESSION_FILE))
        browser.close()

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    status = "✅ 完了" if ok else "⚠️  要手動確認"
    print(f"  CW サービス出品: {status}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    run()
