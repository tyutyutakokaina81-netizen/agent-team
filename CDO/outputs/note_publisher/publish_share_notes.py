#!/usr/bin/env python3
"""
note 送客シェア投稿ヘルパー（オーナーのMacのターミナルで実行する）

projects/2026-04-08 …ではなく、富山ガイドへの送客用に作った
  projects/2026-06-24_富山ガイド/note配信キット.md
の6本（タイトル＋本文＋ハッシュタグ）を読み込み、note.com に Playwright で投稿する。

ログイン状態は既存の publish_to_note.py と同じ永続プロファイル(~/.note_publisher_profile)を
共有するので、初回ログインは一度きり。

────────────────────────────────────────────────────────
使い方:
  # 0) 初回セットアップ（一度だけ。未実施なら）
  ./setup.sh

  # 1) 初回ログイン（一度だけ。Chromiumが立ち上がるので手動でnoteにログイン）
  python3 publish_to_note.py --login        # ← 既存スクリプトのログインを流用

  # 2) 何が投稿されるか一覧で確認（ブラウザは開かない）
  python3 publish_share_notes.py --list

  # 3) 1本だけ下書き保存（安全・既定）。ブラウザが開き、下書きで止まる。
  #    そこで「みんなのフォトギャラリー」で見出し画像を選び、自分で「公開」する。
  python3 publish_share_notes.py --post 1

  # 4) 1本を最後まで自動公開（見出し画像なしで公開される）
  python3 publish_share_notes.py --post 1 --publish

  # 5) 6本まとめて下書き保存（間隔をあけて。各本ごとに確認）
  python3 publish_share_notes.py --all

  # 6) 6本まとめて自動公開（※連投はnoteで埋もれやすい。非推奨だが可能）
  python3 publish_share_notes.py --all --publish --interval 30
────────────────────────────────────────────────────────

安全方針:
  - 既定は「下書き保存して止まる」。--publish を付けたときだけ公開ボタンを押す。
  - 見出し画像（サムネ）は『みんなのフォトギャラリー』推奨のため、自動では設定しない。
    下書きで止めて、あなたが画像を選んで公開するのが一番きれい。
  - 本文・タイトルはキットのまま投稿（改変しない）。
"""

import argparse
import re
import sys
import time
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("Playwrightが未インストールです。setup.sh を実行してください。")

REPO_ROOT = Path(__file__).resolve().parents[3]
KIT_PATH = REPO_ROOT / "projects" / "2026-06-24_富山ガイド" / "note配信キット.md"
PROFILE_DIR = Path.home() / ".note_publisher_profile"   # publish_to_note.py と共有
NOTE_NEW_URL = "https://note.com/notes/new"


# ---------- セッション（既存スクリプトと同じ永続プロファイル方式） ----------

def _launch(playwright):
    """本物Chrome優先、失敗時Chromiumフォールバック（既存と同じ）"""
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


def _ensure_profile():
    if not PROFILE_DIR.exists() or not any(PROFILE_DIR.iterdir()):
        sys.exit("初回ログインがまだです。 `python3 publish_to_note.py --login` を先に実行してください。")


# ---------- 配信キットのパース ----------

def parse_kit(kit_path: Path):
    """note配信キット.md から各投稿(番号/タイトル/本文)を抽出する。

    フォーマット（1ブロック）:
        ## ① 紅ズワイガニ（高志の紅ガニ）
        **タイトル:** ....
        **本文:**
        ```
        本文（複数行・末尾にURL・ハッシュタグ）
        ```
        **みんフォト検索:** `..` `..`
    """
    if not kit_path.exists():
        sys.exit(f"配信キットが見つかりません: {kit_path}")
    text = kit_path.read_text(encoding="utf-8")

    posts = []
    # 各「## 見出し」セクションごとに分割
    sections = re.split(r"\n##\s+", text)
    for sec in sections:
        title_m = re.search(r"\*\*タイトル:\*\*\s*(.+)", sec)
        body_m = re.search(r"\*\*本文:\*\*\s*\n```\n(.+?)\n```", sec, re.S)
        if not (title_m and body_m):
            continue
        heading = sec.splitlines()[0].strip()
        title = title_m.group(1).strip()
        body = body_m.group(1).strip("\n")
        # みんフォト検索ワード（参考表示用）
        photo_m = re.search(r"\*\*みんフォト検索:\*\*\s*(.+)", sec)
        photo_hint = photo_m.group(1).strip() if photo_m else ""
        posts.append({"heading": heading, "title": title, "body": body, "photo": photo_hint})
    return posts


def cmd_list(posts):
    print(f"\n📋 配信キットの投稿（全{len(posts)}本）\n")
    for i, p in enumerate(posts, 1):
        first_line = p["title"]
        print(f"  [{i}] {p['heading']}")
        print(f"      タイトル: {first_line}")
        if p["photo"]:
            print(f"      みんフォト検索: {p['photo']}")
        print()


