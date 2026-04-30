#!/usr/bin/env python3
"""
auto_job_apply.py — 案件全自動サーチ＋応募（Mac/Playwright版）

1. CrowdWorks/Lancers を Playwright でスクレイピング（Chromeセッション使用）
2. ルールベースで GO/CAUTION/NO-GO を判定
3. GO かつ score≥80 の案件に自動応募（1日最大5件）
4. 応募済みログで重複防止

実行: python3 auto_job_apply.py
（Chromeで crowdworks.jp・lancers.jp にログイン済みであること）
"""

import json
import re
import sys
import time
from datetime import date, datetime
from pathlib import Path

REPO = Path(__file__).parent
PIPELINE = REPO / "projects" / "2026-04-08_月30万自動化" / "D_エクセル入力スクレイピング" / "pipeline"
OUTPUT_DIR = REPO / "projects" / "2026-04-08_月30万自動化" / "D_エクセル入力スクレイピング" / "outputs"
SESSIONS = REPO / ".sessions"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

APPLY_LOG = SESSIONS / "applied_jobs.json"
TODAY = date.today().isoformat()
MAX_APPLY_PER_DAY = 5
AUTO_APPLY_THRESHOLD = 50  # CAUTION以上（score≥50）も応募対象

KEYWORDS = ["データ入力", "エクセル入力", "スクレイピング", "データ収集", "CSV作成"]


# ─── ブラウザ起動 ──────────────────────────────────────────────

def launch_page(pw):
    """Chromeの保存済みセッションを使う"""
    import tempfile, shutil

    chrome_paths = [
        Path.home() / "Library/Application Support/Google/Chrome",
        Path.home() / ".config/google-chrome",
        Path.home() / "AppData/Local/Google/Chrome/User Data",
    ]
    user_data = next((p for p in chrome_paths if p.exists()), None)

    if user_data:
        tmp = Path(tempfile.mkdtemp()) / "chrome_copy"
        # ソケット・ロックファイルは除外してコピー
        skip = {"SingletonSocket", "SingletonLock", "SingletonCookie",
                "RunningChromeVersion", "lockfile"}
        shutil.copytree(
            user_data, tmp, dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(*skip),
        )
        browser = pw.chromium.launch_persistent_context(
            str(tmp), headless=True,
            args=["--disable-blink-features=AutomationControlled",
                  "--no-first-run", "--no-default-browser-check"],
        )
        page = browser.new_page()
    else:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

    page.set_extra_http_headers({"Accept-Language": "ja,en;q=0.9"})
    return browser, page


# ─── 案件検索 ─────────────────────────────────────────────────

def search_crowdworks(page, keyword: str) -> list[dict]:
    import urllib.parse
    enc = urllib.parse.quote(keyword)
    url = f"https://crowdworks.jp/public/jobs/search?order=new&keyword={enc}"
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        time.sleep(2)
    except Exception:
        return []

    jobs = []
    seen = set()
    for a in page.query_selector_all("a[href*='/public/jobs/']"):
        try:
            href = a.get_attribute("href") or ""
            m = re.search(r'/public/jobs/(\d+)', href)
            if not m or m.group(1) in seen:
                continue
            seen.add(m.group(1))
            title = a.inner_text().strip()
            if not title or len(title) < 5:
                continue
            full_url = href if href.startswith("http") else f"https://crowdworks.jp{href}"
            jobs.append({
                "id": m.group(1), "title": title,
                "url": full_url, "platform": "crowdworks",
                "keyword": keyword, "budget_text": "",
                "found_at": datetime.now().isoformat(),
            })
        except Exception:
            continue
    return jobs[:8]


def search_lancers(page, keyword: str) -> list[dict]:
    import urllib.parse
    enc = urllib.parse.quote(keyword)
    url = f"https://www.lancers.jp/work/search?keyword={enc}&open=1&sort=new"
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        time.sleep(2)
    except Exception:
        return []

    jobs = []
    seen = set()
    for a in page.query_selector_all("a[href*='/work/detail/']"):
        try:
            href = a.get_attribute("href") or ""
            m = re.search(r'/work/detail/(\d+)', href)
            if not m or m.group(1) in seen:
                continue
            seen.add(m.group(1))
            title = a.inner_text().strip()
            if not title or len(title) < 5:
                continue
            full_url = href if href.startswith("http") else f"https://www.lancers.jp{href}"
            jobs.append({
                "id": f"l{m.group(1)}", "title": title,
                "url": full_url, "platform": "lancers",
                "keyword": keyword, "budget_text": "",
                "found_at": datetime.now().isoformat(),
            })
        except Exception:
            continue
    return jobs[:8]


