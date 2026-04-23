#!/usr/bin/env python3
"""
auto_d_apply.py — CW案件 5件を完全自動応募（ユーザー介入不要）

前提:
  pip install playwright && playwright install chromium
  .sessions/crowdworks_session.json が存在すること
  （初回: projects/.../pipeline/00_session_setup.py でログイン保存）
"""

import json
import time
import sys
from pathlib import Path

PIPELINE_DIR = Path(__file__).parent / "projects/2026-04-08_月30万自動化/D_エクセル入力スクレイピング"
SESSION_FILE = PIPELINE_DIR / ".sessions" / "crowdworks_session.json"

JOBS = [
    {
        "id": "A1",
        "title": "【100%採用】データ入力業務",
        "url": "https://crowdworks.jp/public/jobs/12876568",
        "text": """はじめまして。
データ入力業務で応募いたします。

ご提示の条件で問題なく対応可能です。
・指示通りの正確な作業
・ダブルチェックによるミス防止
・納期厳守・迅速な連絡対応

平日3〜5時間、土日も対応可能です。
ご指示いただければすぐに作業開始いたします。

よろしくお願いいたします。""",
    },
    {
        "id": "A2",
        "title": "ポータルサイトへの店舗入力作業",
        "url": "https://crowdworks.jp/public/jobs/13059624",
        "text": """はじめまして。
ポータルサイトへの店舗情報入力のご案件に応募いたします。

店舗データの入力作業は得意分野で、類似案件にも対応経験があります。

■ 対応スタンス
・マニュアル通りの正確な作業
・表記ゆれ・入力漏れの徹底防止
・ダブルチェックによる品質確保

平日3〜5時間確保可能で、納期厳守いたします。
ご指示いただければすぐに作業開始いたします。

よろしくお願いいたします。""",
    },
    {
        "id": "A3",
        "title": "月初3日間限定・画像情報を文字起こし",
        "url": "https://crowdworks.jp/public/jobs/12965543",
        "text": """はじめまして。
月初限定の画像→テキスト化業務に応募いたします。

画像からの文字起こし、データ入力は得意分野です。
正確性とスピードを両立できます。

■ 稼働
月初3日間は優先的に時間確保可能です。
専用システムの操作もすぐ習熟できます。

■ 強み
・ダブルチェックによるミス防止
・納期厳守
・迅速な連絡対応

ご指示いただければすぐに作業開始いたします。
よろしくお願いいたします。""",
    },
    {
        "id": "A4",
        "title": "繁忙期・好きな時間にできる簡単データ入力",
        "url": "https://crowdworks.jp/public/jobs/12876562",
        "text": """はじめまして。
繁忙期のデータ入力スタッフとして応募いたします。

■ 稼働時間の自由度
平日3〜5時間、土日も対応可能。
繁忙期はさらに時間確保できます。

■ 対応範囲
・Excel・Googleスプレッドシートでの入力
・ダブルチェックによる精度確保
・納期前倒し納品を心がけ

即日対応可能です。
ご指示いただければすぐに作業開始いたします。

よろしくお願いいたします。""",
    },
    {
        "id": "A5",
        "title": "スマートフォンを用いた事務作業",
        "url": "https://crowdworks.jp/public/jobs/12529225",
        "text": """はじめまして。
スマートフォンを用いた事務作業に応募いたします。

■ 対応可能
・スマホ操作に慣れており、スキマ時間活用可能
・事務作業（入力・確認・コピペ）の経験あり
・マニュアル通りの正確な作業

■ 稼働
平日3〜5時間、土日対応可能。
即レス（数時間以内）を心がけております。

ご指示いただければすぐに作業開始いたします。
よろしくお願いいたします。""",
    },
]


def _submit(page, job: dict) -> bool:
    page.goto(job["url"], wait_until="networkidle", timeout=30000)
    time.sleep(2)

    # 応募ボタン
    clicked = False
    for sel in [
        "a.btn-apply",
        "a[href*='apply']",
        "a:has-text('応募する')",
        "button:has-text('応募する')",
    ]:
        btn = page.query_selector(sel)
        if btn:
            btn.click()
            time.sleep(2)
            clicked = True
            break
    if not clicked:
        return False

    # 応募文テキストエリア
    filled = False
    for sel in [
        "textarea[name*='body']",
        "#job_offer_apply_body",
        "#body",
        "textarea.apply-body",
        "textarea",
    ]:
        ta = page.query_selector(sel)
        if ta:
            ta.fill(job["text"])
            time.sleep(0.5)
            filled = True
            break
    if not filled:
        return False

    # 送信ボタン
    for sel in [
        "input[type='submit']",
        "button[type='submit']",
        "button:has-text('送信')",
        "input[value*='送信']",
        "button:has-text('応募')",
    ]:
        btn = page.query_selector(sel)
        if btn:
            btn.click()
            time.sleep(3)
            return True
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
    print("  CW 5件 完全自動応募")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    done = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=300)
        ctx = browser.new_context(
            storage_state=storage,
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        )
        page = ctx.new_page()

        for job in JOBS:
            print(f"\n[{job['id']}] {job['title'][:45]}...")
            try:
                ok = _submit(page, job)
                if ok:
                    done.append(job["id"])
                    print(f"  ✅ 応募完了")
                else:
                    print(f"  ❌ セレクタ不一致（手動確認: {job['url']}）")
            except Exception as e:
                print(f"  ❌ エラー: {e}")
            time.sleep(5)  # BANリスク軽減

        # セッション更新
        ctx.storage_state(path=str(SESSION_FILE))
        browser.close()

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  完了: {len(done)}/5件 {done}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    run()
