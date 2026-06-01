#!/usr/bin/env python3
"""
attach_thumbnails.py — note 公開済み記事に後追いでサムネ(見出し画像)を添付する。

前提:
- 既に publish_to_note.py --login でセッション保存済み
- ローカルの thumbnails/ フォルダに画像ファイルを置いてある
  命名規則（どれかにマッチすれば自動で記事と紐づく）:
    YYYY-MM-DD.jpg               例: 2026-06-01.jpg → その日付の任意の1本
    YYYY-MM-DD_<キーワード>.jpg  例: 2026-06-01_富山ブラック.jpg → タイトルにキーワード含む記事
    <記事mdと同じstem>.jpg       例: 2026-06-01_note記事_富山ブラックラーメン_労働者の塩分補給.jpg

使い方:
  python3 attach_thumbnails.py --dry-run        # 何が更新されるか表示のみ
  python3 attach_thumbnails.py                  # 実行（マッチした全件）
  python3 attach_thumbnails.py --confirm        # 1件ずつ目視確認しながら
  python3 attach_thumbnails.py --filter 2026-06-01  # 指定日付のみ
  python3 attach_thumbnails.py --skip-existing  # 既に見出し画像がある記事は飛ばす
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("Playwrightが未インストールです。setup.sh を実行してください。")

SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parents[2]
ARTICLES_DIR = REPO / "CMO" / "outputs"
PROFILE_DIR = SCRIPT_DIR / ".browser_profile"
THUMB_DIR = SCRIPT_DIR / "thumbnails"

NOTE_MY_NOTES_URL = "https://note.com/notes"
LOG_FILE = SCRIPT_DIR / ".thumbnail_attached.log"


def load_context(playwright):
    if not PROFILE_DIR.exists():
        sys.exit("初回ログインがまだです。 `python3 publish_to_note.py --login` を実行してください。")
    return playwright.chromium.launch_persistent_context(
        str(PROFILE_DIR),
        headless=False,
        channel="chrome",
        viewport={"width": 1280, "height": 900},
        args=["--disable-blink-features=AutomationControlled"],
    )


def extract_title(md_path: Path) -> str:
    text = md_path.read_text(encoding="utf-8")
    m = re.search(r"^## タイトル\s*\n```\s*\n(.+?)\n```", text, re.MULTILINE | re.DOTALL)
    if m:
        return m.group(1).strip().splitlines()[0]
    m = re.search(r"^#\s+note記事[:：]\s*(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else md_path.stem


def collect_images() -> list[Path]:
    if not THUMB_DIR.exists():
        sys.exit(
            f"画像フォルダが無い: {THUMB_DIR}\n"
            f"  mkdir -p {THUMB_DIR} で作成し、ChatGPT/Midjourney等で作った画像を入れてください。\n"
            "  命名例: 2026-06-01_富山ブラック.jpg"
        )
    return sorted(
        p for p in THUMB_DIR.iterdir()
        if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
    )


def best_article_for_image(img: Path, articles: list[Path]) -> Path | None:
    """画像名から最適な記事mdを返す。"""
    stem = img.stem  # 例: 2026-06-01_富山ブラック
    # 完全一致（拡張子違いだけ）
    for a in articles:
        if a.stem == stem:
            return a
    # 日付プレフィックス
    m = re.match(r"(\d{4}-\d{2}-\d{2})(?:_(.+))?$", stem)
    if not m:
        return None
    date, keyword = m.group(1), m.group(2)
    same_date = [a for a in articles if a.name.startswith(date)]
    if not same_date:
        return None
    if not keyword:
        return same_date[0] if len(same_date) == 1 else None
    # キーワードがタイトルに含まれる記事
    keyword_low = keyword.replace("_", "")
    for a in same_date:
        title = extract_title(a)
        if keyword_low in title or keyword in a.stem:
            return a
    return None


def already_done(article_stem: str) -> bool:
    if not LOG_FILE.exists():
        return False
    return any(line.strip() == article_stem for line in LOG_FILE.read_text(encoding="utf-8").splitlines())


def mark_done(article_stem: str):
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(article_stem + "\n")


def find_note_edit_url_by_title(page, title: str) -> str | None:
    """マイページから該当タイトルの記事URLを探す。"""
    page.goto(NOTE_MY_NOTES_URL)
    page.wait_for_load_state("networkidle", timeout=20000)
    # タイトルを部分一致で検索
    title_short = title.split("。")[0][:30]
    links = page.locator(f'a:has-text("{title_short}")')
    n = links.count()
    if n == 0:
        return None
    href = links.first.get_attribute("href") or ""
    if not href:
        return None
    if href.startswith("/"):
        href = "https://note.com" + href
    # 編集URL: /n/{id}/edit が標準パターン
    if "/edit" not in href:
        href = href.rstrip("/") + "/edit"
    return href


def attach_thumbnail(page, edit_url: str, image_path: Path, skip_existing: bool) -> str:
    """指定の編集URLで見出し画像を差し替えて更新。戻り値=状態文字列。"""
    page.goto(edit_url)
    page.wait_for_load_state("networkidle", timeout=20000)
    if "login" in page.url or "accounts.google.com" in page.url:
        return "NEEDS_LOGIN"

    # 既存サムネ判定（簡易）：見出し画像エリアに <img> があるか
    if skip_existing:
        try:
            existing = page.locator('[data-testid*="header"] img, [class*="eyecatch"] img, [class*="header"] img').first
            if existing.is_visible(timeout=1000):
                return "SKIPPED_EXISTING"
        except Exception:
            pass

    # 見出し画像エリアを開く
    try:
        page.locator(
            'button:has-text("見出し画像"), [aria-label*="見出し画像"], button:has-text("画像を追加")'
        ).first.click()
        page.wait_for_timeout(800)
    except Exception:
        pass

    # ファイル選択
    try:
        with page.expect_file_chooser() as fc:
            page.locator('input[type="file"]').first.click()
        fc.value.set_files(str(image_path))
        page.wait_for_timeout(2500)
    except Exception as e:
        return f"UPLOAD_FAIL:{e}"

    # 「適用」「決定」「保存」等のボタンがあれば押す
    for label in ("適用", "決定", "保存", "完了", "Done", "Apply"):
        try:
            btn = page.locator(f'button:has-text("{label}")').first
            if btn.is_visible(timeout=500):
                btn.click()
                page.wait_for_timeout(800)
                break
        except Exception:
            continue

    # 公開済み記事の編集後は「更新」ボタン（または公開設定→更新）
    page.wait_for_timeout(1500)
    try:
        update_btn = page.locator('button:has-text("更新"), button:has-text("公開設定")').last
        update_btn.click()
        page.wait_for_timeout(1500)
        # ダイアログがあれば再度押す
        confirm = page.locator('button:has-text("更新"), button:has-text("公開する")').last
        if confirm.is_visible(timeout=2000):
            confirm.click()
        page.wait_for_timeout(2500)
    except Exception as e:
        return f"UPDATE_FAIL:{e}"

    return "OK"


def main():
    ap = argparse.ArgumentParser(description="note 公開済み記事に後追いでサムネを添付")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--confirm", action="store_true", help="1件ずつ目視確認")
    ap.add_argument("--filter", default="", help="部分一致フィルタ（画像ファイル名）")
    ap.add_argument("--skip-existing", action="store_true", help="既にヘッダー画像がある記事はスキップ")
    args = ap.parse_args()

    images = collect_images()
    if args.filter:
        images = [i for i in images if args.filter in i.name]
    if not images:
        sys.exit("対象画像なし。 thumbnails/ にファイルを置くか --filter を見直してください。")

    articles = sorted(ARTICLES_DIR.glob("2026-*_note記事_*.md"))

    print(f"画像: {len(images)}枚 / 記事: {len(articles)}本\n")

    mapping = []
    for img in images:
        art = best_article_for_image(img, articles)
        if art is None:
            print(f"  ?  マッチ無し: {img.name}")
            continue
        mapping.append((img, art))
        print(f"  +  {img.name}  →  {art.name}")

    if not mapping:
        sys.exit("マッチした記事がありません。命名規則を確認してください。")

    if args.dry_run:
        print(f"\n(dry-run) 実行候補: {len(mapping)}件")
        return

    print(f"\n実行候補: {len(mapping)}件")
    if args.confirm:
        ans = input("続行する？ [y/N] ").strip().lower()
        if ans != "y":
            sys.exit("中断")

    with sync_playwright() as p:
        ctx = load_context(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        success = 0
        skipped = 0
        failed = []
        for img, art in mapping:
            if already_done(art.stem):
                print(f"⏭  既処理: {art.stem}")
                skipped += 1
                continue
            title = extract_title(art)
            print(f"\n→ {art.stem}\n  title: {title}\n  image: {img.name}")
            edit_url = find_note_edit_url_by_title(page, title)
            if not edit_url:
                print(f"  ✗ note上で記事URLが見つからない（タイトル不一致 or 未公開？）")
                failed.append((art.stem, "URL_NOT_FOUND"))
                continue
            print(f"  edit: {edit_url}")
            if args.confirm:
                ans = input("  この記事に貼り付けますか？ [y/N] ").strip().lower()
                if ans != "y":
                    print("  スキップ")
                    continue
            result = attach_thumbnail(page, edit_url, img, args.skip_existing)
            if result == "OK":
                print(f"  ✓ 完了")
                mark_done(art.stem)
                success += 1
            elif result == "SKIPPED_EXISTING":
                print(f"  ⏭  既存サムネあり（スキップ）")
                skipped += 1
            elif result == "NEEDS_LOGIN":
                sys.exit("  ✗ ログインセッション切れ。 `python3 publish_to_note.py --login` を実行してください。")
            else:
                print(f"  ✗ 失敗: {result}")
                failed.append((art.stem, result))
            page.wait_for_timeout(3000)

        print("\n" + "=" * 50)
        print(f"成功: {success} / スキップ: {skipped} / 失敗: {len(failed)}")
        for stem, why in failed:
            print(f"  - {stem}: {why}")
        ctx.close()


if __name__ == "__main__":
    main()
