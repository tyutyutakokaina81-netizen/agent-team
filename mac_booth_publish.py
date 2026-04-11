#!/usr/bin/env python3
"""
mac_booth_publish.py — BOOTH出品（requests版・フォーム解析）
select_type の form action を取得して直接POST
"""
import json, re, sys, time
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install",
                   "requests", "beautifulsoup4", "--break-system-packages", "-q"])
    import requests
    from bs4 import BeautifulSoup

SESSION_FILE = Path(__file__).parent / ".sessions" / "booth_session.json"
DIST_DIR = Path(__file__).parent / "projects/2026-04-08_月30万自動化/C_テンプレ販売/dist"

PRODUCTS = [
    {
        "title": "フリーランス収支管理スプレッドシート【Googleスプレッドシート・確定申告対応】",
        "description": "フリーランスの収入・経費・案件を1枚で管理できるスプレッドシートテンプレートです。\n\n【含まれるもの】\n・Excel ファイル（.xlsx）\n・4シート構成：収入 / 経費 / 案件管理 / 年間サマリー\n\n【できること】\n✅ 月別・年間サマリーを自動生成\n✅ 案件ごとの実質時給を自動計算\n✅ 確定申告の準備資料として活用できる\n\n【返金について】\nデジタルコンテンツの性質上、返金はお受けできません。",
        "price": "980",
        "tags": "フリーランス,スプレッドシート,確定申告,収支管理,テンプレート",
        "file": DIST_DIR / "vol1_freelance_cashflow.xlsx",
    },
    {
        "title": "SNS投稿カレンダー【投稿テーマ50選付き・Googleスプレッドシート対応】",
        "description": "Instagram・X・Facebookを一括管理できる月次カレンダーです。\n\n【含まれるもの】\n・Excel ファイル（.xlsx）\n・2シート構成：月次カレンダー / 投稿テーマ50選\n\n✅ 複数SNSを一覧管理\n✅ 投稿テーマ50選でネタ切れ知らず\n\n【返金について】\nデジタルコンテンツの性質上、返金はお受けできません。",
        "price": "680",
        "tags": "SNS,Instagram,投稿管理,カレンダー,スプレッドシート",
        "file": DIST_DIR / "vol2_sns_calendar.xlsx",
    },
    {
        "title": "飲食店オーナー向けAIプロンプト集20選【ChatGPT・Claude対応｜SNS投稿文が30秒で完成】",
        "description": "飲食店のSNS投稿に特化したAIプロンプトを20個収録したテキストファイルです。\n\n【使い方】\nChatGPT・Claude・Gemini 全てに使えます。[ ] の部分を書き換えて貼るだけ。\n\n新メニュー紹介 / 季節限定 / スタッフ紹介 / イベント告知 など20種類収録\n\n【返金について】\nデジタルコンテンツの性質上、返金はお受けできません。",
        "price": "1980",
        "tags": "飲食店,ChatGPT,AIプロンプト,SNS,Instagram,集客",
        "file": Path(__file__).parent / "projects/2026-04-08_月30万自動化/C_テンプレ販売/vol3_restaurant_prompts.txt",
    },
    {
        "title": "【3点セット32%OFF】フリーランス独立スターターパック｜収支管理+SNSカレンダー+プロンプト集",
        "description": "Vol.1〜3の3点セットです。単品合計¥3,660 → ¥2,480（32%OFF）\n\n1. フリーランス収支管理スプレッドシート（¥980）\n2. SNS投稿カレンダー（¥680）\n3. 飲食店向けAIプロンプト集20選（¥1,980）\n\n【返金について】\nデジタルコンテンツの性質上、返金はお受けできません。",
        "price": "2480",
        "tags": "フリーランス,副業,セット,テンプレート,AIプロンプト",
        "file": DIST_DIR / "vol1_freelance_cashflow.xlsx",
    },
]


def make_session():
    if not SESSION_FILE.exists():
        print("❌ セッションなし")
        sys.exit(1)
    data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    cookie_str = data.get("cookie", "")
    sess = requests.Session()
    sess.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "ja,en-US;q=0.9",
        "Referer": "https://manage.booth.pm/",
    })
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            sess.cookies.set(k.strip(), v.strip(), domain=".booth.pm")
    return sess


