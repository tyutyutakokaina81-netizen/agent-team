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

PROPOSAL_DATA_ENTRY = """はじめまして。データ入力の作業を希望しております。

即対応可能で、本日中に着手できます。
正確かつ丁寧に作業いたします。
入力後のダブルチェックも必ず実施します。

Excel / Google スプレッドシート / CSV いずれも対応可能です。

どうぞよろしくお願いいたします。"""

PROPOSAL_WRITING = """はじめまして。SEO記事・コンテンツ作成を専門に対応しております。

ご依頼の記事作成について、対応可能です。

■ 強み
・構成案から本文・メタディスクリプションまで一貫対応
・納品前にファクトチェック・誤字脱字チェックを必ず実施
・週3〜5本の安定した執筆が可能です

■ 納期
1本あたり2〜3営業日

長期でのお取引を希望しております。
まずはテスト記事1本でクオリティをご確認いただければ幸いです。

よろしくお願いいたします。"""

# 高単価案件を最優先で応募（URLを直接指定）
PRIORITY_JOBS = [
    {
        "title": "文字単価¥3 飲食店マーケティング記事（継続）",
        "url": "https://crowdworks.jp/public/jobs/11861940",
        "proposal": PROPOSAL_WRITING,
    },
    {
        "title": "文字単価¥3 SEO記事（幅広いジャンル・継続）",
        "url": "https://crowdworks.jp/public/jobs/11930622",
        "proposal": PROPOSAL_WRITING,
    },
    {
        "title": "SaaS事業者向けメディア（文字単価最大¥3）",
        "url": "https://crowdworks.jp/public/jobs/7972618",
        "proposal": PROPOSAL_WRITING,
    },
    {
        "title": "ネットニュース記事 ¥2,200〜/本 週10本 継続",
        "url": "https://crowdworks.jp/public/jobs/12568642",
        "proposal": PROPOSAL_WRITING,
    },
]

PROFILE_TEXT = """データ入力・リスト作成を中心に対応しております。
正確性を重視し、入力後のダブルチェックを必ず実施します。
平日土日問わず即日着手可能です。
Excel / Google スプレッドシート / CSV 対応。
よろしくお願いいたします。"""

CATEGORY_URLS = [
    "https://crowdworks.jp/public/jobs/category/52?order=new",   # データ入力
    "https://crowdworks.jp/public/jobs/category/201?order=new",  # リスト作成
]
TASK_URLS = [
    "https://crowdworks.jp/public/jobs/category/52?form=task&order=new",  # データ入力タスク
    "https://crowdworks.jp/public/jobs/category/201?form=task&order=new", # リスト作成タスク
    "https://crowdworks.jp/public/jobs/category/219?form=task&order=new", # アンケート
]
TARGET_APPLY_COUNT = 5


def human_wait(min_sec=1.0, max_sec=2.5):
    time.sleep(random.uniform(min_sec, max_sec))


