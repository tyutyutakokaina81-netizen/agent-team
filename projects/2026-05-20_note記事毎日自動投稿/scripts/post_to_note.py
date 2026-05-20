"""
post_to_note.py — note.com への自動投稿スクリプト

実行環境：
- GitHub Actions（推奨。Secretsから認証情報を読む）
- ローカル（.envに認証情報を置く）

必要な環境変数：
- NOTE_EMAIL              ログイン用メールアドレス
- NOTE_PASSWORD           ログイン用パスワード
- NOTE_SESSION_COOKIE     （任意）事前取得したセッションcookie JSON
- ARTICLE_PATH            （任意）投稿する記事のリポジトリ内パス
- DRY_RUN                 "true"ならログイン確認のみで投稿せず終了
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PROJECT_DIR = Path(__file__).resolve().parents[1]
STATE_DIR = PROJECT_DIR / "state"
STATE_FILE = STATE_DIR / "posted.json"
DEBUG_DIR = Path(__file__).parent

NOTE_LOGIN_URL = "https://note.com/login"
NOTE_NEW_URL = "https://note.com/notes/new"


def load_posted_state() -> dict:
    if not STATE_FILE.exists():
        return {"posted": []}
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def save_posted_state(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def pick_article_to_post(explicit_path: str | None) -> Path:
    """投稿する記事のパスを決定する。

    explicit_path が指定されていればそれを使う。
    なければ CMO/outputs/ 配下の最新 *_note記事.md で、未投稿のものを選ぶ。
    """
    if explicit_path:
        p = (REPO_ROOT / explicit_path).resolve()
        if not p.exists():
            raise FileNotFoundError(f"指定された記事が見つかりません: {p}")
        return p

    outputs_dir = REPO_ROOT / "CMO" / "outputs"
    candidates = sorted(outputs_dir.glob("*_note記事.md"), reverse=True)
    posted_paths = set(load_posted_state().get("posted", []))
    for c in candidates:
        rel = str(c.relative_to(REPO_ROOT))
        if rel not in posted_paths:
            return c
    raise RuntimeError("投稿可能な未投稿記事が見つかりません")


def parse_article(article_path: Path) -> tuple[str, str]:
    """Markdownの記事から、タイトルと本文を抽出する。

    H1（# タイトル）をタイトルにし、それ以外を本文とする。
    """
    text = article_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    title = None
    body_lines: list[str] = []
    for line in lines:
        if title is None and line.startswith("# "):
            title = line[2:].strip()
            continue
        body_lines.append(line)
    if not title:
        title = article_path.stem
    body = "\n".join(body_lines).strip()
    return title, body


def login_with_cookie(context, cookie_json: str) -> bool:
    """事前取得済みのセッションcookieでログイン状態を再現する。"""
    try:
        cookies = json.loads(cookie_json)
    except json.JSONDecodeError:
        print("[WARN] NOTE_SESSION_COOKIE がJSON parseできません。パスワードログインにフォールバックします。")
        return False
    context.add_cookies(cookies)
    return True


def login_with_password(page, email: str, password: str) -> None:
    """メール+パスワードでログインする。

    note.comのログインフォームは将来UIが変わる可能性があるため、
    複数のセレクタ候補を試す。
    """
    page.goto(NOTE_LOGIN_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    email_selectors = [
        'input[type="email"]',
        'input[name="email"]',
        'input[placeholder*="メール"]',
    ]
    password_selectors = [
        'input[type="password"]',
        'input[name="password"]',
    ]

    for sel in email_selectors:
        if page.locator(sel).count():
            page.locator(sel).first.fill(email)
            break
    else:
        page.screenshot(path=str(DEBUG_DIR / "debug_login_email_not_found.png"))
        raise RuntimeError("メール入力欄が見つかりません（note.comのUI変更の可能性）")

    for sel in password_selectors:
        if page.locator(sel).count():
            page.locator(sel).first.fill(password)
            break
    else:
        page.screenshot(path=str(DEBUG_DIR / "debug_login_password_not_found.png"))
        raise RuntimeError("パスワード入力欄が見つかりません")

    submit_selectors = [
        'button[type="submit"]',
        'button:has-text("ログイン")',
    ]
    for sel in submit_selectors:
        if page.locator(sel).count():
            page.locator(sel).first.click()
            break

    try:
        page.wait_for_url(re.compile(r"https://note\.com/(?!login).*"), timeout=15000)
    except Exception:
        page.screenshot(path=str(DEBUG_DIR / "debug_login_no_redirect.png"))
        raise RuntimeError("ログイン後のリダイレクトが確認できません（2FA/CAPTCHAの可能性）")


def post_article(page, title: str, body: str) -> str:
    """noteの新規投稿画面で記事を入力して公開する。

    noteのエディタはリッチテキストで、Markdownをそのままペーストすると
    一部書式が崩れる可能性がある。当面はプレーンテキストとして投入し、
    UI構造が固まったら段階的に整形を強化する。
    """
    page.goto(NOTE_NEW_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    title_selectors = [
        'textarea[placeholder*="タイトル"]',
        'input[placeholder*="タイトル"]',
        '[contenteditable="true"][data-placeholder*="タイトル"]',
    ]
    for sel in title_selectors:
        if page.locator(sel).count():
            page.locator(sel).first.fill(title)
            break
    else:
        page.screenshot(path=str(DEBUG_DIR / "debug_editor_title_not_found.png"))
        raise RuntimeError("タイトル入力欄が見つかりません")

    body_selectors = [
        '[contenteditable="true"][data-placeholder*="本文"]',
        'div.ProseMirror',
        '[role="textbox"]',
    ]
    body_locator = None
    for sel in body_selectors:
        if page.locator(sel).count():
            body_locator = page.locator(sel).last
            break
    if body_locator is None:
        page.screenshot(path=str(DEBUG_DIR / "debug_editor_body_not_found.png"))
        raise RuntimeError("本文入力欄が見つかりません")

    body_locator.click()
    body_locator.type(body, delay=5)

    page.wait_for_timeout(2000)
    page.screenshot(path=str(DEBUG_DIR / "debug_before_publish.png"))

    publish_selectors = [
        'button:has-text("公開設定")',
        'button:has-text("公開に進む")',
        'button:has-text("投稿")',
    ]
    for sel in publish_selectors:
        if page.locator(sel).count():
            page.locator(sel).first.click()
            page.wait_for_timeout(2000)
            break

    final_publish_selectors = [
        'button:has-text("公開する")',
        'button:has-text("有料公開")',
    ]
    for sel in final_publish_selectors:
        if page.locator(sel).count():
            page.locator(sel).first.click()
            break

    try:
        page.wait_for_url(re.compile(r"https://note\.com/.+/n/.+"), timeout=20000)
    except Exception:
        page.screenshot(path=str(DEBUG_DIR / "debug_publish_no_redirect.png"))
        raise RuntimeError("公開後のURLが取得できません")

    return page.url


def main() -> int:
    email = os.environ.get("NOTE_EMAIL", "").strip()
    password = os.environ.get("NOTE_PASSWORD", "").strip()
    cookie_json = os.environ.get("NOTE_SESSION_COOKIE", "").strip()
    explicit = os.environ.get("ARTICLE_PATH", "").strip()
    dry_run = os.environ.get("DRY_RUN", "").lower() == "true"

    if not (email and password) and not cookie_json:
        print("[ERROR] 認証情報が設定されていません。")
        print("  GitHub Secrets に NOTE_EMAIL+NOTE_PASSWORD または NOTE_SESSION_COOKIE を設定してください。")
        return 2

    article_path = pick_article_to_post(explicit or None)
    title, body = parse_article(article_path)
    print(f"[INFO] 投稿対象: {article_path.relative_to(REPO_ROOT)}")
    print(f"[INFO] タイトル: {title}")
    print(f"[INFO] 本文長: {len(body)} 文字")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[ERROR] playwright が未インストールです。`pip install playwright && playwright install chromium`")
        return 3

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        logged_in = False
        if cookie_json:
            logged_in = login_with_cookie(context, cookie_json)
            page.goto("https://note.com/", wait_until="domcontentloaded")
            if "ログイン" in (page.title() or ""):
                logged_in = False

        if not logged_in:
            if not (email and password):
                print("[ERROR] cookieログインに失敗、パスワードも未設定です")
                return 4
            login_with_password(page, email, password)

        if dry_run:
            print("[INFO] DRY_RUN: ログイン確認OK、投稿はスキップします")
            return 0

        url = post_article(page, title, body)
        print(f"[OK] 投稿完了: {url}")

        state = load_posted_state()
        state.setdefault("posted", []).append(str(article_path.relative_to(REPO_ROOT)))
        state.setdefault("history", []).append(
            {
                "path": str(article_path.relative_to(REPO_ROOT)),
                "url": url,
                "posted_at": datetime.utcnow().isoformat() + "Z",
            }
        )
        save_posted_state(state)
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
