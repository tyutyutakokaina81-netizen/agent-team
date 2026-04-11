"""
03_apply.py — 応募文生成 + 自動送信
案件情報をもとに Claude が最適な応募文を生成し、Playwright で自動送信する。

自動送信の条件（リスク管理）:
  - 環境変数 AUTO_APPLY=1 が設定されていること
  - verdict が "GO" であること
  - スコアが AUTO_APPLY_THRESHOLD（デフォルト80）以上であること
"""

import json
import os
import time
import urllib.request
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
SESSION_DIR = Path(__file__).parent.parent / ".sessions"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
AUTO_APPLY = os.environ.get("AUTO_APPLY", "0") == "1"
AUTO_APPLY_THRESHOLD = int(os.environ.get("AUTO_APPLY_THRESHOLD", "80"))

APPLY_PROMPT = """
あなたはクラウドソーシングの応募文を作成するプロフェッショナルです。
以下の案件に対して、受注率の高い応募文を作成してください。

# 案件情報
タイトル: {title}
URL: {url}
カテゴリ: {category}
想定単価: ¥{price}

# 自己PR（使用可能なスキル）
- Pythonによるデータ処理・自動化
- Excel/CSVの高精度データ入力（AI支援＋人間確認）
- Webスクレイピング（BeautifulSoup/Playwright）
- 納期厳守・丁寧なコミュニケーション

# 応募文の条件
- 200〜300文字
- 具体的な作業方法に触れる
- 納期・品質への姿勢を示す
- 自然な日本語で、押しつけがましくない

応募文のみ出力してください（説明・前置き不要）。
"""


def call_claude(prompt: str) -> str:
    if not ANTHROPIC_API_KEY:
        raise EnvironmentError("ANTHROPIC_API_KEY が設定されていません")

    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 512,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        body = json.loads(res.read().decode("utf-8"))
    return body["content"][0]["text"]


def _template_application(job: dict) -> str:
    """APIキー不要のテンプレートベース応募文"""
    title = job.get("title", "")
    category = job.get("category", "")
    price = job.get("estimated_price_jpy", 0)

    if "scraping" in category or "スクレイピング" in title:
        skill = "PythonとPlaywrightを使ったWebスクレイピング"
        detail = "対象サイトの構造を確認し、正確にデータを収集いたします。"
    elif "excel" in category or "エクセル" in title.lower() or "Excel" in title:
        skill = "ExcelおよびPythonを使ったデータ処理・入力作業"
        detail = "正確性を重視し、入力後に必ずダブルチェックを行います。"
    else:
        skill = "データ入力・収集作業"
        detail = "丁寧かつ正確に対応いたします。"

    return f"""はじめまして。{skill}を得意としております。

ご依頼の「{title[:30]}」について、{detail}

納期は厳守いたします。不明点があれば事前に確認させていただきますので、安心してお任せください。ぜひご検討よろしくお願いいたします。"""


def generate_application(job: dict) -> dict:
    if ANTHROPIC_API_KEY:
        prompt = APPLY_PROMPT.format(
            title=job.get("title", ""),
            url=job.get("url", ""),
            category=job.get("category", ""),
            price=job.get("estimated_price_jpy", "不明"),
        )
        try:
            text = call_claude(prompt)
            return {**job, "application_text": text, "status": "draft"}
        except Exception:
            pass

    # APIキーなし → テンプレート応募文
    text = _template_application(job)
    return {**job, "application_text": text, "status": "template"}


def _submit_crowdworks(page, url: str, text: str) -> bool:
    """クラウドワークス: 応募フォームを自動送信"""
    page.goto(url)
    time.sleep(2)
    # 「応募する」ボタンをクリック
    for sel in [
        "a.btn-apply", "a[href*='apply']", "a:has-text('応募する')",
        "button:has-text('応募する')", ".job-apply-btn",
    ]:
        btn = page.query_selector(sel)
        if btn:
            btn.click()
            time.sleep(2)
            break
    # テキストエリアに応募文を入力
    for sel in [
        "textarea[name='job_offer_apply[body]']",
        "textarea[name='apply[body]']",
        "#job_offer_apply_body", "#body",
        "textarea.apply-body", "textarea",
    ]:
        ta = page.query_selector(sel)
        if ta:
            ta.fill(text)
            time.sleep(0.5)
            break
    else:
        return False
    # 送信ボタン
    for sel in [
        "input[type='submit']", "button[type='submit']",
        "button:has-text('送信')", "input[value*='送信']",
        "button:has-text('応募')", "input[value*='応募']",
    ]:
        btn = page.query_selector(sel)
        if btn:
            btn.click()
            time.sleep(3)
            return True
    return False


