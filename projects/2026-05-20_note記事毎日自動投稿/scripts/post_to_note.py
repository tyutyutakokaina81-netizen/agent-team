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


def normalize_cookie(c: dict) -> dict | None:
    """Chrome拡張「EditThisCookie」やDevToolsからエクスポートしたcookieを
    playwright の add_cookies が受け取れる形に正規化する。
    """
    if "name" not in c or "value" not in c:
        return None
    out: dict = {
        "name": c["name"],
        "value": c["value"],
        "path": c.get("path", "/"),
    }
    if "domain" in c and c["domain"]:
        out["domain"] = c["domain"]
    elif "url" in c:
        out["url"] = c["url"]
    else:
        out["domain"] = ".note.com"
    if "expirationDate" in c:
        try:
            out["expires"] = float(c["expirationDate"])
        except (TypeError, ValueError):
            pass
    elif "expires" in c:
        try:
            out["expires"] = float(c["expires"])
        except (TypeError, ValueError):
            pass
    if "httpOnly" in c:
        out["httpOnly"] = bool(c["httpOnly"])
    if "secure" in c:
        out["secure"] = bool(c["secure"])
    if "sameSite" in c and c["sameSite"]:
        ss = str(c["sameSite"]).strip()
        ss_lower = ss.lower()
        if ss_lower in ("strict", "lax", "none"):
            out["sameSite"] = ss.capitalize() if ss_lower != "none" else "None"
        elif ss_lower in ("no_restriction", "unspecified"):
            out["sameSite"] = "None"
    return out


def login_with_cookie(context, cookie_json: str) -> bool:
    """事前取得済みのセッションcookieでログイン状態を再現する。"""
    try:
        raw = json.loads(cookie_json)
    except json.JSONDecodeError:
        print("[WARN] NOTE_SESSION_COOKIE がJSON parseできません。パスワードログインにフォールバックします。")
        return False
    if not isinstance(raw, list):
        print("[WARN] NOTE_SESSION_COOKIE は配列形式である必要があります")
        return False
    normalized = [c for c in (normalize_cookie(c) for c in raw) if c]
    if not normalized:
        print("[WARN] 有効なcookieが0件です")
        return False
    try:
        context.add_cookies(normalized)
    except Exception as e:
        print(f"[WARN] cookie注入に失敗: {e}")
        return False
    print(f"[INFO] {len(normalized)}件のcookieを注入しました")
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


def find_thumbnail(article_path: Path) -> Path | None:
    """記事に紐づくサムネ画像ファイル（同じディレクトリ・同stem + _thumb.jpg/.png）を探す。"""
    stem = article_path.stem.replace("_note記事", "")
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        candidate = article_path.with_name(f"{stem}_thumb{ext}")
        if candidate.exists():
            return candidate
    # CMO/assets/thumbnails/ 配下も探す
    fallback_dir = REPO_ROOT / "CMO" / "assets" / "thumbnails"
    if fallback_dir.exists():
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            candidate = fallback_dir / f"{stem}_thumb{ext}"
            if candidate.exists():
                return candidate
    return None


