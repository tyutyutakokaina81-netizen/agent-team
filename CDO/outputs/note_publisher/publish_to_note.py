#!/usr/bin/env python3
"""
note 自動公開ヘルパー（オーナーのMacで実行する）

CMO/outputs/ の最新note記事(.md)を読み込み、note.com に Playwright で投稿する。
柱D と同じ「初回ログインのみ手動、以後セッション再利用」モデル。

使い方:
  # 初回セットアップ（一度だけ）
  ./setup.sh

  # 初回ログイン（一度だけ。Chromiumが立ち上がるので手動でnoteにログイン）
  python publish_to_note.py --login

  # 公開（基本形：CMO/outputs/の最新記事を、写真ディレクトリを指定して投稿）
  python publish_to_note.py --photos ~/Pictures/note/2026-05-28/

  # 特定記事を指定して公開
  python publish_to_note.py --article CMO/outputs/2026-05-28_note記事_xxx.md --photos ~/Pictures/note/2026-05-28/

  # ドラフト保存だけ（公開ボタンは押さず、最終確認のため）
  python publish_to_note.py --photos ... --draft

写真ディレクトリの命名規則:
  photo_01.jpg, photo_02.jpg, ...  → [写真①], [写真②], ... に順番に対応
  photo_01.jpg がサムネ(見出し画像)になる
"""

import argparse
import re
import sys
import json
from pathlib import Path
from datetime import datetime

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("Playwrightが未インストールです。setup.sh を実行してください。")

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTICLES_DIR = REPO_ROOT / "CMO" / "outputs"
SESSION_FILE = Path.home() / ".note_publisher_session.json"
NOTE_LOGIN_URL = "https://note.com/login"
NOTE_NEW_URL = "https://note.com/notes/new"


# ---------- セッション管理 ----------

def login():
    """初回のみ。Chromiumを立ち上げてオーナーが手動ログイン→セッション保存"""
    print("Chromium を起動します。表示されたウィンドウで note にログインしてください。")
    print("ログイン完了後、このターミナルで Enter を押すとセッションを保存します。")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto(NOTE_LOGIN_URL)
        input("ログインが完了したら Enter ...")
        ctx.storage_state(path=str(SESSION_FILE))
        print(f"✅ セッションを保存しました: {SESSION_FILE}")
        browser.close()


def load_context(playwright):
    """保存済みセッションでブラウザコンテキストを作る"""
    if not SESSION_FILE.exists():
        sys.exit("初回ログインがまだです。 `python publish_to_note.py --login` を実行してください。")
    browser = playwright.chromium.launch(headless=False)  # 進捗が見えるようheaded
    ctx = browser.new_context(storage_state=str(SESSION_FILE))
    return browser, ctx


# ---------- 記事mdから タイトル/本文/写真placeholder を抽出 ----------

