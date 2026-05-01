#!/usr/bin/env python3
"""
mac_publish_all.py — Mac専用・全プラットフォーム一括公開

【実行方法】
  python3 mac_publish_all.py           # note + BOOTH 両方
  python3 mac_publish_all.py --note    # noteのみ
  python3 mac_publish_all.py --booth   # BOOTHのみ

【前提条件】
  pip install requests playwright
  playwright install chromium
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

REPO        = Path(__file__).parent
SESSIONS    = REPO / ".sessions"
SESSIONS.mkdir(exist_ok=True)
CMO_OUT     = REPO / "CMO" / "outputs"
BOOTH_DIST  = REPO / "projects" / "2026-04-08_月30万自動化" / "C_テンプレ販売" / "dist"
NOTE_STATE  = SESSIONS / "note_publish_queue.json"
BOOTH_STATE = SESSIONS / "booth_publish_queue.json"

NOTE_BASE = "https://note.com"
NOTE_V1   = "https://note.com/api/v1"
NOTE_V2   = "https://note.com/api/v2"


# ──────────────────────────────────────────────────────────
# 共通ユーティリティ
# ──────────────────────────────────────────────────────────

def load_env():
    env_file = REPO / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def load_json(path: Path, default) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return default


def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


# ──────────────────────────────────────────────────────────
# note.com 投稿
# ──────────────────────────────────────────────────────────

MONETIZE_FOOTER = """

---

## 旅の予約・準備はこちら

