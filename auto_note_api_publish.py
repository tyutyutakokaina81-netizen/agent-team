#!/usr/bin/env python3
"""
auto_note_api_publish.py — note.com API直接投稿
Playwright不要、requests のみで認証→マガジン作成→記事投稿
"""

import json
import os
import re
import sys
import time
from pathlib import Path

import requests

REPO = Path(__file__).parent
SESSIONS = REPO / ".sessions"
SESSIONS.mkdir(exist_ok=True)
STATE_FILE = SESSIONS / "note_publish_queue.json"

BASE_URL = "https://note.com"
API_BASE  = "https://note.com/api/v2"
API_V1    = "https://note.com/api/v1"


def load_env():
    env_file = REPO / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def login(session: requests.Session) -> str:
    """note.com にログインしてユーザー名を返す"""
    email    = os.environ["NOTE_EMAIL"]
    password = os.environ["NOTE_PASSWORD"]

    # CSRF トークン取得
    r = session.get(BASE_URL, timeout=15)
    csrf = ""
    m = re.search(r'"csrfToken"\s*:\s*"([^"]+)"', r.text)
    if m:
        csrf = m.group(1)
    m2 = re.search(r'name="csrf-token"\s+content="([^"]+)"', r.text)
    if m2:
        csrf = m2.group(1)

    headers = {"Content-Type": "application/json", "X-CSRFToken": csrf,
               "Origin": BASE_URL, "Referer": f"{BASE_URL}/login"}
    payload = {"login": email, "password": password}

    r2 = session.post(f"{API_V1}/sessions", json=payload, headers=headers, timeout=15)

    if r2.status_code not in (200, 201):
        print(f"  ❌ ログイン失敗: {r2.status_code}")
        print(f"     {r2.text[:300]}")
        return ""

    data = r2.json()
    user = data.get("data", {}).get("urlname", "") or data.get("data", {}).get("nickname", "")
    print(f"  ✅ ログイン成功: @{user}")
    return user


def create_magazine(session: requests.Session, urlname: str) -> str:
    """マガジンを作成して id を返す（既存があればそれを使う）"""
    name = "世界よ、これが高岡だ。——知られざる日本の宝石・高岡市 完全ガイド"
    description = (
        "日本人も素通りする、富山県高岡市。\n"
        "国宝3件・日本三大仏・400年続く鋳物と漆器・ドラえもんの生まれた町・"
        "海越しに立山連峰が見える絶景。\n\n"
        "「本物の日本」がここにある。\n\n"
        "全16記事をひとつに。保存版ガイドマガジンです。"
    )

    # 既存マガジン確認
    r = session.get(f"{API_V2_USER(urlname)}/magazines", timeout=15)
    if r.ok:
        for mag in r.json().get("data", {}).get("magazines", []):
            if name in mag.get("name", ""):
                print(f"  📖 既存マガジン使用: {mag['id']}")
                return str(mag["id"])

    payload = {"name": name, "description": description, "is_paid": True, "price": 4980}
    r2 = session.post(f"{API_V1}/magazines", json=payload, timeout=15)
    if r2.status_code in (200, 201):
        mag_id = str(r2.json().get("data", {}).get("id", ""))
        print(f"  ✅ マガジン作成: {mag_id}")
        return mag_id
    print(f"  ⚠️  マガジン作成失敗({r2.status_code}): {r2.text[:200]}")
    return ""


def API_V2_USER(urlname):
    return f"https://note.com/api/v2/creators/{urlname}"


def post_article(session: requests.Session, title: str, body: str,
                 price: int, magazine_id: str) -> str:
    """記事を投稿して note URL を返す"""
    payload = {
        "subject":      title,
        "body":         body,
        "status":       "published",
        "price":        price,
        "paid_type":    "free" if price == 0 else "partially_free",
        "magazine_ids": [magazine_id] if magazine_id else [],
        "hashtags":     ["高岡市", "富山観光", "北陸旅行", "HiddenJapan"],
    }
    r = session.post(f"{API_V1}/text_notes", json=payload, timeout=30)
    if r.status_code in (200, 201):
        note_data = r.json().get("data", {})
        key = note_data.get("key", "")
        urlname = note_data.get("user", {}).get("urlname", "")
        url = f"https://note.com/{urlname}/n/{key}"
        print(f"  ✅ 投稿: {title[:30]}… → {url}")
        return url
    print(f"  ❌ 投稿失敗({r.status_code}): {r.text[:300]}")
    return ""


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"published": {}}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


