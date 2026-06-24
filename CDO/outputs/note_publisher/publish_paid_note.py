#!/usr/bin/env python3
"""
note 有料記事 自動公開ヘルパー（オーナーのMacで実行する）

既存の publish_to_note.py は「CMOの無料note記事（## 本文 形式・写真あり）」専用で、
有料デジタル商品（プロンプト集 / テンプレ集 = note_ready.md 形式）は扱えない：
  - parse_article が「## 本文」コードブロック前提 → note_ready.md ではエラー
  - 有料ライン（ここから有料）・価格を設定する機能が無い → そのまま公開すると全部タダ

このスクリプトは「有料商品」専用。設計の最優先＝**絶対にタダで公開しない**：
  - デフォルトは下書き保存（--draft 相当）で止まる。公開は --publish を明示した時だけ。
  - 有料ラインのセットに確証が持てない場合は、公開せず下書きで止め、手動2クリックの手順を出す。

入力ファイルの約束（note_ready.md）：
  - タイトル … 先頭の `# 見出し`（または --title で上書き）
  - 有料境界 … `<!-- PAYWALL price=980 -->` というコメント行。
                この行より前＝無料、後＝有料。価格は price=NNN で指定（--price で上書き可）。
  - `━━━` の囲みや `★【ここから…】★`、案内文（（noteエディタで…））は自動で除去する。

使い方:
  # 初回ログイン（publish_to_note.py と同じプロファイルを共有。未ログインならこちらでもOK）
  python3 publish_paid_note.py --login

  # 下書きを作る（安全・推奨）。本文が自動で入り、有料ライン+価格まで試みて、公開はしない
  python3 publish_paid_note.py --article <path/to/note_ready.md>

  # 中身を確認して問題なければ公開まで（有料ラインのセット確証が取れた時のみ公開）
  python3 publish_paid_note.py --article <path/to/note_ready.md> --publish

  # 価格やタイトル・タグを上書き
  python3 publish_paid_note.py --article ... --price 980 --title "..." --tags "AI,業務効率化,フリーランス"

注意（A1）：私(code)はnoteへ接続・検証ができないため、note側の有料UI操作は「ベストエフォート」。
UIが変わっている等で自動セットに失敗した場合でも、**下書きは残り**、画面に手動手順を表示して安全に止まる。
"""

import argparse
import re
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("Playwrightが未インストールです。`./setup.sh` を実行してください。")

# 既存ヘルパーとプロファイル（ログインセッション）を共有する
PROFILE_DIR = Path.home() / ".note_publisher_profile"
NOTE_LOGIN_URL = "https://note.com/login"
NOTE_NEW_URL = "https://note.com/notes/new"

# 本文に紛れ込む「人間向けの目印」を消すためのパターン
_MARKER_PATTERNS = [
    re.compile(r"^[━─=]{6,}\s*$"),                       # ━ や ─ の罫線
    re.compile(r"^\s*★?【ここから.*?】★?\s*$"),          # ★【ここから…】★
    re.compile(r"^\s*（note.*?有料.*?）\s*$"),            # （noteエディタで…ここから有料を選ぶ）
    re.compile(r"^\s*<!--\s*PAYWALL.*?-->\s*$"),          # <!-- PAYWALL ... -->（保険）
]


# ---------- セッション管理（publish_to_note.py と同方式） ----------

def _launch(playwright):
    """本物Chrome優先、失敗時Chromiumフォールバック（OAuth自動化検知の回避）。"""
    try:
        ctx = playwright.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="chrome",
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        print("🌐 本物のGoogle Chrome を使用しています")
        return ctx
    except Exception as e:
        print(f"⚠️  Chrome起動失敗 → Chromiumにフォールバック: {e}")
        return playwright.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )


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


# ---------- note_ready.md のパース ----------

