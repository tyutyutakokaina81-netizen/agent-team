"""
booth_requests.py — ブラウザ不要のBOOTH操作クライアント

使い方:
  1. あなたのブラウザで https://booth.pm にログイン
  2. ブラウザの開発者ツール（F12）→ Application → Cookies → booth.pm
  3. "_booth_session" の値をコピー
  4. このスクリプトを実行:
     python3 booth_requests.py --cookie "ペーストした値"

できること:
  - 売上・注文の確認（GET）
  - 商品の出品（POST）
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("[ERROR] pip install requests")
    sys.exit(1)

REPO_DIR     = Path(__file__).parent
SESSION_FILE = REPO_DIR / ".sessions" / "booth_session.json"
SESSION_FILE.parent.mkdir(exist_ok=True)
LOG_DIR      = REPO_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

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
        "file": REPO_DIR / "projects/2026-04-08_月30万自動化/C_テンプレ販売/dist/vol1_freelance_cashflow.xlsx",
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
        "file": REPO_DIR / "projects/2026-04-08_月30万自動化/C_テンプレ販売/dist/vol2_sns_calendar.xlsx",
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
        "file": None,
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
        "file": REPO_DIR / "projects/2026-04-08_月30万自動化/C_テンプレ販売/dist/vol1_freelance_cashflow.xlsx",
        "tags": ["フリーランス", "副業", "セット", "テンプレート", "AIプロンプト"],
    },
]


# ─────────────────────────────────────────────
# セッション管理
# ─────────────────────────────────────────────

def make_session(cookie_str: str) -> requests.Session:
    """クッキー文字列からrequestsセッションを作成"""
    sess = requests.Session()
    sess.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept-Language": "ja,en-US;q=0.9",
    })
    # "_booth_session=xxx; remember_user_token=yyy" 形式に対応
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            sess.cookies.set(k.strip(), v.strip(), domain=".booth.pm")
    return sess


def save_session(cookie_str: str):
    """セッションをファイルに保存"""
    SESSION_FILE.write_text(json.dumps({"cookie": cookie_str}, ensure_ascii=False), encoding="utf-8")
    print(f"  ✅ セッション保存: {SESSION_FILE}")


def load_session() -> requests.Session | None:
    """保存済みセッションを読み込む"""
    if not SESSION_FILE.exists():
        return None
    try:
        data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        cookie = data.get("cookie", "")
        if cookie:
            return make_session(cookie)
    except Exception:
        pass
    return None


def test_session(sess: requests.Session) -> bool:
    """セッションが有効かテスト"""
    try:
        r = sess.get("https://manage.booth.pm/items", timeout=10, allow_redirects=True)
        if "sign_in" in r.url or "login" in r.url:
            print("  ❌ セッション無効（ログインページにリダイレクト）")
            return False
        print("  ✅ セッション有効")
        return True
    except Exception as e:
        print(f"  ❌ 接続エラー: {e}")
        return False


# ─────────────────────────────────────────────
# 売上確認
# ─────────────────────────────────────────────

def check_sales(sess: requests.Session) -> dict:
    """売上・注文情報を取得"""
    from datetime import datetime, date

    orders = []
    total_revenue = 0
    bank_account_required = False

    try:
        r = sess.get("https://manage.booth.pm/orders", timeout=15)
        html = r.text

        # 振込口座未登録チェック
        if "payment_account" in html and ("未登録" in html or "register" in html.lower()):
            bank_account_required = True

        # 金額を抽出
        amounts = re.findall(r"¥([\d,]+)", html)
        for a in amounts:
            v = int(a.replace(",", ""))
            if 100 <= v <= 100000:  # 妥当な金額範囲
                total_revenue += v
                orders.append({"amount": v, "date": date.today().isoformat()})

    except Exception as e:
        return {"error": str(e), "orders": [], "total_revenue": 0, "bank_account_required": False}

    return {
        "orders": orders,
        "total_revenue": total_revenue,
        "bank_account_required": bank_account_required,
        "error": None,
        "checked_at": datetime.now().strftime("%Y/%m/%d %H:%M"),
    }


# ─────────────────────────────────────────────
# 商品出品
# ─────────────────────────────────────────────

def get_csrf_token(sess: requests.Session, url: str) -> str | None:
    """ページからCSRFトークンを取得（複数パターン対応）"""
    try:
        r = sess.get(url, timeout=15)
        html = r.text

        # パターン1: <meta name="csrf-token" content="...">
        m = re.search(r'<meta[^>]+name=["\']csrf-token["\'][^>]+content=["\']([^"\']+)["\']', html)
        if m:
            return m.group(1)

        # パターン2: <meta content="..." name="csrf-token">（属性順が逆）
        m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']csrf-token["\']', html)
        if m:
            return m.group(1)

        # パターン3: <input type="hidden" name="authenticity_token" value="...">
        m = re.search(r'name=["\']authenticity_token["\'][^>]*value=["\']([^"\']+)["\']', html)
        if m:
            return m.group(1)

        # パターン4: value="..." name="authenticity_token"（属性順が逆）
        m = re.search(r'value=["\']([^"\']{20,})["\'][^>]*name=["\']authenticity_token["\']', html)
        if m:
            return m.group(1)

        # パターン5: JSON内の csrf_token
        m = re.search(r'"csrf_token"\s*:\s*"([^"]+)"', html)
        if m:
            return m.group(1)

    except Exception as e:
        print(f"  [debug] CSRF取得エラー: {e}")
    return None


def publish_product(sess: requests.Session, product: dict) -> bool:
    """1商品をBOOTHに出品"""
    new_item_url = "https://manage.booth.pm/items/new"
    csrf = get_csrf_token(sess, new_item_url)
    if not csrf:
        # manage.booth.pm トップからも試みる
        csrf = get_csrf_token(sess, "https://manage.booth.pm/")
    if not csrf:
        print("  ⚠️  CSRFトークン取得失敗（BOOTHにログイン中か確認してください）")
        return False

    # タグをカンマ区切りで渡す
    tags = ",".join(product.get("tags", []))

    data = {
        "authenticity_token": csrf,
        "item[name]": product["title"],
        "item[description]": product["description"],
        "item[price]": str(product["price"]),
        "item[status]": "on_sale",
        "item[tag_list]": tags,
        "item[category_id]": "",
        "item[type]": "digital",
    }

    files = {}
    file_path = product.get("file")
    if file_path and Path(file_path).exists():
        files["item[item_files_attributes][0][file]"] = open(file_path, "rb")

    try:
        r = sess.post(
            "https://manage.booth.pm/items",
            data=data,
            files=files if files else None,
            timeout=30,
            allow_redirects=True,
        )
        for f in files.values():
            f.close()

        # 成功判定
        if r.status_code in (200, 201) and "items/new" not in r.url:
            return True
        if r.status_code == 302:
            location = r.headers.get("Location", "")
            if "items/new" not in location:
                return True
        return False
    except Exception as e:
        print(f"  エラー: {e}")
        return False


def publish_all(sess: requests.Session):
    """全商品を出品"""
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  BOOTH 商品出品（ブラウザ不要）")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    success = 0
    for i, product in enumerate(PRODUCTS, 1):
        print(f"\n[{i}/{len(PRODUCTS)}] {product['title'][:40]}...")
        ok = publish_product(sess, product)
        if ok:
            print(f"  ✅ 出品完了")
            success += 1
        else:
            print(f"  ❌ 失敗（手動で登録してください）")
        time.sleep(2)

    print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  完了: {success}/{len(PRODUCTS)} 件")
    print(f"  確認: https://manage.booth.pm/items")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


# ─────────────────────────────────────────────
# メイン
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ブラウザ不要のBOOTH操作")
    parser.add_argument("--cookie", help="_booth_session クッキー値")
    parser.add_argument("--check-sales", action="store_true", help="売上確認のみ")
    parser.add_argument("--publish", action="store_true", help="商品出品")
    args = parser.parse_args()

    # セッション取得
    if args.cookie:
        sess = make_session(args.cookie)
        save_session(args.cookie)
    else:
        sess = load_session()
        if not sess:
            print("\n使い方:")
            print("  1. https://booth.pm にブラウザでログイン")
            print("  2. F12 → Application → Cookies → .booth.pm")
            print("  3. _booth_session の値をコピー")
            print("  4. python3 booth_requests.py --cookie 'コピーした値'")
            sys.exit(1)

    # セッションテスト
    print("\nセッション確認中...")
    if not test_session(sess):
        print("クッキーを再取得して --cookie オプションで渡してください")
        sys.exit(1)

    if args.check_sales:
        print("\n売上確認中...")
        result = check_sales(sess)
        print(f"  合計売上: ¥{result['total_revenue']:,}")
        print(f"  注文数  : {len(result['orders'])}件")
        if result.get("bank_account_required"):
            print("  🚨 振込口座未登録 → https://manage.booth.pm/payment_accounts")
        return

    if args.publish:
        publish_all(sess)
        return

    # デフォルト: 出品 + 売上確認
    publish_all(sess)
    print("\n売上確認中...")
    result = check_sales(sess)
    print(f"  合計売上: ¥{result['total_revenue']:,}")
    if result.get("bank_account_required"):
        print("  🚨 【手動対応】振込口座を登録してください → https://manage.booth.pm/payment_accounts")


if __name__ == "__main__":
    main()
