"""
auto_apply.py — CW自動応募スクリプト

【使い方】（オーナーのPCで実行）

  1. pip install playwright
  2. playwright install chromium
  3. python auto_apply.py

  → ブラウザが開く → Googleでログイン → Enterキー
  → 以降、自動で案件検索 → 自動応募5件

【所要時間】
  - 人間：ログイン1分
  - AI：検索＋応募5分
"""

import json
import time
import random
import sys
from pathlib import Path
from datetime import datetime

SESSION_DIR = Path(__file__).parent / ".sessions"
SESSION_DIR.mkdir(exist_ok=True)
OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

PROPOSAL_TEXT = """はじめまして。データ入力の作業を希望しております。

即対応可能で、本日中に着手できます。
正確かつ丁寧に作業いたします。
入力後のダブルチェックも必ず実施します。

Excel / Google スプレッドシート / CSV いずれも対応可能です。

どうぞよろしくお願いいたします。"""

PROFILE_TEXT = """データ入力・リスト作成を中心に対応しております。
正確性を重視し、入力後のダブルチェックを必ず実施します。
平日土日問わず即日着手可能です。
Excel / Google スプレッドシート / CSV 対応。
よろしくお願いいたします。"""

SEARCH_KEYWORDS = ["データ入力", "リスト作成", "簡単作業"]
TARGET_APPLY_COUNT = 5


def human_wait(min_sec=1.0, max_sec=2.5):
    time.sleep(random.uniform(min_sec, max_sec))