def search_all(page) -> list[dict]:
    all_jobs = []
    seen = set()
    for kw in KEYWORDS:
        print(f"  [{kw}] CrowdWorks...", end=" ", flush=True)
        jobs = search_crowdworks(page, kw)
        new = [j for j in jobs if j["id"] not in seen]
        for j in new:
            seen.add(j["id"])
            all_jobs.append(j)
        print(f"{len(new)}件", end="  ")

        print(f"Lancers...", end=" ", flush=True)
        jobs2 = search_lancers(page, kw)
        new2 = [j for j in jobs2 if j["id"] not in seen]
        for j in new2:
            seen.add(j["id"])
            all_jobs.append(j)
        print(f"{len(new2)}件")
        time.sleep(1)
    return all_jobs


# ─── 評価 ─────────────────────────────────────────────────────

def evaluate(job: dict) -> dict:
    text = (job.get("title", "") + " " + job.get("budget_text", "")).lower()

    tech = 10
    if any(k in text for k in ["エクセル", "excel", "csv", "データ入力"]):
        tech = 25
    elif any(k in text for k in ["スクレイピング", "データ収集"]):
        tech = 20
    if any(k in text for k in ["captcha", "ログイン必須"]):
        tech = max(tech - 10, 5)

    legal = 20
    if any(k in text for k in ["個人情報", "住所収集"]):
        legal = 5

    amounts = re.findall(r'(\d[\d,]+)', job.get("budget_text", ""))
    max_amt = max([int(a.replace(",", "")) for a in amounts
                   if int(a.replace(",", "")) > 100], default=0)
    profitability = 25 if max_amt >= 10000 else (20 if max_amt >= 5000 else (10 if max_amt >= 2000 else 8))
    estimated_price = max_amt or 5000

    clarity = 15
    total = tech + legal + profitability + clarity

    red_flags = []
    if any(k in text for k in ["海外在住", "受け取り代行", "転送", "送金"]):
        red_flags.append("詐欺の疑い")
        total = 0

    verdict = "GO" if total >= 70 else ("CAUTION" if total >= 50 else "NO-GO")
    return {
        **job,
        "scores": {"technical": tech, "legal": legal,
                   "profitability": profitability, "clarity": clarity},
        "total": total, "verdict": verdict,
        "estimated_price_jpy": estimated_price,
        "red_flags": red_flags,
        "evaluated_at": datetime.now().isoformat(),
    }


# ─── 応募文 ────────────────────────────────────────────────────

def make_application(job: dict) -> str:
    title = job.get("title", "")
    text = title.lower()
    if "スクレイピング" in text or "データ収集" in text:
        skill = "PythonによるWebスクレイピング・データ収集"
        method = "対象サイトの構造を事前に確認し、正確にデータを収集いたします。"
    elif any(k in text for k in ["エクセル", "excel", "csv"]):
        skill = "Excel・Pythonを使ったデータ処理・入力作業"
        method = "入力後に必ずダブルチェックを行い、正確な成果物をお届けします。"
    else:
        skill = "データ入力・収集作業"
        method = "丁寧・正確に対応いたします。"
    return f"""はじめまして。{skill}を得意としております。

ご依頼の内容を拝見しました。{method}

納期は厳守いたします。作業前に不明点があれば必ず確認してから進めますので、安心してお任せください。ぜひご検討のほどよろしくお願いいたします。"""


# ─── 自動応募 ─────────────────────────────────────────────────

def load_apply_log() -> dict:
    if APPLY_LOG.exists():
        return json.loads(APPLY_LOG.read_text())
    return {"applied": {}}


def save_apply_log(log: dict):
    APPLY_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2))


def applied_today_count(log: dict) -> int:
    return sum(1 for v in log["applied"].values()
               if v.get("applied_at", "").startswith(TODAY))


def auto_apply_crowdworks(page, job: dict, text: str) -> bool:
    try:
        page.goto(job["url"], wait_until="domcontentloaded", timeout=20000)
        time.sleep(2)
        # 応募ボタン
        for sel in ["a:has-text('応募する')", "button:has-text('応募する')",
                    "a.btn-apply", ".job-apply-btn"]:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click()
                time.sleep(2)
                break
        # テキストエリア
        for sel in ["textarea[name*='body']", "#job_offer_apply_body", "textarea"]:
            ta = page.query_selector(sel)
            if ta and ta.is_visible():
                ta.fill(text)
                time.sleep(0.5)
                break
        else:
            return False
        # 送信
        for sel in ["input[type='submit']", "button[type='submit']",
                    "button:has-text('送信')", "button:has-text('応募')"]:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click()
                time.sleep(3)
                return True
        return False
    except Exception as e:
        print(f"  [apply error] {e}")
        return False