def upload_thumbnail(page, image_path: Path) -> bool:
    """note エディタの見出し画像にサムネを設定する。

    note の編集画面では、本文上部にある画像アイコン（写真＋プラス風）をクリック →
    開いたメニューから「画像をアップロード」を選択すると input[type=file] が出現する。
    """
    print(f"[INFO] uploading thumbnail: {image_path}")

    # ① 画像挿入アイコンをクリックしてメニューを開く
    icon_clicked = False
    for sel in [
        'button[aria-label*="画像をアップロード"]',
        'button[aria-label*="画像を追加"]',
        'button[aria-label*="見出し画像"]',
        'button[aria-label*="画像"]',
        # アイコン形式（svgのみのボタン）。タイトル上部にある最初のbutton
        'div[class*="header"] button:has(svg)',
    ]:
        if page.locator(sel).count():
            try:
                page.locator(sel).first.click()
                page.wait_for_timeout(1500)
                print(f"[INFO] opened image menu via: {sel}")
                icon_clicked = True
                break
            except Exception as e:
                print(f"[WARN] click failed for {sel}: {e}")
    if not icon_clicked:
        page.screenshot(path=str(DEBUG_DIR / "debug_thumb_icon_not_found.png"))
        print("[WARN] image insertion icon not found; skipping thumbnail")
        return False

    # ② 開いたメニューから「画像をアップロード」を選ぶ
    menu_clicked = False
    for sel in [
        'text=画像をアップロード',
        'button:has-text("画像をアップロード")',
        '[role="menuitem"]:has-text("画像をアップロード")',
        'li:has-text("画像をアップロード")',
    ]:
        if page.locator(sel).count():
            try:
                page.locator(sel).first.click()
                page.wait_for_timeout(1500)
                print(f"[INFO] clicked '画像をアップロード' via: {sel}")
                menu_clicked = True
                break
            except Exception as e:
                print(f"[WARN] menu click failed for {sel}: {e}")
    if not menu_clicked:
        page.screenshot(path=str(DEBUG_DIR / "debug_thumb_menu_not_found.png"))
        # メニューが既に消えた等。ESCで閉じて続行
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
        print("[WARN] '画像をアップロード' menu item not found; skipping thumbnail")
        return False

    # ③ input[type="file"] にファイルをセット
    inputs = page.locator('input[type="file"]')
    count = inputs.count()
    print(f"[INFO] file inputs found: {count}")
    if count == 0:
        page.screenshot(path=str(DEBUG_DIR / "debug_thumb_input_still_missing.png"))
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
        print("[WARN] file input not appearing after menu click")
        return False

    try:
        inputs.first.set_input_files(str(image_path))
        page.wait_for_timeout(6000)
        page.screenshot(path=str(DEBUG_DIR / "debug_after_thumb_upload.png"))
        print("[INFO] thumbnail file set")

        # ④ 画像トリミング/プレビューモーダルの「保存」を押す
        # 「下書き保存」（右上の別UI）と区別するため、dialog内に絞る
        for sel in [
            'div[role="dialog"] button:has-text("保存")',
            '[role="dialog"] button:has-text("保存")',
            'div[class*="modal"] button:has-text("保存")',
            'button:has-text("保存"):not(:has-text("下書き"))',
            'div[role="dialog"] button:has-text("適用")',
            'div[role="dialog"] button:has-text("決定")',
        ]:
            if page.locator(sel).count():
                try:
                    page.locator(sel).first.click(timeout=5000)
                    page.wait_for_timeout(3000)
                    print(f"[INFO] confirmed crop modal with: {sel}")
                    break
                except Exception as e:
                    print(f"[WARN] crop save click failed for {sel}: {e}")
        else:
            # それでも見つからない場合は Enter キーで決定を試みる
            try:
                page.keyboard.press("Enter")
                page.wait_for_timeout(2000)
                print("[INFO] sent Enter to confirm crop modal")
            except Exception:
                pass
        return True
    except Exception as e:
        print(f"[WARN] thumbnail upload failed: {e}")
        page.screenshot(path=str(DEBUG_DIR / "debug_thumb_upload_error.png"))
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
        return False


