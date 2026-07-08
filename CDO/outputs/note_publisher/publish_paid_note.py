#!/usr/bin/env python3
"""
note 有料記事 自動公開ヘルパー（オーナーのMacで実行する）

publish_to_note.py（無料記事用）の姉妹スクリプト。有料デジタル商品／有料記事を扱う。
設計の最優先＝**絶対にタダで公開しない**：
  - デフォルトは下書き保存で止まる。公開は --publish を明示した時だけ。
  - 有料ライン(有料エリア指定)と価格の両方が確実にセットできたと判断できた時だけ公開する。
    どちらかでも未確定なら公開せず下書きで止め、手動手順を出す。

2026-07-03 更新（cowork self-fix）: note新エディタ(editor.note.com)にUI追従。
  - 入口: editor.note.com/new（/notes/new は一覧へリダイレクトするため）
  - 有料ライン: 本文の境界行でブロックメニュー(メニューを開く)→「有料エリア指定」
  - 価格: 「公開に進む」→ /publish/ 画面で「有料」を選び価格入力
  - 公開ボタン: 「投稿する」（旧「公開する」は廃止）
  - 公開前に「下書き保存」で編集状態を確定（見出し画像等の後の公開バリデーション誤判定回避）

入力ファイル（2形式に対応）：
  A) 明示ブロック形式（推奨・当リポジトリのCMO有料記事）：
     `## タイトル` / `## 無料部分` / `## 有料部分` / `## ハッシュタグ` の各コードブロック。
  B) note_ready.md 形式：先頭 `# 見出し` ＋ `<!-- PAYWALL price=NNN -->` または `★【ここから…】★`。

使い方:
  python3 publish_paid_note.py --login
  python3 publish_paid_note.py --article <path> --price 300           # 下書き（安全・既定）
  python3 publish_paid_note.py --article <path> --price 300 --publish  # 公開まで（安全ゲート付き）
"""

import argparse
import re
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("Playwrightが未インストールです。`./setup.sh` を実行してください。")

PROFILE_DIR = Path.home() / ".note_publisher_profile"
NOTE_LOGIN_URL = "https://note.com/login"
NOTE_NEW_URL_CANDIDATES = [
    "https://editor.note.com/new",
    "https://note.com/notes/new",
    "https://note.com/new",
]
TITLE_SELECTOR = (
    'textarea[placeholder="記事タイトル"], '
    'input[placeholder*="タイトル"], textarea[placeholder*="タイトル"], '
    '[contenteditable="true"][data-placeholder*="タイトル"], '
    'h1[contenteditable="true"], div[role="textbox"][aria-label*="タイトル"]'
)

_MARKER_PATTERNS = [
    re.compile(r"^[━─=]{6,}\s*$"),
    re.compile(r"^\s*★?【ここから.*?】★?\s*$"),
    re.compile(r"^\s*◆◆.*?◆◆\s*$"),
    re.compile(r"^\s*（note.*?有料.*?）\s*$"),
    re.compile(r"^\s*<!--\s*PAYWALL.*?-->\s*$"),
]


# ---------- セッション管理（publish_to_note.py と同方式） ----------

def _launch(playwright):
    try:
        ctx = playwright.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR), channel="chrome", headless=False,
            args=["--disable-blink-features=AutomationControlled"])
        print("🌐 本物のGoogle Chrome を使用しています")
        return ctx
    except Exception as e:
        print(f"⚠️  Chrome起動失敗 → Chromiumにフォールバック: {e}")
        return playwright.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR), headless=False,
            args=["--disable-blink-features=AutomationControlled"])