def auto_apply_lancers(page, job: dict, text: str) -> bool:
    try:
        page.goto(job["url"], wait_until="domcontentloaded", timeout=20000)
        time.sleep(2)
        for sel in ["a:has-text('提案する')", "button:has-text('提案する')",
                    ".btn-proposal"]:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click()
                time.sleep(2)
                break
        for sel in ["textarea[name*='message']", "textarea[name*='body']", "textarea"]:
            ta = page.query_selector(sel)
            if ta and ta.is_visible():
                ta.fill(text)
                time.sleep(0.5)
                break
        else:
            return False
        for sel in ["button[type='submit']", "input[type='submit']",
                    "button:has-text('提案')", "button:has-text('送信')"]:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click()
                time.sleep(3)
                return True
        return False
    except Exception as e:
        print(f"  [apply error] {e}")
        return False


# ─── メイン ──────────────────────────────────────────────────

def run():
    print("━" * 50)
    print("  案件全自動サーチ＆応募")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("━" * 50)

    apply_log = load_apply_log()
    today_count = applied_today_count(apply_log)
    remaining = MAX_APPLY_PER_DAY - today_count
    print(f"  本日応募済: {today_count}件 / 上限: {MAX_APPLY_PER_DAY}件 / 残り: {remaining}件")

    if remaining <= 0:
        print("  本日の応募上限に達しました")
        return

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "playwright",
                        "--break-system-packages", "-q"], check=False)
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=False)
        from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        _run_with_playwright(pw, apply_log, remaining)

    print("━" * 50)


def _run_with_playwright(pw, apply_log, remaining):
    browser, page = launch_page(pw)
    try:
        # 検索
        print("\n[1] 案件検索...")
        jobs = search_all(page)
        print(f"\n  取得: {len(jobs)}件")

        if not jobs:
            print("  案件なし（Chromeでログイン確認）")
            return

        # 評価
        results = [evaluate(j) for j in jobs]
        go_jobs = [r for r in results
                   if r["total"] >= AUTO_APPLY_THRESHOLD
                   and r["verdict"] != "NO-GO"
                   and r["id"] not in apply_log["applied"]]

        print(f"\n[2] 評価結果: 応募対象={len(go_jobs)}件 / 全{len(results)}件")

        # JSON保存
        out = OUTPUT_DIR / f"{TODAY}_evaluated.json"
        out.write_text(json.dumps(results, ensure_ascii=False, indent=2))

        # 自動応募
        applied = 0
        print("\n[3] 自動応募...")
        for job in sorted(go_jobs, key=lambda x: x["total"], reverse=True):
            if applied >= remaining:
                break
            app_text = make_application(job)
            print(f"  [{job['total']}点] {job['title'][:40]}", end=" → ")

            if job["platform"] == "crowdworks":
                ok = auto_apply_crowdworks(page, job, app_text)
            else:
                ok = auto_apply_lancers(page, job, app_text)

            if ok:
                print("✅ 応募完了")
                apply_log["applied"][job["id"]] = {
                    "title": job["title"], "url": job["url"],
                    "score": job["total"], "platform": job["platform"],
                    "applied_at": datetime.now().isoformat(),
                    "application_text": app_text,
                }
                applied += 1
                time.sleep(3)
            else:
                print("⚠ スキップ（フォーム未検出）")

        save_apply_log(apply_log)

        # サマリ
        print(f"\n  本日応募: {applied}件")
        total_applied = len(apply_log["applied"])
        print(f"  累計応募: {total_applied}件")

        # 非GOの応募文も保存（手動確認用）
        txt_path = SESSIONS / f"job_applications_{TODAY}.txt"
        lines = ["═" * 60, f"  案件リスト {TODAY}", "═" * 60, ""]
        for r in sorted(results, key=lambda x: x["total"], reverse=True)[:10]:
            icon = "✅" if r.get("id") in apply_log["applied"] else ("⚠️ " if r["verdict"] == "CAUTION" else "❌")
            lines += [
                f"[{icon} {r['verdict']} {r['total']}点] {r['title']}",
                f"URL: {r['url']}",
                f"想定: ¥{r['estimated_price_jpy']:,}",
                "",
                make_application(r),
                "",
            ]
        txt_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"  一覧 → {txt_path}")

    finally:
        try:
            browser.close()
        except Exception:
            pass


if __name__ == "__main__":
    run()
