#!/usr/bin/env python3
"""
mac_booth_publish.py v2 — BOOTH出品（2ステップ方式）
1. select_type の digital フォームで blank item を作成 → item_id 取得
2. PATCH で商品情報 + ファイルを登録して公開
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
        print("❌ セッションなし。mac_auto_cookie.py を先に実行してください")
        sys.exit(1)
    data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    cookie_str = data.get("cookie", "")
    sess = requests.Session()
    sess.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json, text/html, */*",
        "Accept-Language": "ja,en-US;q=0.9",
        "Referer": "https://manage.booth.pm/",
        "X-Requested-With": "XMLHttpRequest",
    })
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            sess.cookies.set(k.strip(), v.strip(), domain=".booth.pm")
    return sess


def get_select_type_forms(sess):
    """select_type ページのフォームを解析して返す"""
    r = sess.get("https://manage.booth.pm/items/select_type", timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    forms = []
    for form in soup.find_all("form"):
        action = form.get("action", "")
        inputs = {}
        for inp in form.find_all(["input", "select", "textarea"]):
            name = inp.get("name")
            val = inp.get("value", "")
            if name:
                inputs[name] = val
        forms.append({"action": action, "inputs": inputs})
    return forms


def extract_csrf(html_text):
    """HTML から CSRF トークンを取得（meta tag または form input）"""
    soup = BeautifulSoup(html_text, "html.parser")
    # React SPA でも <meta name="csrf-token"> は含まれることが多い
    meta = soup.find("meta", {"name": "csrf-token"})
    if meta and meta.get("content"):
        return meta["content"]
    # フォームの hidden input
    for inp in soup.find_all("input", {"name": "authenticity_token"}):
        val = inp.get("value", "")
        if val:
            return val
    return None


def create_digital_item(sess, forms):
    """
    デジタルアイテムを select_type フォームで作成し、item_id と CSRF を返す。
    戻り値: (item_id, edit_csrf) or (None, None)
    """
    # 'digital' を action URL に含むフォームを選択
    digital_form = next(
        (f for f in forms if "digital" in f.get("action", "")), None
    )
    if not digital_form:
        return None, None

    action = digital_form["action"]
    csrf = digital_form["inputs"].get("authenticity_token", "")
    url = f"https://manage.booth.pm{action}" if action.startswith("/") else action

    print(f"  デジタルフォーム: {url}")

    # POST → blank デジタルアイテム作成 → /items/{id}/edit へリダイレクト
    r = sess.post(url, data={"authenticity_token": csrf},
                  timeout=20, allow_redirects=True)
    print(f"  作成後URL: {r.url} (status: {r.status_code})")

    # アイテムID を URL から抽出
    m = re.search(r"/items/(\d+)", r.url)
    if not m:
        print(f"  ❌ アイテムIDが取得できません")
        return None, None

    item_id = m.group(1)

    # edit ページの CSRF を取得（meta tag 優先）
    edit_csrf = extract_csrf(r.text)
    if not edit_csrf:
        # フォールバック: select_type の CSRF をそのまま使用
        edit_csrf = csrf
        print(f"  ⚠️  edit CSRF が見つからないため select_type の CSRF を使用")

    return item_id, edit_csrf


def update_item(sess, item_id, product, csrf):
    """PATCH でアイテムに商品情報とファイルを登録し、公開状態にする"""
    url = f"https://manage.booth.pm/items/{item_id}"

    # BOOTH React SPA は JSON API → X-CSRF-Token ヘッダー + Accept: application/json
    extra_headers = {
        "X-CSRF-Token": csrf,
        "Accept": "application/json, */*",
        "Referer": f"https://manage.booth.pm/items/{item_id}/edit",
    }

    data = {
        "item[name]": product["title"],
        "item[description]": product["description"],
        "item[price]": product["price"],
        "item[tag_list]": product["tags"],
        "item[status]": "on_sale",
    }

    files = {}
    fp = product.get("file")
    if fp and Path(fp).exists():
        files["item[item_files_attributes][0][file]"] = (
            Path(fp).name,
            open(fp, "rb"),
            "application/octet-stream",
        )
        print(f"  ファイル: {Path(fp).name} ({Path(fp).stat().st_size // 1024}KB)")
    else:
        print(f"  ⚠️  ファイルなし: {fp}")

    # 実際の PATCH メソッドを使用（_method オーバーライド不要）
    r = sess.patch(url, data=data, files=files if files else None,
                   headers=extra_headers, timeout=30, allow_redirects=True)

    for fv in files.values():
        fv[1].close()

    return r


def main():
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  BOOTH 出品（2ステップ方式 v2）")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    sess = make_session()

    # ログイン確認
    r = sess.get("https://manage.booth.pm/items", timeout=15, allow_redirects=True)
    if "sign_in" in r.url or "login" in r.url:
        print("❌ セッション無効。mac_auto_cookie.py を再実行してください")
        sys.exit(1)
    print(f"✅ ログイン確認: {r.url}\n")

    # 前回誤作成のアイテムがある場合の案内
    print("📋 注意: 前回のテスト実行で誤作成されたアイテムがある場合は")
    print("   https://manage.booth.pm/items?state=draft で確認・削除してください\n")

    # 前回作成済みの blank デジタルアイテム（再利用して無駄な作成を防ぐ）
    # 新規作成する場合は空リストにする: REUSE_IDS = []
    REUSE_IDS = ["8190086", "8190087", "8190088", "8190089"]

    success = 0
    created_ids = []

    for i, product in enumerate(PRODUCTS, 1):
        print(f"[{i}/{len(PRODUCTS)}] {product['title'][:45]}...")

        # 再利用 or 新規作成
        if i - 1 < len(REUSE_IDS):
            item_id = REUSE_IDS[i - 1]
            print(f"  既存アイテム再利用: {item_id}")
            # edit ページから CSRF を取得
            r_edit = sess.get(f"https://manage.booth.pm/items/{item_id}/edit", timeout=15)
            edit_csrf = extract_csrf(r_edit.text)
            if not edit_csrf:
                # select_type から CSRF を取得
                forms = get_select_type_forms(sess)
                edit_csrf = next(
                    (f["inputs"].get("authenticity_token") for f in forms if f["inputs"].get("authenticity_token")),
                    None
                )
        else:
            # select_type フォームを毎回取得（CSRF 更新のため）
            forms = get_select_type_forms(sess)
            print(f"  フォーム数: {len(forms)} | "
                  f"digital: {'✅' if any('digital' in f['action'] for f in forms) else '❌'}")

            # blank デジタルアイテムを作成
            item_id, edit_csrf = create_digital_item(sess, forms)
            if not item_id:
                print(f"  ❌ アイテム作成スキップ\n")
                continue

        created_ids.append(item_id)
        print(f"  アイテムID: {item_id}")

        # Step 2: PATCH で商品情報 + ファイルを登録
        r2 = update_item(sess, item_id, product, edit_csrf)
        print(f"  更新後URL: {r2.url} (status: {r2.status_code})")

        if r2.status_code < 400 and "/edit" not in r2.url:
            print(f"  ✅ 出品完了: https://freelance-tools.booth.pm/items/{item_id}")
            success += 1
        else:
            print(f"  ⚠️  要確認: https://manage.booth.pm/items/{item_id}/edit")
            # エラー内容を抽出して表示
            err_soup = BeautifulSoup(r2.text, "html.parser")
            # JSON エラーレスポンスの可能性
            try:
                err_json = r2.json()
                print(f"     JSON: {str(err_json)[:200]}")
            except Exception:
                # HTML エラーメッセージを抽出
                for sel in [".error", ".alert", "[class*='error']", "[class*='alert']"]:
                    errors = err_soup.select(sel)
                    if errors:
                        msgs = [e.get_text(strip=True)[:80] for e in errors[:3]]
                        print(f"     エラー: {msgs}")
                        break

        print()
        time.sleep(3)

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  完了: {success}/{len(PRODUCTS)} 件")
    if created_ids:
        print(f"  作成ID: {', '.join(created_ids)}")
    print(f"  確認: https://manage.booth.pm/items")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    main()