# ── 投稿する記事リスト ───────────────────────────────────────
ARTICLES = [
    {"id": "takaoka_intro",   "price": 0,   "file": "2026-04-28_高岡市観光_note記事.md"},
    {"id": "takaoka_map",     "price": 980,  "file": "2026-04-29_高岡観光_有料note記事.md"},
    {"id": "hokuriku_pass",   "price": 500,  "file": "2026-04-30_hokuriku_pass_note記事.md"},
    {"id": "budget_guide",    "price": 500,  "file": "2026-04-30_takaoka_budget_note記事.md"},
    {"id": "zuiryuji",        "price": 300,  "file": "2026-04-29_瑞龍寺_note記事.md"},
    {"id": "daibutsu",        "price": 300,  "file": "2026-04-29_高岡大仏_note記事.md"},
    {"id": "kanayamachi",     "price": 300,  "file": "2026-04-29_金屋町_note記事.md"},
    {"id": "amehare",         "price": 300,  "file": "2026-04-30_amehare_coast_note記事.md"},
    {"id": "doraemon",        "price": 300,  "file": "2026-04-30_doraemon_town_note記事.md"},
    {"id": "katsukoji",       "price": 300,  "file": "2026-04-30_katsukoji_note記事.md"},
    {"id": "manyo_tram",      "price": 300,  "file": "2026-04-30_manyo_tram_note記事.md"},
    {"id": "nousaku",         "price": 300,  "file": "2026-04-30_nousaku_craft_note記事.md"},
    {"id": "lacquer",         "price": 300,  "file": "2026-04-30_takaoka_lacquer_note記事.md"},
    {"id": "inami_wood",      "price": 300,  "file": "2026-04-30_inami_wood_note記事.md"},
    {"id": "kanaya_morning",  "price": 300,  "file": "2026-04-30_kanaya_morning_note記事.md"},
    {"id": "tofu_shop",       "price": 300,  "file": "2026-04-24_奥とうふ店_note記事.md"},
]


def extract_title(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return "高岡観光ガイド"


def run():
    load_env()
    print("━" * 50)
    print("  note 自動投稿")
    print("━" * 50)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
        "Accept": "application/json",
    })

    urlname = login(session)
    if not urlname:
        sys.exit(1)

    print("\n  マガジン準備中...")
    magazine_id = create_magazine(session, urlname)

    state = load_state()
    published = state["published"]

    cmo_out = REPO / "CMO" / "outputs"
    results = []

    print(f"\n  記事投稿開始（{len(ARTICLES)}本）\n")
    for art in ARTICLES:
        if art["id"] in published:
            print(f"  ⏭️  スキップ（投稿済み）: {art['id']}")
            continue

        fpath = cmo_out / art["file"]
        if not fpath.exists():
            print(f"  ⚠️  ファイルなし: {art['file']}")
            continue

        body = fpath.read_text(encoding="utf-8")
        title = extract_title(body)

        # 無料記事の末尾にマガジン誘導を追加
        if art["price"] == 0:
            body += (
                "\n\n---\n\n"
                "**▼ 各スポットの詳細ガイド・モデルコース・予算別プランはマガジンで**\n\n"
                "👉 高岡市 完全ガイドマガジン（¥4,980）\n\n"
                "#高岡市 #富山観光 #北陸旅行 #HiddenJapan #日本三大仏 #瑞龍寺 #金屋町"
            )

        url = post_article(session, title, body, art["price"], magazine_id)
        if url:
            published[art["id"]] = {"url": url, "price": art["price"], "published_at": __import__("datetime").date.today().isoformat()}
            results.append((title, art["price"], url))
            save_state(state)
            time.sleep(2)  # rate limit 対策

    print(f"\n{'━'*50}")
    print(f"  完了: {len(results)}本投稿")
    for title, price, url in results:
        tag = "無料" if price == 0 else f"¥{price:,}"
        print(f"  [{tag}] {title[:35]}…")
        print(f"         {url}")
    print("━" * 50)


if __name__ == "__main__":
    run()
