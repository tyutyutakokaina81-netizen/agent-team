"""
04_publish_note.py — note へ自動公開（Playwright）

note には公式の投稿APIが無いため、ブラウザ自動化で公開する。
既存「柱D」と同じ「初回ログインのみ人手」モデル：
  1. 初回は `python 04_publish_note.py login` でブラウザを開き手動ログイン
     → セッション(storage_state)を .sessions/note_state.json に保存
  2. 以降は保存セッションで自動的に新規記事を作成・本文/サムネ投入・公開

認証情報はコードに書かず、セッションファイル(.sessions/・gitignore)で保持。
"""

import re
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

BASE = Path(__file__).resolve().parent.parent
SESSION_DIR = Path(__file__).resolve().parent / ".sessions"
STATE_FILE = SESSION_DIR / "note_state.json"
NOTE_NEW = "https://note.com/notes/new"
NOTE_LOGIN = "https://note.com/login"


def _split_front_matter(article_path: Path):
    text = article_path.read_text(encoding="utf-8")
    m = re.search(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    fm, body = {}, text
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                fm[k.strip()] = v.strip().strip('"')
        body = m.group(2).strip()
    return fm, body


def login():
    """初回のみ：手動ログインしてセッションを保存。"""
    if sync_playwright is None:
        raise RuntimeError("playwright 未インストール。requirements.txt を参照。")
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto(NOTE_LOGIN)
        print("ブラウザでログインを完了したら、ここで Enter を押してください…")
        input()
        ctx.storage_state(path=str(STATE_FILE))
        print(f"[login] セッション保存: {STATE_FILE}")
        browser.close()


def publish(article_path: Path, thumbnail_path: Path | None = None, headless=True):
    """保存セッションで note に下書き作成→サムネ添付→公開。

    注: noteのDOM/セレクタは変更されうる。下記セレクタは要メンテ。
    安全側に倒し、最終公開前に確認したい場合は headless=False + 公開ボタン手動。
    """
    if sync_playwright is None:
        raise RuntimeError("playwright 未インストール。requirements.txt を参照。")
    if not STATE_FILE.exists():
        raise RuntimeError("セッション未保存。まず `python 04_publish_note.py login` を実行。")

    fm, body = _split_front_matter(article_path)
    title = fm.get("title", article_path.stem)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(storage_state=str(STATE_FILE))
        page = ctx.new_page()
        page.goto(NOTE_NEW)
        page.wait_for_load_state("networkidle")

        # タイトル入力（プレースホルダ「記事タイトル」想定）
        page.get_by_placeholder("記事タイトル").fill(title)

        # 本文入力（エディタ本体にフォーカスして投入）
        editor = page.locator("[contenteditable='true']").last
        editor.click()
        editor.type(body)

        # サムネ（見出し画像）添付 — UI操作はnote側仕様に合わせ要調整
        if thumbnail_path and Path(thumbnail_path).exists():
            try:
                page.get_by_text("見出し画像を追加").click()
                page.set_input_files("input[type='file']", str(thumbnail_path))
                page.wait_for_timeout(1500)
                # 画像トリミングの「保存」等が出る場合はここでクリック
            except Exception as e:
                print(f"[warn] サムネ添付に失敗（手動添付してください）: {e}")

        # 公開：誤爆防止のため既定では下書き保存に留め、公開は確認後に
        print("[publish] 下書きを作成しました。公開ボタンは確認後に押してください。")
        page.wait_for_timeout(2000)
        ctx.storage_state(path=str(STATE_FILE))
        browser.close()


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "login":
        login()
    else:
        art = Path(sys.argv[1])
        thumb = Path(sys.argv[2]) if len(sys.argv) > 2 else None
        publish(art, thumb, headless=False)