def _clean_lines(block: str) -> str:
    """人間向けの目印（罫線・★案内）を除去し、過剰な空行を畳む。"""
    kept = []
    for line in block.splitlines():
        if any(p.match(line) for p in _MARKER_PATTERNS):
            continue
        kept.append(line)
    text = "\n".join(kept)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def parse_paid_article(md_path: Path, title_override=None, price_override=None):
    """note_ready.md を (title, free_body, paid_body, price) に分解する。"""
    text = md_path.read_text(encoding="utf-8")

    # 価格：sentinel の price=NNN → --price で上書き
    price = None
    m = re.search(r"<!--\s*PAYWALL[^>]*\bprice\s*=\s*(\d+)", text)
    if m:
        price = int(m.group(1))
    if price_override is not None:
        price = price_override

    # 有料境界で分割
    sentinel = re.search(r"<!--\s*PAYWALL.*?-->", text)
    if sentinel:
        free_raw = text[:sentinel.start()]
        paid_raw = text[sentinel.end():]
    else:
        # フォールバック：★【ここから…】★ の行で分割
        alt = re.search(r"^.*★?【ここから.*?】★?.*$", text, re.M)
        if not alt:
            sys.exit("✗ 有料境界が見つかりません（<!-- PAYWALL --> も ★【ここから…】★ も無い）。"
                     "\n  無料記事として出すなら publish_to_note.py を使ってください。")
        free_raw = text[:alt.start()]
        paid_raw = text[alt.end():]

    # タイトル：先頭の `# 見出し`（# 1つ）
    if title_override:
        title = title_override.strip()
    else:
        tm = re.search(r"^#\s+(.+?)\s*$", free_raw, re.M)
        if not tm:
            sys.exit("✗ タイトル（先頭の `# 見出し`）が見つかりません。--title で指定してください。")
        title = tm.group(1).strip()
        # 本文からタイトル行は落とす（noteのタイトル欄に入れるため）
        free_raw = free_raw[:tm.start()] + free_raw[tm.end():]

    free_body = _clean_lines(free_raw)
    paid_body = _clean_lines(paid_raw)

    if not paid_body:
        sys.exit("✗ 有料エリアの本文が空です。境界の位置を確認してください。")
    if price is None:
        sys.exit("✗ 価格が不明です。md に <!-- PAYWALL price=980 --> を置くか、--price 980 を指定してください。")

    return title, free_body, paid_body, price


# ---------- note UI 操作 ----------

def _dismiss_dialogs(page):
    for _ in range(3):
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(200)
        except Exception:
            pass
    for label in ("閉じる", "あとで", "スキップ", "今はしない", "×"):
        try:
            b = page.locator(f'button:has-text("{label}")').first
            if b.is_visible(timeout=300):
                b.click()
                page.wait_for_timeout(250)
        except Exception:
            pass


def _type_body(page, text: str):
    """段落ごとに insert_text → Enter で本文を流し込む（改行保持）。"""
    paragraphs = text.split("\n")
    for i, para in enumerate(paragraphs):
        if para:
            page.keyboard.insert_text(para)
        if i < len(paragraphs) - 1:
            page.keyboard.press("Enter")
            page.wait_for_timeout(20)


def _try_set_paywall(page) -> bool:
    """現在のカーソル位置に note の「ここから有料」ラインを挿入する（ベストエフォート）。
    note のUI差異に備えて複数手段を試す。確実にセットできたと判断できたら True。"""
    # 手段1：行頭の「＋」追加ボタン → メニューに「有料」を含む項目
    try:
        plus = page.locator('button[aria-label*="追加"], button[aria-label*="ブロック"]').first
        if plus.is_visible(timeout=1500):
            plus.click()
            page.wait_for_timeout(400)
            item = page.locator(
                '[role="menuitem"]:has-text("有料"), button:has-text("ここから有料"), '
                'li:has-text("ここから有料"), span:has-text("ここから有料")'
            ).first
            if item.is_visible(timeout=1500):
                item.click()
                page.wait_for_timeout(500)
                return True
    except Exception:
        pass
    # 手段2：ツールバー等にある「有料エリア」「ライン」ボタン
    for sel in ('button:has-text("有料エリア")', 'button:has-text("ここから有料")',
                '[aria-label*="有料"]'):
        try:
            b = page.locator(sel).first
            if b.is_visible(timeout=800):
                b.click()
                page.wait_for_timeout(500)
                return True
        except Exception:
            continue
    return False