def post_article(page, title: str, body: str, thumbnail_path: Path | None = None) -> str:
    """noteの新規投稿画面で記事を入力して公開する。"""
    page.goto(NOTE_NEW_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    print(f"[INFO] editor URL: {page.url}")

    # === サムネ画像アップロード（本文入力の前にやる）===
    if thumbnail_path and thumbnail_path.exists():
        upload_thumbnail(page, thumbnail_path)
        page.wait_for_timeout(2000)

    # === タイトル入力 ===
    title_selectors = [
        'textarea[placeholder*="タイトル"]',
        'input[placeholder*="タイトル"]',
        '[contenteditable="true"][data-placeholder*="タイトル"]',
    ]
    title_locator = None
    for sel in title_selectors:
        if page.locator(sel).count():
            title_locator = page.locator(sel).first
            print(f"[INFO] title selector: {sel}")
            break
    if title_locator is None:
        page.screenshot(path=str(DEBUG_DIR / "debug_editor_title_not_found.png"))
        raise RuntimeError("タイトル入力欄が見つかりません")

    title_locator.click()
    page.wait_for_timeout(300)
    page.keyboard.press("Control+A")
    page.keyboard.press("Delete")
    page.keyboard.insert_text(title)
    page.wait_for_timeout(500)
    print(f"[INFO] title entered: {title[:30]}...")

    # === 本文入力 ===
    body_locator = None
    for sel in ['[contenteditable="true"][data-placeholder*="本文"]', 'div.ProseMirror', '[role="textbox"]']:
        if page.locator(sel).count():
            body_locator = page.locator(sel).last
            print(f"[INFO] body selector: {sel}")
            break
    if body_locator is None:
        page.screenshot(path=str(DEBUG_DIR / "debug_editor_body_not_found.png"))
        raise RuntimeError("本文入力欄が見つかりません")

    body_locator.click()
    page.wait_for_timeout(500)
    # 既存の本文を全消去
    page.keyboard.press("Control+A")
    page.keyboard.press("Delete")
    page.wait_for_timeout(300)

    # 高速入力（insert_text は1回で全文を流し込む。type と違って文字ごとのキーイベントを発火しない）
    try:
        page.keyboard.insert_text(body)
        print("[INFO] body entered via insert_text")
    except Exception as e:
        print(f"[WARN] insert_text failed: {e}, fallback to execCommand")
        body_locator.evaluate(
            "(el, text) => { el.focus(); document.execCommand('insertText', false, text); }",
            body,
        )
        print("[INFO] body entered via execCommand")

    page.wait_for_timeout(3000)
    page.screenshot(path=str(DEBUG_DIR / "debug_before_publish.png"))

    # === 公開設定ボタン ===
    publish_clicked = False
    for sel in [
        'button:has-text("公開設定")',
        'button:has-text("公開に進む")',
        'button:has-text("投稿")',
        'a:has-text("公開設定")',
    ]:
        if page.locator(sel).count():
            print(f"[INFO] publish setting button: {sel}")
            page.locator(sel).first.click()
            page.wait_for_timeout(3000)
            publish_clicked = True
            break
    if not publish_clicked:
        page.screenshot(path=str(DEBUG_DIR / "debug_publish_button_not_found.png"))
        raise RuntimeError("「公開設定」ボタンが見つかりません")

    page.screenshot(path=str(DEBUG_DIR / "debug_publish_modal.png"))

    # === 最終公開ボタン ===
    final_clicked = False
    for sel in [
        'button:has-text("投稿する")',
        'button:has-text("公開する")',
        'button:has-text("無料で公開")',
        'button:has-text("有料公開")',
    ]:
        if page.locator(sel).count():
            print(f"[INFO] final publish button: {sel}")
            page.locator(sel).first.click()
            final_clicked = True
            break
    if not final_clicked:
        page.screenshot(path=str(DEBUG_DIR / "debug_final_publish_not_found.png"))
        raise RuntimeError("「公開する」ボタンが見つかりません")

    # 公開後のURLを待つ
    try:
        page.wait_for_url(re.compile(r"https://note\.com/.+/n/.+"), timeout=30000)
        print(f"[INFO] redirected to: {page.url}")
    except Exception:
        page.screenshot(path=str(DEBUG_DIR / "debug_publish_no_redirect.png"))
        # URLが変わらないが、成功している可能性も。確認のため待機
        page.wait_for_timeout(5000)
        print(f"[WARN] no expected redirect; current URL: {page.url}")
    return page.url


def main() -> int:
    import traceback
    try:
        return _main()
    except SystemExit:
        raise
    except Exception as e:
        print(f"[FATAL] Uncaught exception: {type(e).__name__}: {e}")
        traceback.print_exc()
        return 99


def _main() -> int:
    email = os.environ.get("NOTE_EMAIL", "").strip()
    password = os.environ.get("NOTE_PASSWORD", "").strip()
    cookie_json = os.environ.get("NOTE_SESSION_COOKIE", "").strip()
    explicit = os.environ.get("ARTICLE_PATH", "").strip()
    dry_run = os.environ.get("DRY_RUN", "").lower() == "true"
    print(f"[INFO] NOTE_EMAIL set: {bool(email)}")
    print(f"[INFO] NOTE_PASSWORD set: {bool(password)}")
    print(f"[INFO] NOTE_SESSION_COOKIE set: {bool(cookie_json)} (length={len(cookie_json)})")
    print(f"[INFO] ARTICLE_PATH: {explicit or '(auto)'}")
    print(f"[INFO] DRY_RUN: {dry_run}")

    if not (email and password) and not cookie_json:
        print("[ERROR] 認証情報が設定されていません。")
        print("  GitHub Secrets に NOTE_EMAIL+NOTE_PASSWORD または NOTE_SESSION_COOKIE を設定してください。")
        return 2

    article_path = pick_article_to_post(explicit or None)
    title, body = parse_article(article_path)
    thumbnail_path = find_thumbnail(article_path)
    print(f"[INFO] 投稿対象: {article_path.relative_to(REPO_ROOT)}")
    print(f"[INFO] タイトル: {title}")
    print(f"[INFO] 本文長: {len(body)} 文字")
    print(f"[INFO] サムネ: {thumbnail_path.relative_to(REPO_ROOT) if thumbnail_path else '(なし)'}")

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
            if logged_in:
                # 投稿画面に直接遷移してリダイレクトされなければログイン済み
                try:
                    page.goto(NOTE_NEW_URL, wait_until="domcontentloaded", timeout=15000)
                    page.wait_for_timeout(2500)
                except Exception as e:
                    print(f"[WARN] 投稿画面遷移エラー: {e}")
                    page.screenshot(path=str(DEBUG_DIR / "debug_cookie_goto_error.png"))
                    logged_in = False

                if logged_in:
                    current_url = page.url
                    print(f"[INFO] After goto, URL = {current_url}")
                    page.screenshot(path=str(DEBUG_DIR / "debug_after_cookie_login.png"))
                    try:
                        page.content_html = page.content()
                        with open(DEBUG_DIR / "debug_after_cookie_login.html", "w", encoding="utf-8") as f:
                            f.write(page.content_html[:50000])
                    except Exception:
                        pass

                    # ログイン画面に飛ばされていたら失敗
                    if "/login" in current_url or "/signin" in current_url:
                        print("[WARN] 投稿画面アクセス時にログイン画面へリダイレクトされました（cookie失効か無効）")
                        logged_in = False
                    else:
                        print("[INFO] cookieログイン成功（投稿画面に直接アクセスできました）")

        if not logged_in:
            if not (email and password):
                print("[ERROR] cookieログインに失敗、パスワードも未設定です")
                return 4
            login_with_password(page, email, password)

        if dry_run:
            print("[INFO] DRY_RUN: ログイン確認OK、投稿はスキップします")
            return 0

        url = post_article(page, title, body, thumbnail_path=thumbnail_path)
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
