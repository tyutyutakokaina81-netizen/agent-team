#!/usr/bin/env python3
"""
upload_to_gumroad.py — Gumroad商品へファイルを自動アップロード（オーナーのMacで実行）

publish_to_note.py と同じ方式：本物のChrome＋永続プロファイル（Googleログイン状態を保存）。
Claude側(コンテナ)はネット遮断で実行不可。これは「オーナーのMac」で動かす自動化。

使い方:
  # 初回だけ：Gumroadにログイン（Googleで）
  python3 ops/auto_company/upload_to_gumroad.py --login

  # アップロード（商品のpermalinkを指定。例 tako81.gumroad.com/l/oikujo なら oikujo）
  python3 ops/auto_company/upload_to_gumroad.py --permalink oikujo

  # 別ファイルを上げる場合
  python3 ops/auto_company/upload_to_gumroad.py --permalink oikujo --file path/to.md

注意:
  - Gumroadの画面構造が変わるとセレクタ調整が要る場合あり（Claudeはネット遮断で実機テスト不可）。
  - 保存/公開ボタンは自動で押さず、人が画面を確認してからEnterで進める設計（安全側）。
"""
import argparse
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("Playwrightが未インストールです。note_publisher の setup.sh を実行してください。")

REPO = Path(__file__).resolve().parents[2]
DEFAULT_FILE = REPO / "ops" / "outbox" / "gumroad" / "Solo_CEO_OS_完全版.md"
PROFILE_DIR = Path.home() / ".gumroad_publisher_profile"


def launch(playwright):
    try:
        ctx = playwright.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR), channel="chrome", headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        print("🌐 本物のGoogle Chrome を使用")
        return ctx
    except Exception as e:
        print(f"⚠️ Chrome起動失敗→Chromium: {e}")
        return playwright.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR), headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )


def do_login():
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    print("ブラウザでGumroadにログインしてください（Sign in with Google）。")
    with sync_playwright() as p:
        ctx = launch(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://app.gumroad.com/login")
        input("ログイン完了（ダッシュボードが見えたら）でEnter ...")
        ctx.close()
        print(f"✅ プロファイル保存: {PROFILE_DIR}")


def do_upload(permalink, file_path):
    if not PROFILE_DIR.exists() or not any(PROFILE_DIR.iterdir()):
        sys.exit("先にログインしてください: python3 ops/auto_company/upload_to_gumroad.py --login")
    fp = Path(file_path).expanduser().resolve()
    if not fp.exists():
        sys.exit(f"ファイルが無い: {fp}")

    edit_url = f"https://app.gumroad.com/products/{permalink}/edit"
    with sync_playwright() as p:
        ctx = launch(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        print(f"→ 商品編集ページを開く: {edit_url}")
        page.goto(edit_url, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        # Contentタブへ（あれば）
        for sel in ["a:has-text('Content')", "text=Content"]:
            try:
                el = page.locator(sel).first
                if el.is_visible():
                    el.click()
                    print("→ Contentタブをクリック")
                    page.wait_for_timeout(2500)
                    break
            except Exception:
                pass

        # ファイル入力にセット（hidden inputでもset_input_filesは効く）
        try:
            file_input = page.locator("input[type='file']").first
            file_input.set_input_files(str(fp))
            print(f"✅ ファイルをセット: {fp.name}")
        except Exception as e:
            print(f"⚠️ ファイル入力が見つからない: {e}")
            print("   → 画面の『Upload files』を一度クリックしてから、もう一度このスクリプトを実行してみてください。")

        page.wait_for_timeout(6000)  # アップロード反映待ち
        print("\n画面でファイルが追加されたか確認してください。")
        print("OKなら、画面右上の『Save changes』→『Publish』を押すか、Enterで自動クリックを試みます。")
        input("Enterで保存/公開を試行（手動で押したい場合はそのままEnter後ブラウザで操作）...")

        for label in ["Save changes", "Save and continue", "Publish", "Publish and continue"]:
            try:
                btn = page.get_by_role("button", name=label)
                if btn.is_visible():
                    btn.click()
                    print(f"→ 『{label}』をクリック")
                    page.wait_for_timeout(2500)
            except Exception:
                pass

        print("\n完了確認のため、ブラウザは開いたままにします。商品ページを目視してください。")
        input("終了するならEnter ...")
        ctx.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--login", action="store_true")
    ap.add_argument("--permalink", help="商品のpermalink（例: oikujo）")
    ap.add_argument("--file", default=str(DEFAULT_FILE))
    a = ap.parse_args()
    if a.login:
        do_login()
    elif a.permalink:
        do_upload(a.permalink, a.file)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