def _try_set_price(page, price: int) -> bool:
    """販売設定で「有料」を選び、価格を入力する（ベストエフォート）。"""
    ok = False
    # 「公開設定」「販売設定」へ進む
    for label in ("公開に進む", "公開設定", "販売設定", "次へ"):
        try:
            b = page.locator(f'button:has-text("{label}")').first
            if b.is_visible(timeout=800):
                b.click()
                page.wait_for_timeout(700)
                break
        except Exception:
            continue
    # 「有料」を選択（ラジオ/トグル/タブ）
    for sel in ('label:has-text("有料")', 'button:has-text("有料")', 'text=有料'):
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=800):
                el.click()
                page.wait_for_timeout(500)
                break
        except Exception:
            continue
    # 価格入力
    for sel in ('input[placeholder*="価格"]', 'input[placeholder*="金額"]',
                'input[type="number"]', 'input[inputmode="numeric"]'):
        try:
            inp = page.locator(sel).first
            if inp.is_visible(timeout=800):
                inp.click()
                inp.fill(str(price))
                page.wait_for_timeout(300)
                ok = True
                break
        except Exception:
            continue
    return ok


def publish(md_path: Path, do_publish: bool, title_override, price_override, tags):
    title, free_body, paid_body, price = parse_paid_article(md_path, title_override, price_override)

    print(f"📝 商品: {md_path.name}")
    print(f"🏷️  タイトル: {title}")
    print(f"💴 価格: ¥{price}")
    print(f"🆓 無料パート: {len(free_body)} 文字 / 🔒 有料パート: {len(paid_body)} 文字")
    print(f"🔖 タグ: {', '.join(tags) if tags else 'なし'}")
    print(f"🚦 モード: {'公開まで(--publish)' if do_publish else '下書き保存（安全・既定）'}")

    with sync_playwright() as p:
        ctx = load_context(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(NOTE_NEW_URL)
        page.wait_for_load_state("networkidle", timeout=20000)
        if "accounts.google.com" in page.url or page.url.rstrip("/").endswith("/login"):
            sys.exit("✗ note にログインしていません。 `python3 publish_paid_note.py --login` を再実行してください。")

        _dismiss_dialogs(page)

        # タイトル
        title_input = page.locator(
            'input[placeholder*="タイトル"], textarea[placeholder*="タイトル"]'
        ).first
        try:
            title_input.wait_for(state="visible", timeout=60000)
        except Exception:
            print("⚠️  タイトル入力欄が見つかりません。note側のUI変更/ログイン切れの可能性。")
            print(f"    現在のURL: {page.url}")
            if sys.stdin.isatty():
                input("    画面を確認し、必要なら手動で。Enterで閉じる ...")
            ctx.close()
            sys.exit(2)
        title_input.click()
        title_input.fill(title)
        print("✅ タイトル入力完了")

        # 本文（無料パート）
        editor = page.locator('div[contenteditable="true"]').first
        editor.click()
        _type_body(page, free_body)
        page.keyboard.press("Enter")
        page.wait_for_timeout(150)

        # 有料ラインをセット（ベストエフォート）
        paywall_ok = _try_set_paywall(page)
        if paywall_ok:
            print("✅ 「ここから有料」ラインをセットしました")
        else:
            # セット不能 → 目印を本文に残す（手動で2クリックできるように）
            page.keyboard.insert_text("━━━【ここから下を有料に設定してください】━━━")
            page.keyboard.press("Enter")
            print("⚠️  有料ラインの自動セットに失敗。本文に目印を入れました（後で手動設定）。")

        # 有料パートを続けて入力
        _type_body(page, paid_body)
        print("✅ 本文（無料＋有料）の流し込み完了")

        # タグ
        if tags:
            try:
                tag_input = page.locator(
                    'input[placeholder*="ハッシュタグ"], input[placeholder*="タグ"]'
                ).first
                if not tag_input.is_visible(timeout=1200):
                    page.locator('button:has-text("公開に進む"), button:has-text("公開設定")').first.click()
                    page.wait_for_timeout(700)
                    tag_input = page.locator(
                        'input[placeholder*="ハッシュタグ"], input[placeholder*="タグ"]'
                    ).first
                for t in tags[:10]:
                    tag_input.click()
                    page.keyboard.type(t)
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(150)
                print(f"✅ タグ {len(tags[:10])} 個を入力")
            except Exception as e:
                print(f"⚠️  タグ入力に失敗: {e}（手動で追加してください）")

        # 価格設定（ベストエフォート）
        price_ok = _try_set_price(page, price)
        print(f"{'✅' if price_ok else '⚠️ '} 価格設定: {'¥'+str(price)+' を入力' if price_ok else '自動入力に失敗（手動で価格を入れてください）'}")

        # --- 公開可否の判定（収益化セーフティ）---
        # 有料ライン or 価格のどちらかが未確定なら、絶対に公開しない（タダ公開・無料公開の事故防止）
        safe_to_publish = paywall_ok and price_ok
        if do_publish and not safe_to_publish:
            print("\n🛑 安全のため公開を中止します（有料ライン/価格の自動セットが未確定）。")
            print("   下書きは保存されています。画面で次を確認してから手動で「公開」してください：")
            print("   1) 本文中の「ここから有料」ライン（無い場合は目印行の下で ＋メニュー→ここから有料）")
            print(f"   2) 販売設定で「有料」を選び、価格 ¥{price} を入力")
            print("   3) 右上の「公開」")
            if sys.stdin.isatty():
                input("   確認したら Enter で閉じる ...")
            ctx.close()
            return

        if not do_publish:
            print("\n📋 下書きモード（既定）：公開しません。note上で内容と有料設定を確認してください。")
            print(f"   この商品の想定価格は ¥{price} です。販売設定→有料→価格、を確認のうえ手動で公開を。")
            if sys.stdin.isatty():
                input("   Enterで閉じる ...")
            ctx.close()
            return

        # ここに来るのは do_publish かつ paywall_ok かつ price_ok のときだけ
        print("\n🚀 公開ボタンを押します（3秒後）...")
        page.wait_for_timeout(3000)
        try:
            page.locator('button:has-text("公開")').last.click()
            page.wait_for_timeout(1500)
            confirm = page.locator('button:has-text("有料エリア設定で公開"), button:has-text("公開する"), button:has-text("公開")').last
            if confirm.is_visible(timeout=2000):
                confirm.click()
            page.wait_for_timeout(3000)
            print("✅ 公開リクエストを送信しました。note側で反映と価格を必ず確認してください。")
        except Exception as e:
            print(f"⚠️  公開ボタン自動クリック失敗: {e}（画面で手動公開してください）")
            if sys.stdin.isatty():
                input("   公開を確認したら Enter ...")
        ctx.close()


# ---------- CLI ----------

def main():
    ap = argparse.ArgumentParser(description="note 有料記事 自動公開ヘルパー（収益化セーフティ付き）")
    ap.add_argument("--login", action="store_true", help="初回セッション保存（手動ログイン）")
    ap.add_argument("--article", type=str, help="商品md（note_ready.md）のパス")
    ap.add_argument("--publish", action="store_true",
                    help="公開まで実行（有料ライン+価格の自動セットが確証できた時のみ実際に公開）。既定は下書き保存。")
    ap.add_argument("--price", type=int, default=None, help="価格(円)。md の price=NNN を上書き")
    ap.add_argument("--title", type=str, default=None, help="タイトルを上書き（既定は先頭の # 見出し）")
    ap.add_argument("--tags", type=str, default=None, help="タグをカンマ区切りで指定（例: AI,業務効率化,フリーランス）")
    args = ap.parse_args()

    if args.login:
        login()
        return
    if not args.article:
        sys.exit("--article <note_ready.md のパス> を指定してください。")
    md_path = Path(args.article).expanduser()
    if not md_path.exists():
        sys.exit(f"記事が見つかりません: {md_path}")

    tags = [t.strip().lstrip("#") for t in args.tags.split(",")] if args.tags else []
    publish(md_path, do_publish=args.publish, title_override=args.title,
            price_override=args.price, tags=tags)


if __name__ == "__main__":
    main()