def login():
    print("ブラウザを起動します。表示されたウィンドウで note にログインしてください。")
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        ctx = _launch(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(NOTE_LOGIN_URL)
        input("ログインが完了したら Enter ...")
        ctx.close()
        print(f"✅ プロファイルを保存しました: {PROFILE_DIR}")


def load_context(playwright):
    if not PROFILE_DIR.exists() or not any(PROFILE_DIR.iterdir()):
        sys.exit("初回ログインがまだです。 `python3 publish_paid_note.py --login` を実行してください。")
    return _launch(playwright)


# ---------- パース ----------

def _clean_lines(block: str) -> str:
    kept = [ln for ln in block.splitlines() if not any(p.match(ln) for p in _MARKER_PATTERNS)]
    text = "\n".join(kept)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _extract_block(text: str, header: str):
    """`## <header>` 直下の ``` コードブロックを返す。無ければ None。"""
    m = re.search(rf"##\s*{re.escape(header)}.*?\n```\n(.+?)\n```", text, re.S)
    return m.group(1).strip() if m else None


def parse_paid_article(md_path: Path, title_override=None, price_override=None):
    """(title, free_body, paid_body, price, tags) を返す。
    明示ブロック形式（## 無料部分 / ## 有料部分）を優先。無ければ PAYWALL/★ 形式にフォールバック。"""
    text = md_path.read_text(encoding="utf-8")

    # 価格
    price = None
    m = re.search(r"<!--\s*PAYWALL[^>]*\bprice\s*=\s*(\d+)", text, re.I)
    if m:
        price = int(m.group(1))
    # 大文字/小文字を問わず「価格/Price」＋数字を拾う（英語有料商品の Price: ¥100 対応・2026-07-08）
    m2 = re.search(r"(?:価格|price)[^\d]{0,8}?(\d{3,5})", text, re.I)
    if price is None and m2:
        price = int(m2.group(1))
    if price_override is not None:
        price = price_override

    # タグ
    tags = []
    tag_block = _extract_block(text, "ハッシュタグ")
    if tag_block:
        tags = [t.lstrip("#").strip() for t in re.findall(r"#\S+", tag_block)]

    # 明示ブロック形式（推奨）
    free_block = _extract_block(text, "無料部分")
    paid_block = _extract_block(text, "有料部分")
    title_block = _extract_block(text, "タイトル")
    if free_block and paid_block:
        if title_override:
            title = title_override.strip()
        elif title_block:
            title = title_block.splitlines()[0].strip()
        else:
            tm = re.search(r"^#\s+(.+?)\s*$", text, re.M)
            title = tm.group(1).strip() if tm else md_path.stem
        free_body = _clean_lines(free_block)
        paid_body = _clean_lines(paid_block)
    else:
        # フォールバック：note_ready.md 形式
        sentinel = re.search(r"<!--\s*PAYWALL.*?-->", text)
        if sentinel:
            free_raw, paid_raw = text[:sentinel.start()], text[sentinel.end():]
        else:
            alt = re.search(r"^.*(?:★?【ここから.*?】★?|◆◆.*?◆◆).*$", text, re.M)
            if not alt:
                sys.exit("✗ 有料境界が見つかりません（## 無料部分/## 有料部分 も PAYWALL も ◆◆ も無い）。")
            free_raw, paid_raw = text[:alt.start()], text[alt.end():]
        if title_override:
            title = title_override.strip()
        else:
            tm = re.search(r"^#\s+(.+?)\s*$", free_raw, re.M)
            if not tm:
                sys.exit("✗ タイトル（先頭の `# 見出し`）が見つかりません。--title で指定してください。")
            title = tm.group(1).strip()
            free_raw = free_raw[:tm.start()] + free_raw[tm.end():]
        free_body = _clean_lines(free_raw)
        paid_body = _clean_lines(paid_raw)

    if not paid_body:
        sys.exit("✗ 有料エリアの本文が空です。境界の位置を確認してください。")
    if price is None:
        sys.exit("✗ 価格が不明です。--price 300 を指定してください。")
    return title, free_body, paid_body, price, tags


# ---------- note UI 操作（新エディタ） ----------

def _type_body(page, text: str):
    for i, para in enumerate(text.split("\n")):
        if para:
            page.keyboard.insert_text(para)
        page.keyboard.press("Enter")
        page.wait_for_timeout(20)


def _open_editor(page):
    """editor.note.com/new へ入り、タイトル欄を返す。"""
    for entry in NOTE_NEW_URL_CANDIDATES:
        try:
            page.goto(entry, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1500)
        except Exception:
            continue
        if "accounts.google.com" in page.url or page.url.rstrip("/").endswith("/login"):
            sys.exit("✗ note にログインしていません。 `python3 publish_paid_note.py --login` を再実行してください。")
        cand = page.locator(TITLE_SELECTOR).first
        try:
            cand.wait_for(state="visible", timeout=20000)
            print(f"🚪 エディタ入口: {entry} → {page.url}")
            return cand
        except Exception:
            continue
    return None


def _try_set_paywall(page) -> bool:
    """現在のカーソル行で ブロックメニュー(メニューを開く)→「有料エリア指定」を挿入。"""
    try:
        m = page.locator('[aria-label="メニューを開く"]').first
        if m.is_visible(timeout=2000):
            m.click()
            page.wait_for_timeout(700)
            item = page.locator(
                '[role="menuitem"]:has-text("有料エリア指定"), button:has-text("有料エリア指定"), '
                'li:has-text("有料エリア指定"), span:has-text("有料エリア指定")'
            ).first
            if item.is_visible(timeout=2000):
                item.click()
                page.wait_for_timeout(800)
                return True
    except Exception:
        pass
    return False


def _try_set_price_on_publish(page, price: int) -> bool:
    """/publish/ 画面で「有料」を選び価格を入力し、境界を確定。DOMで価格を検証できたら True。
    2026-07-03実測: 「有料」はradioを内包する<label>。選択後に価格input(placeholder=300相当)と
    「このラインより先を有料にする」ボタンが現れる。ボタンで本文の有料エリア指定ラインを束ねる。"""
    # 1) 「有料」を選択（labelクリックでpaid radioをオン）
    for sel in ('label:has-text("有料")', 'input[value="paid"]',
                '[role="radio"][value="paid"]', 'text=有料'):
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=1200):
                el.click()
                page.wait_for_timeout(1200)
                break
        except Exception:
            continue
    # 2) 価格入力（有料選択後に出現）
    filled = False
    for sel in ('input[type="number"]', 'input[inputmode="numeric"]',
                'input[placeholder="300"]', 'input[placeholder*="価格"]', 'input[placeholder*="金額"]'):
        try:
            inp = page.locator(sel).first
            if inp.is_visible(timeout=1500):
                inp.click()
                inp.fill("")
                inp.fill(str(price))
                page.wait_for_timeout(500)
                filled = True
                break
        except Exception:
            continue
    # 3) 有料境界の確定。2026-07-07 cowork self-fix（実測）：
    #    /publish/ 画面の最終ボタン「投稿する」は、有料ラインを確定するまで出現しない。
    #    まず「有料エリア設定」を開き、次に「このラインより先を有料にする」で
    #    ドラフト本文の既存 PAYWALL-LINE をそのまま確定する（境界は移動しない＝冪等）。
    try:
        area = page.locator('button:has-text("有料エリア設定")').first
        if area.is_visible(timeout=2000):
            area.click()
            page.wait_for_timeout(1500)
    except Exception:
        pass
    try:
        b = page.locator('button:has-text("このラインより先を有料にする")').first
        if b.is_visible(timeout=2500):
            b.click()
            page.wait_for_timeout(1500)
    except Exception:
        pass
    # 4) DOM検証：価格入力の値が price と一致
    try:
        vals = page.evaluate("()=>[...document.querySelectorAll('input')].map(i=>i.value).filter(Boolean)")
        return str(price) in vals
    except Exception:
        return filled