def find_latest_article():
    """CMO/outputs/ 配下の最新note記事mdを返す"""
    candidates = sorted(
        ARTICLES_DIR.glob("*_note記事_*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        sys.exit(f"記事が見つかりません: {ARTICLES_DIR}/*_note記事_*.md")
    return candidates[0]


def parse_article(md_path: Path):
    """記事mdから タイトル・本文・写真placeholderの順序を取り出す"""
    text = md_path.read_text(encoding="utf-8")

    # タイトル：「メイン：」直下の最初の ``` コードブロック
    title_m = re.search(r"メイン.*?\n```\n(.+?)\n```", text, re.S)
    if not title_m:
        # フォールバック：「## タイトル」直下
        title_m = re.search(r"##\s*タイトル.*?\n```\n(.+?)\n```", text, re.S)
    if not title_m:
        sys.exit("タイトルブロックがmdから抽出できませんでした。")
    title = title_m.group(1).strip().splitlines()[0].strip()

    # 本文：「## 本文」直下の ``` コードブロック
    body_m = re.search(r"##\s*本文.*?\n```\n(.+?)\n```", text, re.S)
    if not body_m:
        sys.exit("本文ブロック（## 本文 直下の ```）がmdから抽出できませんでした。")
    body = body_m.group(1).strip()

    # 写真placeholderの個数（[写真①]〜⑩、または[ここに写真...]）
    placeholders = re.findall(r"\[(?:ここに)?写真[①②③④⑤⑥⑦⑧⑨⑩\d]+[^\]]*\]", body)
    return title, body, placeholders


def split_body_by_photo_placeholders(body: str):
    """本文を写真placeholderで分割し、[テキスト断片, 写真index, テキスト断片, ...] のリストを返す"""
    parts = re.split(r"(\[(?:ここに)?写真[①②③④⑤⑥⑦⑧⑨⑩\d]+[^\]]*\])", body)
    out = []
    i_photo = 0
    for p in parts:
        if not p:
            continue
        if re.match(r"\[(?:ここに)?写真", p):
            i_photo += 1
            out.append(("photo", i_photo))
        else:
            out.append(("text", p))
    return out


def collect_photos(photo_dir: Path):
    """photo_dir から photo_01.* photo_02.* ... を順番に集める"""
    if not photo_dir or not photo_dir.exists():
        return []
    photos = []
    for i in range(1, 21):
        for ext in ("jpg", "jpeg", "png", "JPG", "JPEG", "PNG", "heic", "HEIC"):
            p = photo_dir / f"photo_{i:02d}.{ext}"
            if p.exists():
                photos.append(p)
                break
    return photos


# ---------- 投稿フロー（note UI操作） ----------

def publish(md_path: Path, photo_dir: Path | None, draft: bool):
    title, body, placeholders = parse_article(md_path)
    photos = collect_photos(photo_dir) if photo_dir else []

    print(f"📝 記事: {md_path.name}")
    print(f"🏷️  タイトル: {title}")
    print(f"📸 写真placeholder: {len(placeholders)} 個")
    print(f"🖼️  実写ファイル: {len(photos)} 枚 ({photo_dir})")

    if placeholders and not photos:
        print("⚠️  写真placeholderはあるが、写真ファイルが見つかりません。")
        print("    --photos でディレクトリを指定するか、photo_01.jpg を配置してください。")
    if len(photos) < len(placeholders):
        print(f"⚠️  写真が不足: {len(placeholders)}枚必要 / {len(photos)}枚しかない")

    with sync_playwright() as p:
        browser, ctx = load_context(p)
        page = ctx.new_page()
        page.goto(NOTE_NEW_URL)
        page.wait_for_load_state("networkidle", timeout=20000)

        # タイトル入力（noteのエディタはplaceholderに「タイトル」を含む）
        title_input = page.locator(
            'input[placeholder*="タイトル"], textarea[placeholder*="タイトル"]'
        ).first
        title_input.click()
        title_input.fill(title)
        print("✅ タイトル入力完了")

        # 本文エディタにフォーカス
        editor = page.locator('div[contenteditable="true"]').first
        editor.click()

        # 本文を写真placeholderで分割しながら、テキスト→写真→テキスト... で挿入
        segments = split_body_by_photo_placeholders(body)
        for kind, val in segments:
            if kind == "text":
                # 段落ごとに改行を保ちながら挿入
                page.keyboard.insert_text(val)
            elif kind == "photo":
                idx = val - 1
                if idx < len(photos):
                    # noteの画像挿入：ツールバーの画像ボタン or ドラッグ
                    # MVP: ファイル選択ダイアログを開けるボタンを探してクリック→画像をupload
                    try:
                        # 画像挿入ボタンを探す（aria-label に "画像" を含むことが多い）
                        with page.expect_file_chooser() as fc_info:
                            page.locator(
                                'button[aria-label*="画像"], [data-testid*="image"]'
                            ).first.click()
                        file_chooser = fc_info.value
                        file_chooser.set_files(str(photos[idx]))
                        page.wait_for_timeout(1500)  # アップロード待機
                        print(f"  ✅ 写真{val} アップロード: {photos[idx].name}")
                    except Exception as e:
                        print(f"  ⚠️  写真{val} 自動挿入に失敗: {e}")
                        print(f"      ファイル {photos[idx]} を手動で挿入してください")
                else:
                    print(f"  ⚠️  写真{val} のファイルが無いためスキップ")
            page.wait_for_timeout(200)

        print("✅ 本文＆写真の挿入処理が完了")

        # サムネ（見出し画像）：写真① をアップロード
        if photos:
            try:
                # 「見出し画像」エリアを開く（noteは設定パネルにある）
                page.locator('button:has-text("見出し画像"), [aria-label*="見出し画像"]').first.click()
                page.wait_for_timeout(500)
                with page.expect_file_chooser() as fc:
                    page.locator('input[type="file"]').first.click()
                fc.value.set_files(str(photos[0]))
                page.wait_for_timeout(1500)
                print(f"✅ サムネ(見出し画像)に {photos[0].name} を設定")
            except Exception as e:
                print(f"⚠️  サムネ自動設定に失敗: {e}（手動で写真①をサムネに）")

        # 公開 or 下書き
        if draft:
            print("\n📋 ドラフトモード：公開ボタンは押しません。画面で内容確認してください。")
            input("Enterで閉じる ...")
        else:
            print("\n🚀 公開ボタンを押します（3秒後）...")
            page.wait_for_timeout(3000)
            try:
                page.locator('button:has-text("公開")').last.click()
                page.wait_for_timeout(2000)
                # 確認ダイアログがあれば再度公開
                confirm = page.locator('button:has-text("公開する"), button:has-text("公開")').last
                if confirm.is_visible():
                    confirm.click()
                page.wait_for_timeout(3000)
                print("✅ 公開リクエストを送信しました。note側で反映を確認してください。")
            except Exception as e:
                print(f"⚠️  公開ボタン自動クリック失敗: {e}")
                print("    画面で「公開」ボタンを手動で押してください。")
                input("公開を確認したら Enter ...")

        browser.close()


# ---------- CLI ----------

def main():
    ap = argparse.ArgumentParser(description="note 自動公開ヘルパー")
    ap.add_argument("--login", action="store_true", help="初回セッション保存（手動ログイン）")
    ap.add_argument("--article", type=str, help="記事mdのパス（省略時は最新を自動選択）")
    ap.add_argument("--photos", type=str, help="写真ディレクトリ（photo_01.jpg, photo_02.jpg, ...）")
    ap.add_argument("--draft", action="store_true", help="公開ボタンを押さずに止める（最終確認用）")
    args = ap.parse_args()

    if args.login:
        login()
        return

    md_path = Path(args.article) if args.article else find_latest_article()
    if not md_path.exists():
        sys.exit(f"記事が見つかりません: {md_path}")

    photo_dir = Path(args.photos).expanduser() if args.photos else None
    publish(md_path, photo_dir, draft=args.draft)


if __name__ == "__main__":
    main()