def get_forms(sess, url):
    """ページのフォームを全て解析して返す"""
    r = sess.get(url, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    forms = []
    for form in soup.find_all("form"):
        action = form.get("action", "")
        method = form.get("method", "post").lower()
        inputs = {}
        for inp in form.find_all(["input", "select", "textarea"]):
            name = inp.get("name")
            val = inp.get("value", "")
            if name:
                inputs[name] = val
        forms.append({"action": action, "method": method, "inputs": inputs})
    return forms, soup


def publish_product(sess, product, form_url, csrf_token):
    """商品を出品"""
    data = {
        "authenticity_token": csrf_token,
        "item[name]": product["title"],
        "item[description]": product["description"],
        "item[price]": product["price"],
        "item[tag_list]": product["tags"],
        "item[status]": "on_sale",
        "item[type]": "digital",
    }

    files = {}
    fp = product.get("file")
    if fp and Path(fp).exists():
        files["item[item_files_attributes][0][file]"] = (
            Path(fp).name,
            open(fp, "rb"),
            "application/octet-stream",
        )

    r = sess.post(
        form_url,
        data=data,
        files=files if files else None,
        timeout=30,
        allow_redirects=True,
    )
    for f in files.values():
        f[1].close()

    return r


def main():
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  BOOTH 出品（フォーム解析版）")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    sess = make_session()

    # select_type フォームを解析
    print("フォームを解析中...")
    forms, soup = get_forms(sess, "https://manage.booth.pm/items/select_type")
    print(f"  フォーム数: {len(forms)}個")
    for i, f in enumerate(forms):
        print(f"  [{i}] action={f['action']} inputs={list(f['inputs'].keys())}")

    # デジタル商品フォームを特定してPOST
    digital_url = None
    digital_csrf = None

    for f in forms:
        action = f.get("action", "")
        if "digital" in action or "item" in action:
            digital_url = "https://manage.booth.pm" + action if action.startswith("/") else action
            digital_csrf = f["inputs"].get("authenticity_token", "")
            break

    if not digital_url:
        # 最初のフォームを試す
        if forms:
            f = forms[0]
            action = f.get("action", "")
            digital_url = "https://manage.booth.pm" + action if action.startswith("/") else action
            digital_csrf = f["inputs"].get("authenticity_token", "")
            print(f"  最初のフォームを使用: {digital_url}")

    if not digital_url or not digital_csrf:
        print("❌ フォームが見つかりません")
        print("  全フォーム:")
        for f in forms:
            print(f"    {f}")
        return

    print(f"\n  出品フォーム: {digital_url}")
    print(f"  CSRFトークン: {digital_csrf[:20]}...")

    # まずフォームページに移動してCSRFを再取得
    print("\n出品フォームを取得中...")
    r = sess.post(digital_url,
                  data={"authenticity_token": digital_csrf},
                  timeout=15, allow_redirects=True)
    print(f"  → {r.url} (status: {r.status_code})")

    # 出品フォームのCSRFを取得
    item_forms, item_soup = get_forms(sess, r.url)
    print(f"  出品フォーム要素数: {len(item_forms)}")

    item_csrf = None
    item_post_url = None
    for f in item_forms:
        if f["inputs"].get("authenticity_token"):
            item_csrf = f["inputs"]["authenticity_token"]
            action = f.get("action", "")
            item_post_url = "https://manage.booth.pm" + action if action.startswith("/") else action
            break

    if not item_csrf:
        print("❌ 出品フォームのCSRFが見つかりません")
        print(f"  フォーム内容: {item_forms}")
        return

    # 商品を出品
    success = 0
    for i, product in enumerate(PRODUCTS, 1):
        print(f"\n[{i}/{len(PRODUCTS)}] {product['title'][:40]}...")
        r = publish_product(sess, product, item_post_url or r.url, item_csrf)
        print(f"  status: {r.status_code} | url: {r.url}")
        if r.status_code < 400 and "select_type" not in r.url and "new" not in r.url:
            print(f"  ✅ 出品完了")
            success += 1
        else:
            print(f"  ❌ 失敗")
        time.sleep(2)

    print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  完了: {success}/{len(PRODUCTS)} 件")
    print(f"  確認: https://manage.booth.pm/items")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    main()
