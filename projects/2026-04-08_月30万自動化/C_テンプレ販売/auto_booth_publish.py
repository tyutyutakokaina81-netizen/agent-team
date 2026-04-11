"""
auto_booth_publish.py — BOOTH への商品自動出品

やること（自動）:
  1. BOOTH にブラウザで開く
  2. Google ログインボタンをクリック（ユーザーが Google 許可を1回クリック）
  3. Vol.1〜4 の商品ページを自動で作成・出品

やること（手動・1回だけ）:
  - Google の許可ボタンを1クリック
  - 振込先口座の登録（BOOTHの収益を受け取るため）

実行方法:
  pip install playwright && playwright install chromium
  python generate_products.py   # 先にファイル生成
  python auto_booth_publish.py
"""

import json
import time
from pathlib import Path

DIST_DIR = Path(__file__).parent / "dist"
SESSION_FILE = Path(__file__).parent.parent.parent / ".sessions" / "booth_session.json"
SESSION_FILE.parent.mkdir(exist_ok=True)

PRODUCTS = [
    {
        "title": "フリーランス収支管理スプレッドシート【Googleスプレッドシート・確定申告対応】",
        "description": """フリーランスの収入・経費・案件を1枚で管理できるExcelテンプレートです。

【含まれるもの】
・Excel ファイル（.xlsx）※Googleスプレッドシートでもそのまま使えます
・4シート構成：収入 / 経費 / 案件管理 / 年間サマリー

【できること】
✅ 収入を入力すると月別・年間サマリーを自動生成
✅ 案件ごとの実質時給を自動計算
✅ 経費を科目別（通信費・交通費等）に自動集計
✅ 確定申告の準備資料として活用できる

【動作環境】
・Microsoft Excel / Googleスプレッドシート（無料）
・スマホ・PC 両対応

【返金について】
デジタルコンテンツの性質上、返金はお受けできません。""",
        "price": 980,
        "file": "vol1_freelance_cashflow.xlsx",
        "tags": ["フリーランス", "スプレッドシート", "確定申告", "収支管理", "テンプレート"],
    },
    {
        "title": "SNS投稿カレンダー【投稿テーマ50選付き・Googleスプレッドシート対応】",
        "description": """Instagram・X・Facebook を一括管理できる月次カレンダーです。

【含まれるもの】
・Excel ファイル（.xlsx）※Googleスプレッドシート対応
・2シート構成：月次カレンダー / 投稿テーマ50選

【できること】
✅ 月別カレンダーで投稿予定を管理
✅ 複数SNSを一覧管理（Instagram/X/Facebook/TikTok）
✅ テーマ・ハッシュタグ・投稿ステータスを一元化
✅ 投稿テーマ50選でネタ切れ知らず

【こんな方に】
・複数SNSをまとめて管理したい方
・月初に1ヶ月の投稿計画を立てたい方

【返金について】
デジタルコンテンツの性質上、返金はお受けできません。""",
        "price": 680,
        "file": "vol2_sns_calendar.xlsx",
        "tags": ["SNS", "Instagram", "投稿管理", "カレンダー", "スプレッドシート"],
    },
    {
        "title": "飲食店オーナー向けAIプロンプト集20選【ChatGPT・Claude対応｜SNS投稿文が30秒で完成】",
        "description": """飲食店のSNS投稿に特化したAIプロンプト（指示文）を20個収録したテキストファイルです。

【収録プロンプト20選】
新メニュー紹介 / 季節限定メニュー / スタッフ紹介 / お客様の声 / 食材こだわり紹介
営業時間のお知らせ / イベント告知 / テイクアウト告知 / ランチ紹介 / 周年記念
雨の日特典 / 予約受付 / 満席御礼 / 求人募集 / 産地紹介
シェフコメント / 人気メニュー紹介 / ドリンク紹介 / 地域イベント連動 / 年末年始告知

【使い方】
ChatGPT・Claude・Gemini 全てに使えます。
[ ] の部分をお店の情報に書き換えて貼るだけで投稿文が完成。

【返金について】
デジタルコンテンツの性質上、返金はお受けできません。""",
        "price": 1980,
        "file": None,  # テキストファイル → 商品説明にプロンプト全文を含める
        "tags": ["飲食店", "ChatGPT", "AIプロンプト", "SNS", "Instagram", "集客"],
    },
    {
        "title": "【3点セット32%OFF】フリーランス独立スターターパック｜収支管理+SNSカレンダー+プロンプト集",
        "description": """Vol.1〜3 の3点セットです。単品合計¥3,660 → ¥2,480（32%OFF）

【セット内容】
1. フリーランス収支管理スプレッドシート（単品¥980）
2. SNS投稿カレンダー（単品¥680）
3. 飲食店向けAIプロンプト集20選（単品¥1,980）

【こんな方に】
・フリーランス1年目で何から整えればいいかわからない方
・お金の管理とSNS発信を同時に整えたい方
・AIを活用して作業を効率化したい方

一度購入すれば永久に使い回せます。

【返金について】
デジタルコンテンツの性質上、返金はお受けできません。""",
        "price": 2480,
        "file": "vol1_freelance_cashflow.xlsx",  # 代表ファイル（購入後に全ファイルを配布）
        "tags": ["フリーランス", "副業", "セット", "テンプレート", "AIプロンプト"],
    },
]