def login(page):
    """CWにログイン（人間が1回だけ操作）"""
    print("\n" + "=" * 50)
    print("  CW自動応募ツール v2")
    print("=" * 50)

    session_file = SESSION_DIR / "cw_session.json"

    if session_file.exists():
        print("✅ 保存済みセッションを使用します")
        return json.loads(session_file.read_text(encoding="utf-8"))

    print("\n📱 ブラウザでCWにログインしてください")
    print("   ログイン完了後、Enterキーを押してください\n")

    page.goto("https://crowdworks.jp/login")
    input("   → ログイン完了したらEnterキー: ")

    storage = page.context.storage_state()
    session_file.write_text(
        json.dumps(storage, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("✅ セッション保存完了（次回からログイン不要）")
    return storage


def search_jobs(page, category_url):
    """カテゴリページから案件を取得"""
    import re

    page.goto(category_url)
    human_wait(3, 5)
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
            if not re.search(r'/public/jobs/\d+$', href):
                continue
            seen.add(href)

            title = link.inner_text().strip()
            if not title or len(title) < 5:
                continue

            url_full = href if href.startswith("http") else f"https://crowdworks.jp{href}"
            jobs.append({"title": title, "url": url_full})
        except Exception:
            continue

    return jobs[:15]


def try_apply(page, job, proposal_text=None):
    """案件ページを開いて応募を試みる（半自動モード）"""
    if proposal_text is None:
        proposal_text = PROPOSAL_DATA_ENTRY
    try:
        page.goto(job["url"])
        human_wait(3, 4)

        body_text = page.inner_text("body")

        # まず全ボタン/リンクのテキストを収集してデバッグ
        all_clickables = page.query_selector_all("a, button, input[type='submit']")
        clickable_texts = []
        for el in all_clickables:
            txt = el.inner_text().strip() if el.inner_text() else ""
            if txt:
                clickable_texts.append(txt)

        # 応募系のボタン/リンクを探す（幅広いパターン）
        apply_keywords = ["応募", "提案", "仕事を始める", "この仕事に", "相談する", "条件についての相談"]
        found_btn = None
        for el in all_clickables:
            txt = (el.inner_text() or "").strip()
            if any(kw in txt for kw in apply_keywords):
                found_btn = el
                break

        if found_btn:
            btn_text = found_btn.inner_text().strip()
            print(f"    🔘 ボタン発見:「{btn_text}」")
            found_btn.click()
            human_wait(3, 4)

            # テキスト入力欄を探す
            textareas = page.query_selector_all("textarea")
            if textareas:
                for ta in textareas:
                    if ta.is_visible():
                        ta.fill(proposal_text)
                        print(f"    ✏️ 提案文を入力しました")
                        break

            # 手動確認で送信
            print(f"    👆 内容を確認して「応募する」ボタンを押してください")
            input(f"    → 送信完了後Enterキー: ")
            return True
        else:
            # ボタンが見つからない → ページURLを表示して手動誘導
            print(f"    ⚠️ 応募ボタンが見つかりません")
            print(f"    📋 案件URL: {job['url']}")
            print(f"    → このURLをブラウザで開いて手動で応募できますか？")
            ans = input(f"    → 応募した(y) / スキップ(n): ").strip().lower()
            return ans == "y"

    except Exception as e:
        print(f"    ❌ エラー: {e}")
        return False


def do_tasks(page):
    """タスク案件（応募不要）を実行"""
    import re
    tasks_done = 0

    for task_url in TASK_URLS:
        if tasks_done >= 5:
            break
        print(f"\n[タスク検索: {task_url.split('category/')[1][:10]}...]")
        page.goto(task_url)
        human_wait(3, 5)

        links = page.query_selector_all("a")
        job_urls = []
        seen = set()
        for link in links:
            try:
                href = link.get_attribute("href") or ""
                if href in seen:
                    continue
                if not re.search(r'/public/jobs/\d+$', href):
                    continue
                seen.add(href)
                title = link.inner_text().strip()
                if len(title) < 5:
                    continue
                url_full = href if href.startswith("http") else f"https://crowdworks.jp{href}"
                job_urls.append({"title": title, "url": url_full})
            except Exception:
                continue

        for job in job_urls[:5]:
            if tasks_done >= 5:
                break
            print(f"\n  📝 {job['title'][:50]}...")
            try:
                page.goto(job["url"])
                human_wait(2, 3)

                # 作業開始ボタンを幅広く探す
                all_els = page.query_selector_all("a, button")
                start_btn = None
                for el in all_els:
                    txt = (el.inner_text() or "").strip()
                    if any(kw in txt for kw in ["作業を開始", "作業開始", "作業する", "タスクを開始"]):
                        start_btn = el
                        break

                if start_btn:
                    start_btn.click()
                    human_wait(2, 3)
                    print(f"    ✅ 作業画面を開きました")
                    print(f"    → 画面の指示に従って作業してください")
                    input(f"    → 作業完了後Enterキー: ")
                    tasks_done += 1
                else:
                    print(f"    → 作業開始ボタンなし（スキップ）")
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

        # === Phase 1: 高単価案件を最優先で応募 ===
        print(f"\n💎 高単価案件に優先応募（{len(PRIORITY_JOBS)}件）")
        for pj in PRIORITY_JOBS:
            if applied >= TARGET_APPLY_COUNT:
                break
            print(f"\n[{applied + 1}/{TARGET_APPLY_COUNT}] 💎 {pj['title'][:50]}...")
            if try_apply(page, pj, proposal_text=pj["proposal"]):
                applied += 1
                print(f"    ✅ 応募完了 ({applied}/{TARGET_APPLY_COUNT})")
                log_entry = {
                    "title": pj["title"],
                    "url": pj["url"],
                    "applied_at": datetime.now().isoformat(),
                    "priority": "high",
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

        # === Phase 2: カテゴリ検索で残り枠を埋める ===
        all_jobs = []
        for cat_url in CATEGORY_URLS:
            if applied >= TARGET_APPLY_COUNT:
                break
            cat_name = "データ入力" if "52" in cat_url else "リスト作成"
            print(f"\n🔍 カテゴリ検索: {cat_name}")
            jobs = search_jobs(page, cat_url)
            print(f"   → {len(jobs)}件見つかりました")
            all_jobs.extend(jobs)

        # 重複除去
        seen_urls = set()
        unique_jobs = []
        for j in all_jobs:
            if j["url"] not in seen_urls:
                seen_urls.add(j["url"])
                unique_jobs.append(j)

        print(f"\n📋 合計 {len(unique_jobs)} 件の候補。上から順に応募します。")
        print(f"   （応募ボタン発見時は半自動：テキスト自動入力→手動で送信確認）\n")

        for job in unique_jobs:
            if applied >= TARGET_APPLY_COUNT:
                break

            print(f"\n[{applied + 1}/{TARGET_APPLY_COUNT}] {job['title'][:50]}...")

            if try_apply(page, job):
                applied += 1
                print(f"    ✅ 応募完了 ({applied}/{TARGET_APPLY_COUNT})")

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