**宿泊予約（高岡・富山）**
- [じゃらんnet — 高岡市のホテル・旅館](https://www.jalan.net/ken/japan_160000/city_16202/)
- [楽天トラベル — 高岡市の宿](https://travel.rakuten.co.jp/place/toyama/takaoka/)

**交通・パス**
- [JR西日本 北陸乗り放題パス](https://www.westjr.co.jp/global/en/travel-information/pass/hokuriku/)

**旅行グッズ（Amazon）**
- [旅行用コンパクトバッグ](https://www.amazon.co.jp/s?k=%E6%97%85%E8%A1%8C+%E3%83%90%E3%83%83%E3%82%B0+%E3%82%B3%E3%83%B3%E3%83%91%E3%82%AF%E3%83%88)
- [ガイドブック「富山・石川」](https://www.amazon.co.jp/s?k=%E3%82%AC%E3%82%A4%E3%83%89%E3%83%96%E3%83%83%E3%82%AF+%E5%AF%8C%E5%B1%B1+%E7%9F%B3%E5%B7%9D)

---

*この記事が役に立ったら「スキ」で応援してください！*

#高岡市 #富山観光 #北陸旅行 #HiddenJapan #国内旅行 #日帰り旅行
"""

NOTE_ARTICLES = [
    {"id": "takaoka_intro",  "price": 0,   "file": "2026-04-28_高岡市観光_note記事.md"},
    {"id": "takaoka_map",    "price": 980, "file": "2026-04-29_高岡観光_有料note記事.md"},
    {"id": "hokuriku_pass",  "price": 500, "file": "2026-04-30_hokuriku_pass_note記事.md"},
    {"id": "budget_guide",   "price": 500, "file": "2026-04-30_takaoka_budget_note記事.md"},
    {"id": "zuiryuji",       "price": 300, "file": "2026-04-29_瑞龍寺_note記事.md"},
    {"id": "daibutsu",       "price": 300, "file": "2026-04-29_高岡大仏_note記事.md"},
    {"id": "kanayamachi",    "price": 300, "file": "2026-04-29_金屋町_note記事.md"},
    {"id": "amehare",        "price": 300, "file": "2026-04-30_amehare_coast_note記事.md"},
    {"id": "doraemon",       "price": 300, "file": "2026-04-30_doraemon_town_note記事.md"},
    {"id": "katsukoji",      "price": 300, "file": "2026-04-30_katsukoji_note記事.md"},
    {"id": "manyo_tram",     "price": 300, "file": "2026-04-30_manyo_tram_note記事.md"},
    {"id": "nousaku",        "price": 300, "file": "2026-04-30_nousaku_craft_note記事.md"},
    {"id": "lacquer",        "price": 300, "file": "2026-04-30_takaoka_lacquer_note記事.md"},
    {"id": "inami_wood",     "price": 300, "file": "2026-04-30_inami_wood_note記事.md"},
    {"id": "kanaya_morning", "price": 300, "file": "2026-04-30_kanaya_morning_note記事.md"},
    {"id": "tofu_shop",      "price": 300, "file": "2026-04-24_奥とうふ店_note記事.md"},
]


def note_login(s: requests.Session) -> str:
    email    = os.environ["NOTE_EMAIL"]
    password = os.environ["NOTE_PASSWORD"]

    r = s.get(NOTE_BASE, timeout=15)
    csrf = ""
    m = re.search(r'"csrfToken"\s*:\s*"([^"]+)"', r.text)
    if m:
        csrf = m.group(1)
    m2 = re.search(r'name="csrf-token"\s+content="([^"]+)"', r.text)
    if m2:
        csrf = m2.group(1)

    headers = {"Content-Type": "application/json", "X-CSRFToken": csrf,
               "Origin": NOTE_BASE, "Referer": f"{NOTE_BASE}/login"}
    r2 = s.post(f"{NOTE_V1}/sessions",
                json={"login": email, "password": password},
                headers=headers, timeout=15)
    if r2.status_code not in (200, 201):
        print(f"  ❌ noteログイン失敗: {r2.status_code} {r2.text[:200]}")
        return ""
    data = r2.json()
    user = data.get("data", {}).get("urlname", "") or data.get("data", {}).get("nickname", "")
    print(f"  ✅ noteログイン: @{user}")
    return user


def note_ensure_magazine(s: requests.Session, urlname: str) -> str:
    name = "世界よ、これが高岡だ。——知られざる日本の宝石・高岡市 完全ガイド"
    r = s.get(f"{NOTE_V2}/creators/{urlname}/magazines", timeout=15)
    if r.ok:
        for mag in r.json().get("data", {}).get("magazines", []):
            if name in mag.get("name", ""):
                print(f"  📖 既存マガジン: {mag['id']}")
                return str(mag["id"])

    desc = (
        "日本人も素通りする、富山県高岡市。\n"
        "国宝3件・日本三大仏・400年続く鋳物と漆器・ドラえもんの生まれた町・"
        "海越しに立山連峰が見える絶景。\n\n"
        "「本物の日本」がここにある。\n\n全16記事をひとつに。保存版ガイドマガジンです。"
    )
    r2 = s.post(f"{NOTE_V1}/magazines",
                json={"name": name, "description": desc, "is_paid": True, "price": 4980},
                timeout=15)
    if r2.status_code in (200, 201):
        mid = str(r2.json().get("data", {}).get("id", ""))
        print(f"  ✅ マガジン作成: {mid}")
        return mid
    print(f"  ⚠️  マガジン作成失敗: {r2.status_code}")
    return ""


def note_post(s: requests.Session, title: str, body: str, price: int, mag_id: str) -> str:
    payload = {
        "subject":      title,
        "body":         body,
        "status":       "published",
        "price":        price,
        "paid_type":    "free" if price == 0 else "partially_free",
        "magazine_ids": [mag_id] if mag_id else [],
        "hashtags":     ["高岡市", "富山観光", "北陸旅行", "HiddenJapan"],
    }
    r = s.post(f"{NOTE_V1}/text_notes", json=payload, timeout=30)
    if r.status_code in (200, 201):
        d = r.json().get("data", {})
        key     = d.get("key", "")
        urlname = d.get("user", {}).get("urlname", "")
        url = f"https://note.com/{urlname}/n/{key}"
        return url
    print(f"  ❌ 投稿失敗 {r.status_code}: {r.text[:300]}")
    return ""


def extract_title(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return "高岡観光ガイド"


def run_note():
    print("\n" + "━"*50)
    print("  [note] 記事一括投稿")
    print("━"*50)

    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
        "Accept": "application/json",
    })

    urlname = note_login(s)
    if not urlname:
        print("  ログイン失敗 → note をスキップ")
        return

    mag_id  = note_ensure_magazine(s, urlname)
    state   = load_json(NOTE_STATE, {"published": {}})
    done    = state["published"]
    results = []

    print(f"\n  {len(NOTE_ARTICLES)}本の記事を投稿中…\n")
    for art in NOTE_ARTICLES:
        if art["id"] in done:
            print(f"  ⏭  スキップ（投稿済み）: {art['id']}")
            continue

        fpath = CMO_OUT / art["file"]
        if not fpath.exists():
            print(f"  ⚠️  ファイルなし: {art['file']}")
            continue

        body  = fpath.read_text(encoding="utf-8") + MONETIZE_FOOTER
        title = extract_title(body)

        if art["price"] == 0:
            body += (
                "\n\n---\n\n"
                "**▼ 各スポットの詳細ガイドはマガジンで**\n\n"
                "👉 高岡市 完全ガイドマガジン（¥4,980）\n\n"
                "#高岡市 #富山観光 #北陸旅行 #HiddenJapan"
            )

        url = note_post(s, title, body, art["price"], mag_id)
        if url:
            from datetime import date
            done[art["id"]] = {"url": url, "price": art["price"],
                               "published_at": date.today().isoformat()}
            results.append((title, art["price"], url))
            save_json(NOTE_STATE, state)
            print(f"  ✅ [{art['price']:>4}¥] {title[:35]}")
            print(f"     {url}")
            time.sleep(3)

    print(f"\n  完了: {len(results)}本投稿")


# ──────────────────────────────────────────────────────────
# BOOTH 出品（Playwright）
# ──────────────────────────────────────────────────────────

BOOTH_PRODUCTS = [
    {
        "id": "vol1",
        "title": "フリーランス収支管理スプレッドシート【Googleスプレッドシート・確定申告対応】",
        "description": (
            "フリーランスの収入・経費・案件を1枚で管理できるExcelテンプレートです。\n\n"
            "【含まれるもの】\n"
            "・Excel ファイル（.xlsx）※Googleスプレッドシートでもそのまま使えます\n"
            "・4シート構成：収入 / 経費 / 案件管理 / 年間サマリー\n\n"
            "【できること】\n"
            "✅ 収入を入力すると月別・年間サマリーを自動生成\n"
            "✅ 案件ごとの実質時給を自動計算\n"
            "✅ 経費を科目別に自動集計\n"
            "✅ 確定申告の準備資料として活用できる\n\n"
            "【返金について】\nデジタルコンテンツの性質上、返金はお受けできません。"
        ),
        "price": 980,
        "file": "vol1_freelance_cashflow.xlsx",
    },
    {
        "id": "vol2",
        "title": "SNS投稿カレンダー【投稿テーマ50選付き・Googleスプレッドシート対応】",
        "description": (
            "Instagram・X・Facebook を一括管理できる月次カレンダーです。\n\n"
            "【含まれるもの】\n"
            "・Excel ファイル（.xlsx）※Googleスプレッドシート対応\n"
            "・2シート構成：月次カレンダー / 投稿テーマ50選\n\n"
            "【できること】\n"
            "✅ 月別カレンダーで投稿予定を管理\n"
            "✅ 複数SNSを一覧管理（Instagram/X/Facebook/TikTok）\n"
            "✅ 投稿テーマ50選でネタ切れ知らず\n\n"
            "【返金について】\nデジタルコンテンツの性質上、返金はお受けできません。"
        ),
        "price": 680,
        "file": "vol2_sns_calendar.xlsx",
    },
]


def run_booth():
    print("\n" + "━"*50)
    print("  [BOOTH] 商品出品（Playwright）")
    print("━"*50)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  playwright 未インストール: pip install playwright && playwright install chromium")
        return

    state = load_json(BOOTH_STATE, {"listed": {}})
    listed = state["listed"]

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        ctx = browser.new_context()
        page = ctx.new_page()

        # ログイン
        print("\n  BOOTHへアクセス中...")
        page.goto("https://manage.booth.pm/items/new")
        page.wait_for_timeout(3000)

        if "login" in page.url or "sign_in" in page.url:
            print("  Googleログインが必要です。ブラウザで許可してください。")
            page.wait_for_url("**/manage/**", timeout=120000)
            print("  ✅ ログイン完了")

        for product in BOOTH_PRODUCTS:
            if product["id"] in listed:
                print(f"  ⏭  スキップ（出品済み）: {product['id']}")
                continue

            dist_file = BOOTH_DIST / product["file"]
            if not dist_file.exists():
                print(f"  ⚠️  ファイルなし: {product['file']}")
                continue

            print(f"\n  出品中: {product['title'][:40]}…")
            try:
                page.goto("https://manage.booth.pm/items/new")
                page.wait_for_load_state("networkidle")

                page.fill('input[name="item[name]"]', product["title"])
                page.fill('textarea[name="item[description]"]', product["description"])
                page.fill('input[name="item[price]"]', str(product["price"]))

                file_input = page.query_selector('input[type="file"]')
                if file_input:
                    file_input.set_input_files(str(dist_file))
                    page.wait_for_timeout(2000)

                page.click('button[type="submit"], input[type="submit"]')
                page.wait_for_timeout(3000)

                url = page.url
                listed[product["id"]] = {"url": url, "price": product["price"]}
                save_json(BOOTH_STATE, state)
                print(f"  ✅ 出品完了: {url}")
                time.sleep(2)

            except Exception as e:
                print(f"  ❌ 出品失敗: {e}")

        browser.close()

    print(f"\n  完了: {len([p for p in BOOTH_PRODUCTS if p['id'] in listed])}件出品済み")


# ──────────────────────────────────────────────────────────
# エントリポイント
# ──────────────────────────────────────────────────────────

def main():
    load_env()
    parser = argparse.ArgumentParser(description="Mac専用・全プラットフォーム一括公開")
    parser.add_argument("--note",  action="store_true", help="noteのみ実行")
    parser.add_argument("--booth", action="store_true", help="BOOTHのみ実行")
    args = parser.parse_args()

    run_all = not args.note and not args.booth

    print("=" * 50)
    print("  mac_publish_all — 全プラットフォーム一括公開")
    print("=" * 50)

    if args.note or run_all:
        run_note()

    if args.booth or run_all:
        run_booth()

    print("\n" + "="*50)
    print("  全処理完了")
    print("="*50)


if __name__ == "__main__":
    main()