# ---------- note エディタへの投入（既存 publish_to_note.py の操作を踏襲） ----------

def post_one(ctx, post: dict, do_publish: bool):
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(NOTE_NEW_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(2500)

    # ログイン確認（新規作成画面に来られているか）
    if "login" in page.url:
        sys.exit("✗ note にログインしていません。`python3 publish_to_note.py --login` を再実行してください。")

    # 初回チュートリアル等のポップアップを閉じる保険
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass

    # タイトル入力
    title_input = page.locator(
        'textarea[placeholder*="タイトル"], textarea[placeholder*="記事タイトル"], '
        'input[placeholder*="タイトル"], div[contenteditable="true"]'
    ).first
    title_input.click()
    page.wait_for_timeout(300)
    page.keyboard.insert_text(post["title"])
    page.wait_for_timeout(400)

    # 本文へ移動（Tab か、本文コンテンツ領域をクリック）
    page.keyboard.press("Tab")
    page.wait_for_timeout(400)
    editor = page.locator('div[contenteditable="true"]').last
    try:
        editor.click()
    except Exception:
        pass
    page.wait_for_timeout(300)

    # 本文を段落ごとに入力（空行で段落分け）
    paragraphs = post["body"].split("\n")
    for i, para in enumerate(paragraphs):
        if para.strip() == "":
            page.keyboard.press("Enter")
        else:
            page.keyboard.insert_text(para)
            page.keyboard.press("Enter")
        page.wait_for_timeout(120)

    page.wait_for_timeout(800)

    if not do_publish:
        print("  📝 下書きの内容を入力しました（公開はしません）。")
        print("     → ブラウザで『みんなのフォトギャラリー』から見出し画像を選び、")
        print(f"       検索ワード例: {post['photo']}")
        print("     → 内容を確認して、自分で『公開』を押してください。")
        return

    # --publish: 公開フローへ
    print("  🚀 公開に進みます…")
    try:
        page.locator('button:has-text("公開に進む"), button:has-text("公開設定")').first.click()
        page.wait_for_timeout(1500)
    except Exception:
        pass
    # 最終「公開」ボタン
    try:
        page.locator('button:has-text("公開")').last.click()
        page.wait_for_timeout(1500)
        confirm = page.locator('button:has-text("公開する"), button:has-text("投稿する"), button:has-text("公開")').last
        confirm.click(timeout=4000)
        print("  ✅ 公開リクエストを送信しました。")
    except Exception as e:
        print(f"  ⚠️  公開ボタンの自動クリックに失敗: {e}")
        print("     画面で『公開』を手動で押してください。")
        input("     公開を確認したら Enter ...")


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description="note 送客シェア投稿ヘルパー（配信キット6本）")
    ap.add_argument("--list", action="store_true", help="投稿内容を一覧表示（ブラウザは開かない）")
    ap.add_argument("--post", type=int, metavar="N", help="N番目(1〜)の投稿だけ実行")
    ap.add_argument("--all", action="store_true", help="全6本を順番に実行")
    ap.add_argument("--publish", action="store_true", help="公開ボタンまで押す（既定は下書きで停止）")
    ap.add_argument("--interval", type=int, default=20, help="--all時の各投稿の間隔秒（既定20）")
    args = ap.parse_args()

    posts = parse_kit(KIT_PATH)
    if not posts:
        sys.exit("配信キットから投稿を抽出できませんでした。note配信キット.md の形式を確認してください。")

    if args.list:
        cmd_list(posts)
        return

    if not args.post and not args.all:
        cmd_list(posts)
        print("使い方: --post N で1本、--all で全部。既定は下書き保存（--publish で公開まで）。")
        return

    _ensure_profile()

    # 対象の決定
    if args.post:
        if not (1 <= args.post <= len(posts)):
            sys.exit(f"--post は 1〜{len(posts)} で指定してください。")
        targets = [posts[args.post - 1]]
    else:
        targets = posts

    mode = "公開" if args.publish else "下書き保存"
    print(f"\n▶ {len(targets)}本を「{mode}」で処理します。\n")

    with sync_playwright() as p:
        ctx = _launch(p)
        try:
            for idx, post in enumerate(targets, 1):
                print(f"--- [{idx}/{len(targets)}] {post['heading']} ---")
                post_one(ctx, post, do_publish=args.publish)
                if args.all and idx < len(targets):
                    print(f"  …次まで {args.interval}秒待機\n")
                    time.sleep(args.interval)
            if not args.publish:
                print("\n📌 すべて下書きで止めました。各ブラウザタブで画像を足して『公開』してください。")
                input("確認が終わったら Enter でブラウザを閉じます ...")
        finally:
            ctx.close()
    print("\n完了。")


if __name__ == "__main__":
    main()
