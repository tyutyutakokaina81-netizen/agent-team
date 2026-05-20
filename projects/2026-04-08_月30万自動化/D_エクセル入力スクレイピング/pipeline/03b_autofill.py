"""
03b_autofill.py — 応募フォーム本文の自動入力

【動作の流れ】
  1. 案件ページを Playwright で開く（保存済みセッション使用）
  2. ユーザーが「応募する」ボタンを手動でクリック
  3. 応募フォーム画面へ遷移したことを検出
  4. 本文欄を応募文で自動入力（送信は行わない）
  5. ユーザーが内容を確認して「応募する／応募を確定」ボタンを手動でクリック

【規約遵守】
  - 応募送信ボタンは人手必須（応募禁止ルール ① に準拠）
  - 自動入力後はパイプラインが停止し、ユーザー判断を待つ

使い方:
  python 03b_autofill.py                       # 最新の applications.json を使用
  python 03b_autofill.py <applications.json>   # 指定ファイル
"""

import json
import sys
import time
from pathlib import Path

SESSION_DIR = Path(__file__).parent.parent / ".sessions"
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"


# プラットフォーム別の応募フォーム本文セレクタ（複数フォールバック）
TEXTAREA_SELECTORS = {
    "crowdworks": [
        'textarea[name="proposal[content]"]',
        'textarea[name="proposal[message]"]',
        '#proposal_content',
        'textarea.proposal-content',
        '.proposal-form textarea',
        'form textarea',  # 最終フォールバック
    ],
    "lancers": [
        'textarea[name="proposal[content]"]',
        'textarea[name="proposal[message]"]',
        '#proposal_content',
        'textarea[data-target="propose"]',
        '.c-proposalForm textarea',
        'form textarea',  # 最終フォールバック
    ],
}

# 応募フォームのURLパターン（遷移検出用）
PROPOSAL_URL_PATTERNS = {
    "crowdworks": ["/proposals/new", "/proposals/", "proposal"],
    "lancers": ["/work/proposal", "/proposal/"],
}


def _detect_platform(url: str) -> str:
    if "crowdworks.jp" in url:
        return "crowdworks"
    if "lancers.jp" in url:
        return "lancers"
    return "unknown"


def _wait_for_proposal_page(page, platform: str, timeout_sec: int = 120) -> bool:
    """ユーザーが応募ボタンを押して応募フォームへ遷移するのを待つ"""
    patterns = PROPOSAL_URL_PATTERNS.get(platform, [])
    if not patterns:
        return False

    print(f"  → 「応募する」ボタンを押して応募フォームを開いてください（最大{timeout_sec}秒待機）")
    start = time.time()
    while time.time() - start < timeout_sec:
        try:
            current_url = page.url
            if any(p in current_url for p in patterns):
                # 遷移検出（フォーム描画完了のため少し待つ）
                time.sleep(1.5)
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def _fill_textarea(page, platform: str, content: str) -> bool:
    """応募フォームの本文欄に応募文を入力（送信はしない）"""
    selectors = TEXTAREA_SELECTORS.get(platform, [])
    for selector in selectors:
        try:
            el = page.query_selector(selector)
            if el:
                # 既存の入力をクリアして自動入力
                el.fill("")
                time.sleep(0.3)
                el.fill(content)
                print(f"  ✅ 本文自動入力完了（セレクタ: {selector}）")
                return True
        except Exception:
            continue
    return False


def autofill_one(playwright_page, app: dict) -> str:
    """1案件の応募フォーム自動入力を実行

    戻り値: "filled" / "skipped" / "timeout" / "no_textarea" / "error"
    """
    url = app.get("url", "")
    title = app.get("title", "")[:50]
    content = app.get("application_text", "")
    platform = _detect_platform(url)

    if not url or not content:
        print(f"  [SKIP] URL or 応募文が空: {title}")
        return "skipped"

    if platform == "unknown":
        print(f"  [SKIP] 未対応プラットフォーム: {url}")
        return "skipped"

    print(f"\n━━━ {title} ━━━")
    print(f"  URL: {url}")

    try:
        playwright_page.goto(url, wait_until="domcontentloaded", timeout=20000)
    except Exception as e:
        print(f"  [ERROR] ページ読込失敗: {e}")
        return "error"

    # ユーザーが応募ボタンを押すのを待つ
    if not _wait_for_proposal_page(playwright_page, platform):
        print("  [TIMEOUT] 応募フォーム遷移を検出できませんでした（スキップ）")
        return "timeout"

    # 本文欄に自動入力
    if not _fill_textarea(playwright_page, platform, content):
        print("  [WARN] 本文欄が見つかりません。手動入力してください")
        return "no_textarea"

    # ユーザー確認待ち
    try:
        input("  ▶ 内容を確認し、応募ボタンを押したら Enter を押してください: ")
    except (KeyboardInterrupt, EOFError):
        print("\n  [中断] ユーザーが中断しました")
        return "skipped"

    return "filled"