def login(page):
    """CWにログイン（人間が1回だけ操作）"""
    print("\n" + "=" * 50)
    print("  CW自動応募ツール")
    print("=" * 50)

    session_file = SESSION_DIR / "cw_session.json"

    if session_file.exists():
        print("✅ 保存済みセッションを使用します")
        return json.loads(session_file.read_text(encoding="utf-8"))

    print("\n📱 ブラウザでCWにログインしてください")
    print("   ログイン完了後、Enterキーを押してください\n")

    page.goto("https://crowdworks.jp/login")
    input("   → ログイン完了したらEnterキー: ")

    # セッション保存
    storage = page.context.storage_state()
    session_file.write_text(
        json.dumps(storage, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("✅ セッション保存完了（次回からログイン不要）")
    return storage


def search_jobs(page, keyword):
    """案件を検索して一覧を取得"""
    import urllib.parse
    import re

    encoded = urllib.parse.quote(keyword)
    url = f"https://crowdworks.jp/public/jobs/search?order=new&keyword={encoded}"
    page.goto(url)
    human_wait(2, 4)

    # スクロール
    page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
    human_wait(1, 2)

    jobs = []
    links = page.query_selector_all("a")
    seen = set()

    for link in links:
        try:
            href = link.get_attribute("href") or ""
            if not href or href in seen:
                continue
            if not re.search(r'/public/jobs/\d+', href):
                continue
            if 'search' in href or 'category' in href:
                continue
            seen.add(href)

            title = link.inner_text().strip()
            if not title or len(title) < 5:
                continue

            url_full = href if href.startswith("http") else f"https://crowdworks.jp{href}"
            jobs.append({"title": title, "url": url_full})
        except Exception:
            continue

    return jobs[:20]


def check_job_detail(page, job):
    """案件詳細を確認して応募可能か判定"""
    try:
        page.goto(job["url"])
        human_wait(2, 3)

        text = page.inner_text("body").lower()

        # 応募ボタンがあるか
        apply_btn = page.query_selector(
            "a[href*='apply'], button:has-text('応募'), a:has-text('応募する'), "
            "a:has-text('この仕事に応募する')"
        )

        if not apply_btn:
            return None, None

        # 初心者歓迎チェック
        beginner_friendly = any(k in text for k in [
            "初心者", "未経験", "簡単", "誰でも", "歓迎"
        ])

        return apply_btn, beginner_friendly
    except Exception:
        return None, None


def apply_to_job(page, job, apply_btn):
    """案件に応募する"""
    try:
        apply_btn.click()
        human_wait(2, 3)

        # 提案文入力欄を探す
        textarea = page.query_selector(
            "textarea[name*='description'], textarea[name*='message'], "
            "textarea[name*='proposal'], textarea.c-textarea, textarea"
        )

        if textarea:
            textarea.fill("")
            human_wait(0.5, 1)
            textarea.fill(PROPOSAL_TEXT)
            human_wait(1, 2)

            # 送信ボタン
            submit = page.query_selector(
                "button[type='submit'], input[type='submit'], "
                "button:has-text('応募する'), button:has-text('送信')"
            )

            if submit:
                print(f"    📤 応募送信中...")
                submit.click()
                human_wait(3, 5)
                return True
            else:
                print(f"    ⚠️ 送信ボタンが見つかりません（手動で送信してください）")
                input("    → 手動送信後Enterキー: ")
                return True

        else:
            print(f"    ⚠️ テキスト欄が見つかりません（手動で入力してください）")
            input("    → 手動入力・送信後Enterキー: ")
            return True

    except Exception as e:
        print(f"    ❌ 応募エラー: {e}")
        return False


def do_tasks(page):
    """タスク案件（応募不要）を実行"""
    print("\n[タスク案件を検索中...]")
    page.goto("https://crowdworks.jp/public/jobs?category=jobs&form=task&order=new")
    human_wait(2, 4)

    task_links = page.query_selector_all("a")
    tasks_done = 0

    for link in task_links:
        if tasks_done >= 3:
            break
        try:
            href = link.get_attribute("href") or ""
            if "/public/jobs/" not in href or "search" in href:
                continue
            title = link.inner_text().strip()
            if len(title) < 5:
                continue

            print(f"\n  タスク: {title[:40]}...")
            # タスクページを開く（ただし実行は手動）
            url = href if href.startswith("http") else f"https://crowdworks.jp{href}"
            page.goto(url)
            human_wait(2, 3)

            # 作業開始ボタンを探す
            start_btn = page.query_selector(
                "a:has-text('作業を開始'), button:has-text('作業を開始'), "
                "a:has-text('作業開始')"
            )
            if start_btn:
                start_btn.click()
                human_wait(2, 3)
                print(f"    ✅ 作業画面を開きました")
                print(f"    → 画面の指示に従って作業してください")
                input(f"    → 作業完了後Enterキー: ")
                tasks_done += 1
        except Exception:
            continue

    print(f"\n[タスク完了: {tasks_done}件]")
    return tasks_done


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ Playwright未インストール")
        print("   pip install playwright && playwright install chromium")
        sys.exit(1)

    with sync_playwright() as p:
        # セッション確認
        session_file = SESSION_DIR / "cw_session.json"
        storage = None
        if session_file.exists():
            storage = json.loads(session_file.read_text(encoding="utf-8"))

        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context_args = {
            "viewport": {"width": 1280, "height": 800},
            "user_agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }
        if storage:
            context_args["storage_state"] = storage

        context = browser.new_context(**context_args)
        page = context.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        # ログイン
        if not storage:
            login(page)
            # セッション再読み込み
            context.close()
            storage = json.loads(session_file.read_text(encoding="utf-8"))
            context = browser.new_context(**{**context_args, "storage_state": storage})
            page = context.new_page()
            page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

        # 応募フェーズ
        applied = 0
        all_jobs = []

        for kw in SEARCH_KEYWORDS:
            if applied >= TARGET_APPLY_COUNT:
                break
            print(f"\n🔍 検索: 「{kw}」")
            jobs = search_jobs(page, kw)
            print(f"   → {len(jobs)}件見つかりました")
            all_jobs.extend(jobs)

        print(f"\n📋 合計 {len(all_jobs)} 件の候補。上から順に応募します。")

        for job in all_jobs:
            if applied >= TARGET_APPLY_COUNT:
                break

            print(f"\n[{applied + 1}/{TARGET_APPLY_COUNT}] {job['title'][:50]}...")
            apply_btn, beginner_ok = check_job_detail(page, job)

            if not apply_btn:
                print("    → 応募ボタンなし（スキップ）")
                continue

            if apply_to_job(page, job, apply_btn):
                applied += 1
                print(f"    ✅ 応募完了 ({applied}/{TARGET_APPLY_COUNT})")

                # ログ記録
                log_entry = {
                    "title": job["title"],
                    "url": job["url"],
                    "applied_at": datetime.now().isoformat(),
                }
                log_file = OUTPUT_DIR / "apply_log.json"
                logs = []
                if log_file.exists():
                    logs = json.loads(log_file.read_text(encoding="utf-8"))
                logs.append(log_entry)
                log_file.write_text(
                    json.dumps(logs, ensure_ascii=False, indent=2), encoding="utf-8"
                )

            human_wait(3, 5)

        # タスクフェーズ
        tasks_done = do_tasks(page)

        # 完了サマリ
        print("\n" + "=" * 50)
        print(f"  ✅ 完了")
        print(f"  応募: {applied}件")
        print(f"  タスク: {tasks_done}件")
        print("=" * 50)
        print(f"\n次のステップ:")
        print(f"  → 採用通知が来たら作業指示をAIに渡す")
        print(f"  → AIが作業を100%実行")
        print(f"  → 納品ボタンを押すだけ")

        input("\n終了するにはEnterキー: ")
        browser.close()


if __name__ == "__main__":
    main()