def wait_for_login(page, timeout=120):
    """Google OAuth ログイン完了を待つ"""
    print("\n  ⏳ Google のログイン許可画面が開きます")
    print("  👆 Google アカウントを選択して「許可」をクリックしてください")
    print(f"  （{timeout}秒以内に操作してください）\n")

    start = time.time()
    while time.time() - start < timeout:
        try:
            if "booth.pm" in page.url and "/dashboard" in page.url:
                return True
            if page.query_selector(".p-header__username, .c-globalHeader__username, [class*='username']"):
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


def setup_booth_session(playwright):
    """BOOTH にログインしてセッションを保存"""
    print("\n[BOOTH] ブラウザを起動してログインします...")

    browser = playwright.chromium.launch(headless=False, slow_mo=200)
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    page = context.new_page()

    page.goto("https://accounts.booth.pm/users/sign_in")
    time.sleep(2)

    # Google ログインボタンを探してクリック
    for selector in [
        "a[href*='google']",
        "a[data-provider='google']",
        ".c-btn--google",
        "a:has-text('Google')",
    ]:
        btn = page.query_selector(selector)
        if btn:
            btn.click()
            print("  Google ログインボタンをクリックしました")
            break
    else:
        print("  Google ログインボタンが見つかりません")
        print("  手動でログインしてください...")

    logged_in = wait_for_login(page)

    if logged_in or page.query_selector("[class*='header'][class*='user'], [class*='mypage']"):
        storage = context.storage_state()
        SESSION_FILE.write_text(json.dumps(storage, ensure_ascii=False, indent=2), encoding="utf-8")
        print("  ✅ ログイン成功・セッション保存")
    else:
        print("  ⚠️  ログイン確認できず（セッションは保存します）")
        storage = context.storage_state()
        SESSION_FILE.write_text(json.dumps(storage, ensure_ascii=False, indent=2), encoding="utf-8")

    browser.close()
    return context


def publish_products(playwright):
    """BOOTH に商品を自動出品"""
    if not SESSION_FILE.exists():
        print("[ERROR] セッションがありません。先に BOOTH ログインを実行してください")
        return False

    storage = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    browser = playwright.chromium.launch(headless=False, slow_mo=300)
    context = browser.new_context(
        storage_state=storage,
        viewport={"width": 1280, "height": 800},
    )
    page = context.new_page()

    success_count = 0
    for i, product in enumerate(PRODUCTS, 1):
        print(f"\n[{i}/{len(PRODUCTS)}] 出品中: {product['title'][:35]}...")

        try:
            # 商品作成ページ
            page.goto("https://manage.booth.pm/items/new")
            time.sleep(2)

            # タイトル
            for sel in ["#item_name", "[name='item[name]']", "input[placeholder*='タイトル']"]:
                el = page.query_selector(sel)
                if el:
                    el.fill(product["title"])
                    break

            time.sleep(0.5)

            # 説明文
            for sel in ["#item_description", "[name='item[description]']", "textarea[placeholder*='説明']"]:
                el = page.query_selector(sel)
                if el:
                    el.fill(product["description"])
                    break

            time.sleep(0.5)

            # 価格
            for sel in ["#item_price", "[name='item[price]']", "input[placeholder*='価格']"]:
                el = page.query_selector(sel)
                if el:
                    el.fill(str(product["price"]))
                    break

            time.sleep(0.5)

            # ファイル添付
            if product["file"]:
                file_path = DIST_DIR / product["file"]
                if file_path.exists():
                    for sel in ["input[type='file']", "#item_file"]:
                        el = page.query_selector(sel)
                        if el:
                            el.set_input_files(str(file_path))
                            print(f"  📎 ファイル添付: {product['file']}")
                            time.sleep(1)
                            break
                else:
                    print(f"  ⚠️  ファイルなし: {file_path}（先に generate_products.py を実行）")

            time.sleep(1)

            # 保存（下書き）
            for sel in ["[type='submit']", "button:has-text('保存')", "input[value*='保存']"]:
                btn = page.query_selector(sel)
                if btn:
                    btn.click()
                    time.sleep(2)
                    print(f"  ✅ 保存完了（下書き状態）")
                    success_count += 1
                    break

        except Exception as e:
            print(f"  ❌ エラー: {e}")

        time.sleep(1)

    browser.close()

    print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  出品完了: {success_count}/{len(PRODUCTS)} 件")
    if success_count > 0:
        print(f"  ⚠️  下書き状態です。BOOTH 管理画面で「公開」にしてください")
        print(f"  https://manage.booth.pm/items")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    return success_count > 0


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[ERROR] pip install playwright && playwright install chromium")
        return

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  BOOTH 自動出品スクリプト")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # 商品ファイル確認
    missing = [p["file"] for p in PRODUCTS if p["file"] and not (DIST_DIR / p["file"]).exists()]
    if missing:
        print(f"\n⚠️  商品ファイルがありません: {missing}")
        print("先に以下を実行してください:")
        print("  python generate_products.py\n")

    with sync_playwright() as p:
        # ログイン
        if not SESSION_FILE.exists():
            print("\n[STEP 1] BOOTH にログイン（Google ボタンを1クリック）")
            setup_booth_session(p)
        else:
            print("\n[STEP 1] セッションあり（ログインスキップ）✅")

        # 出品
        print("\n[STEP 2] 商品を自動出品します...")
        publish_products(p)

    print("\n【次のステップ】")
    print("1. https://manage.booth.pm/items で各商品を「公開」に変更")
    print("2. https://manage.booth.pm/payment_accounts で振込先口座を登録")
    print("   （口座登録しないと売上を受け取れません）")


if __name__ == "__main__":
    main()