def publish(md_path: Path, do_publish: bool, title_override, price_override, tags_override):
    title, free_body, paid_body, price, file_tags = parse_paid_article(
        md_path, title_override, price_override)
    tags = tags_override if tags_override else file_tags

    print(f"📝 商品: {md_path.name}")
    print(f"🏷️  タイトル: {title}")
    print(f"💴 価格: ¥{price}")
    print(f"🆓 無料パート: {len(free_body)} 文字 / 🔒 有料パート: {len(paid_body)} 文字")
    print(f"🔖 タグ: {', '.join(tags) if tags else 'なし'}")
    print(f"🚦 モード: {'公開まで(--publish)' if do_publish else '下書き保存（安全・既定）'}")

    with sync_playwright() as p:
        ctx = load_context(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        title_input = _open_editor(page)
        if title_input is None:
            print("⚠️  タイトル入力欄が見つかりません。note側のUI変更/ログイン切れの可能性。")
            print(f"    現在のURL: {page.url}")
            if sys.stdin.isatty():
                input("Enterで閉じる ...")
            ctx.close()
            sys.exit(2)
        title_input.click()
        title_input.fill(title)
        print("✅ タイトル入力完了")

        editor = page.locator('div[contenteditable="true"]').first
        editor.click()
        _type_body(page, free_body)          # 無料パート＋末尾で改行済み
        print("✅ 無料パート入力完了")

        # 有料ライン（無料パートの直後＝正しい境界）
        paywall_ok = _try_set_paywall(page)
        if paywall_ok:
            print("✅ 「有料エリア指定」ラインをセットしました（無料パート直後）")
        else:
            editor.click()
            page.keyboard.insert_text("━━━【ここから下を有料に設定してください】━━━")
            page.keyboard.press("Enter")
            print("⚠️  有料ラインの自動セットに失敗。本文に目印を入れました（後で手動設定）。")

        # 有料パート
        # カーソルを編集領域の末尾へ確実に移動（JSで選択範囲を末尾に collapse）。
        # 旧実装（editor.click()+End）は本文中間にカーソルが飛び、有料本文が無料パートの
        # 途中に混入して全文がスクランブルする不具合があった（2026-07-07 cowork self-fix：
        # ncdcbf437aa5d で実測→JS caret-to-end に置換。FREE/PAYWALL-LINE/PAID の順序を保証）。
        page.evaluate(
            "()=>{const ed=document.querySelector('div[contenteditable=\"true\"]');"
            "if(!ed)return;ed.focus();const r=document.createRange();"
            "r.selectNodeContents(ed);r.collapse(false);"
            "const s=window.getSelection();s.removeAllRanges();s.addRange(r);}"
        )
        page.wait_for_timeout(200)
        _type_body(page, paid_body)
        print("✅ 有料パート入力完了")

        # 下書き保存で状態確定
        try:
            ds = page.locator('button:has-text("下書き保存")').first
            if ds.is_visible(timeout=2000):
                ds.click()
                page.wait_for_timeout(2500)
                print("✅ 下書き保存で編集状態を確定")
        except Exception as e:
            print(f"⚠️  下書き保存クリック省略: {e}")

        # 公開設定画面へ
        try:
            page.locator('button:has-text("公開に進む")').first.click()
            try:
                page.wait_for_url("**/publish/**", timeout=15000)
            except Exception:
                page.wait_for_timeout(3000)
        except Exception as e:
            print(f"⚠️  『公開に進む』クリック失敗: {e}")
        page.wait_for_timeout(1500)

        # タグ
        if tags:
            try:
                tag_input = page.locator(
                    'input[placeholder*="ハッシュタグ"], input[placeholder*="タグ"]').first
                tag_input.wait_for(state="visible", timeout=8000)
                for t in tags[:10]:
                    tag_input.click()
                    page.keyboard.type(t)
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(180)
                print(f"✅ タグ {len(tags[:10])} 個を入力")
            except Exception as e:
                print(f"⚠️  タグ入力に失敗: {e}")

        # 価格設定
        price_ok = _try_set_price_on_publish(page, price)
        print(f"{'✅' if price_ok else '⚠️ '} 価格設定: {'¥'+str(price)+' をDOM検証OK' if price_ok else '自動入力/検証に失敗'}")

        # --- 収益化セーフティ：有料ライン と 価格 の両方が確定した時だけ公開 ---
        safe_to_publish = paywall_ok and price_ok
        if not do_publish or not safe_to_publish:
            if do_publish and not safe_to_publish:
                print("\n🛑 安全のため公開を中止します（有料ライン/価格の自動セットが未確定）。")
            else:
                print("\n📋 下書きモード（既定）：公開しません。")
            print("   下書きは保存されています。note画面で次を確認し、必要なら手動で「投稿する」を：")
            print("   1) 本文中の「ここから有料」ライン（無料パート直後）")
            print(f"   2) /publish/ 画面で「有料」を選び、価格 ¥{price}")
            print(f"   現在URL: {page.url}")
            if sys.stdin.isatty():
                input("   確認したら Enter で閉じる ...")
            ctx.close()
            return None

        # 公開（投稿する）。公開は1回のみ。
        print("\n🚀 投稿する（＝公開）を押します（3秒後）...")
        page.wait_for_timeout(3000)
        published_id = None
        try:
            pub = page.locator('button:has-text("投稿する")').first
            pub.wait_for(state="visible", timeout=10000)
            pub.click()
            page.wait_for_timeout(2500)
            for lbl in ("有料エリア設定で投稿", "投稿する", "公開する", "OK"):
                try:
                    c = page.locator(f'[role="dialog"] >> button:has-text("{lbl}")').last
                    if c.is_visible(timeout=800):
                        c.click()
                        page.wait_for_timeout(1500)
                        break
                except Exception:
                    continue
            page.wait_for_timeout(3000)
            m = re.search(r"/notes/(n[a-z0-9]+)/", page.url)
            published_id = m.group(1) if m else None
            print(f"✅ 公開リクエスト送信。最終URL: {page.url}")
            if published_id:
                print(f"🔗 想定公開URL: https://note.com/safe_canna441/n/{published_id}")
        except Exception as e:
            print(f"⚠️  公開ボタン(投稿する)自動クリック失敗: {e}（画面で手動公開してください）")
            if sys.stdin.isatty():
                input("   公開を確認したら Enter ...")
        ctx.close()
        return published_id


# ---------- CLI ----------

def main():
    ap = argparse.ArgumentParser(description="note 有料記事 自動公開ヘルパー（収益化セーフティ付き）")
    ap.add_argument("--login", action="store_true")
    ap.add_argument("--article", type=str)
    ap.add_argument("--publish", action="store_true",
                    help="公開まで実行（有料ライン+価格の自動セットが確証できた時のみ実際に公開）。既定は下書き保存。")
    ap.add_argument("--price", type=int, default=None)
    ap.add_argument("--title", type=str, default=None)
    ap.add_argument("--tags", type=str, default=None)
    args = ap.parse_args()

    if args.login:
        login()
        return
    if not args.article:
        sys.exit("--article <path> を指定してください。")
    md_path = Path(args.article).expanduser()
    if not md_path.exists():
        sys.exit(f"記事が見つかりません: {md_path}")

    tags = [t.strip().lstrip("#") for t in args.tags.split(",")] if args.tags else None
    publish(md_path, do_publish=args.publish, title_override=args.title,
            price_override=args.price, tags_override=tags)


if __name__ == "__main__":
    main()