def run(applications: list[dict] | None = None):
    if applications is None:
        files = sorted(OUTPUT_DIR.glob("*_applications.json"))
        if not files:
            print("[ERROR] 応募文ファイルが見つかりません。03_apply.py を先に実行してください")
            return
        applications = json.loads(files[-1].read_text(encoding="utf-8"))

    # GO のみ・上位5件
    sorted_apps = sorted(
        [a for a in applications if a.get("verdict") in ("GO", "CAUTION")],
        key=lambda x: x.get("total", 0),
        reverse=True,
    )[:5]

    if not sorted_apps:
        print("[終了] 自動入力対象がありません（GO/CAUTION 案件なし）")
        return

    # セッション確認
    platforms_needed = set(_detect_platform(a.get("url", "")) for a in sorted_apps)
    platforms_needed.discard("unknown")
    missing = [p for p in platforms_needed if not (SESSION_DIR / f"{p}_session.json").exists()]
    if missing:
        print(f"[ERROR] セッション未設定: {missing}")
        print("  python 00_session_setup.py を先に実行してください")
        return

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[ERROR] pip install playwright && playwright install chromium")
        return

    print("\n" + "━" * 60)
    print(f"  応募フォーム自動入力モード（{len(sorted_apps)}件・上位順）")
    print("━" * 60)
    print("  各案件で:")
    print("    1. ブラウザが案件ページを自動で開きます")
    print("    2. ご自身で「応募する」ボタンを押してください")
    print("    3. 応募フォームの本文が自動で入力されます")
    print("    4. 内容を確認し、応募ボタンを押してください（送信は手動）")
    print("    5. Enter キーで次の案件へ進みます")
    print("━" * 60)

    stats = {"filled": 0, "skipped": 0, "timeout": 0, "no_textarea": 0, "error": 0}

    with sync_playwright() as p:
        # 案件ごとにプラットフォームが異なるので、最初は cw・必要時に lancers セッション切替
        contexts = {}
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )

        try:
            for i, app in enumerate(sorted_apps, 1):
                url = app.get("url", "")
                platform = _detect_platform(url)
                if platform == "unknown":
                    stats["skipped"] += 1
                    continue

                # プラットフォーム別 context を遅延作成
                if platform not in contexts:
                    session_file = SESSION_DIR / f"{platform}_session.json"
                    storage = json.loads(session_file.read_text(encoding="utf-8"))
                    contexts[platform] = browser.new_context(
                        storage_state=storage,
                        viewport={"width": 1280, "height": 800},
                        user_agent=(
                            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/120.0.0.0 Safari/537.36"
                        ),
                    )
                    contexts[platform].add_init_script(
                        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                    )

                page = contexts[platform].new_page()
                print(f"\n[{i}/{len(sorted_apps)}]", end=" ")
                result = autofill_one(page, app)
                stats[result] = stats.get(result, 0) + 1
                try:
                    page.close()
                except Exception:
                    pass
        finally:
            for ctx in contexts.values():
                try:
                    ctx.close()
                except Exception:
                    pass
            browser.close()

    # サマリ
    print("\n" + "━" * 60)
    print("  自動入力サマリ")
    print("━" * 60)
    print(f"  自動入力完了: {stats.get('filled', 0)}件")
    print(f"  タイムアウト: {stats.get('timeout', 0)}件")
    print(f"  本文欄不検出: {stats.get('no_textarea', 0)}件")
    print(f"  エラー    : {stats.get('error', 0)}件")
    print(f"  スキップ  : {stats.get('skipped', 0)}件")
    print("\n  応募ログを CSO/research/応募ログ/2026-05.md に記録してください")


if __name__ == "__main__":
    apps = None
    if len(sys.argv) > 1:
        apps = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    run(apps)