def _submit_lancers(page, url: str, text: str) -> bool:
    """ランサーズ: 提案フォームを自動送信"""
    page.goto(url)
    time.sleep(2)
    # 「提案する」ボタン
    for sel in [
        "a.btn-proposal", "a[href*='propose']", "a:has-text('提案する')",
        "button:has-text('提案する')", ".propose-btn",
    ]:
        btn = page.query_selector(sel)
        if btn:
            btn.click()
            time.sleep(2)
            break
    # テキストエリア
    for sel in [
        "textarea[name='proposal[body]']", "textarea[name='body']",
        "#proposal_body", "textarea.proposal-body", "textarea",
    ]:
        ta = page.query_selector(sel)
        if ta:
            ta.fill(text)
            time.sleep(0.5)
            break
    else:
        return False
    # 送信
    for sel in [
        "input[type='submit']", "button[type='submit']",
        "button:has-text('提案を送る')", "input[value*='提案']",
    ]:
        btn = page.query_selector(sel)
        if btn:
            btn.click()
            time.sleep(3)
            return True
    return False


def auto_submit_application(app: dict) -> bool:
    """
    高スコア GO 案件に Playwright で自動応募する。
    AUTO_APPLY=1 かつ score >= AUTO_APPLY_THRESHOLD の場合のみ実行。
    """
    if not AUTO_APPLY:
        return False
    if app.get("verdict") != "GO":
        return False
    if app.get("total", 0) < AUTO_APPLY_THRESHOLD:
        return False

    url = app.get("url", "")
    text = app.get("application_text", "")
    if not url or not text:
        return False

    platform = "crowdworks" if "crowdworks.jp" in url else "lancers" if "lancers.jp" in url else None
    if not platform:
        return False

    session_file = SESSION_DIR / f"{platform}_session.json"
    if not session_file.exists():
        print(f"  ⚠️  セッションなし ({platform}) → 手動応募してください")
        return False

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False

    storage = json.loads(session_file.read_text(encoding="utf-8"))
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, slow_mo=200)
            context = browser.new_context(
                storage_state=storage,
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()
            if platform == "crowdworks":
                ok = _submit_crowdworks(page, url, text)
            else:
                ok = _submit_lancers(page, url, text)
            browser.close()
        return ok
    except Exception as e:
        print(f"  ⚠️  自動応募失敗 ({platform}): {e}")
        return False


def run(jobs: list[dict] | None = None):
    if jobs is None:
        files = sorted(OUTPUT_DIR.glob("*_evaluated.json"))
        if not files:
            print("[ERROR] 評価済みファイルが見つかりません。02_evaluate.py を先に実行してください")
            return []
        all_jobs = json.loads(files[-1].read_text(encoding="utf-8"))
        jobs = [j for j in all_jobs if j.get("verdict") in ("GO", "CAUTION")]

    print(f"[応募文生成] {len(jobs)}件")
    applications = [generate_application(j) for j in jobs]

    out_path = OUTPUT_DIR / f"{datetime.now().strftime('%Y-%m-%d_%H%M')}_applications.json"
    out_path.write_text(
        json.dumps(applications, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 自動応募（AUTO_APPLY=1 の場合）
    auto_count = 0
    if AUTO_APPLY:
        go_apps = [a for a in applications if a.get("verdict") == "GO" and a.get("total", 0) >= AUTO_APPLY_THRESHOLD]
        print(f"\n[自動応募] GO案件 {len(go_apps)}件（スコア≥{AUTO_APPLY_THRESHOLD}）")
        for app in go_apps:
            print(f"  応募中: {app.get('title','')[:40]}...", end=" ", flush=True)
            ok = auto_submit_application(app)
            if ok:
                app["submitted"] = True
                auto_count += 1
                print("✅ 送信完了")
            else:
                print("❌ 失敗（手動対応）")
        out_path.write_text(json.dumps(applications, ensure_ascii=False, indent=2), encoding="utf-8")

    # サマリ表示
    print("\n" + "=" * 60)
    if AUTO_APPLY:
        print(f"  自動応募: {auto_count}件送信完了")
        manual = [a for a in applications if not a.get("submitted")]
        if manual:
            print(f"  手動応募が必要: {len(manual)}件")
    else:
        print("  応募文を生成しました（手動送信 or AUTO_APPLY=1 で自動送信）")
    print("=" * 60)
    for i, app in enumerate(applications, 1):
        submitted = "✅ 送信済" if app.get("submitted") else "📋 未送信"
        print(f"\n[{i}] {submitted} {app['title']}")
        print(f"    URL: {app['url']}")
        if not app.get("submitted"):
            print(f"    応募文:\n{app.get('application_text', '')}")
            print("-" * 40)

    print(f"\n[完了] {len(applications)}件 → {out_path}")
    return applications


if __name__ == "__main__":
    run()
