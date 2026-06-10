#!/usr/bin/env python3
"""note の現在の投稿エディタが持つ ボタン/入力欄/ファイル入力 を一覧表示する診断ツール。

note が UI を変えるとセレクタが合わなくなり、サムネ・タグ・投稿ボタンが掴めなくなる。
このツールで「今のnoteに実在する要素名」を吸い出し、それを元にセレクタを直す。

前提: 既に publish_to_note.py --login でログイン済み（プロファイル保存済み）。

使い方:
  python3 inspect_note_editor.py
出力（このテキストをそのまま貼ってください）:
  - ボタンの文言一覧 / aria-label 一覧 / role=button 一覧 / input[type=file] の数
"""
from __future__ import annotations
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("Playwright未インストール。setup.sh を先に。")

PROFILE_DIR = Path.home() / ".note_publisher_profile"
NEW_POST = "https://note.com/notes/new"


def launch(p):
    for kw in ({"channel": "chrome"}, {}):
        try:
            return p.chromium.launch_persistent_context(
                str(PROFILE_DIR), headless=False,
                viewport={"width": 1280, "height": 900},
                args=["--disable-blink-features=AutomationControlled"], **kw)
        except Exception:
            continue
    raise RuntimeError("ブラウザ起動失敗")


def dump(page, label):
    print(f"\n========== {label} ==========")
    # ボタン文言
    texts = page.eval_on_selector_all(
        "button", "els => els.map(e => (e.innerText||'').trim()).filter(Boolean)")
    print("【button のテキスト】")
    for t in sorted(set(texts)):
        print("  -", t[:40])
    # aria-label
    arias = page.eval_on_selector_all(
        "[aria-label]", "els => els.map(e => e.getAttribute('aria-label')).filter(Boolean)")
    print("【aria-label】")
    for t in sorted(set(arias)):
        print("  -", t[:40])
    # role=button
    roles = page.eval_on_selector_all(
        "[role=button]", "els => els.map(e => (e.innerText||e.getAttribute('aria-label')||'').trim()).filter(Boolean)")
    print("【role=button】")
    for t in sorted(set(roles)):
        print("  -", t[:40])
    # file inputs
    nfile = len(page.query_selector_all('input[type=file]'))
    print(f"【input[type=file] の数】 {nfile}")
    # プレースホルダ（タグ欄探し）
    phs = page.eval_on_selector_all(
        "input,textarea", "els => els.map(e => e.getAttribute('placeholder')).filter(Boolean)")
    print("【placeholder】")
    for t in sorted(set(phs)):
        print("  -", t[:40])


def main():
    if not PROFILE_DIR.exists():
        sys.exit("未ログイン。先に python3 publish_to_note.py --login を実行。")
    with sync_playwright() as p:
        ctx = launch(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(NEW_POST)
        page.wait_for_timeout(6000)
        dump(page, "新規投稿エディタ (初期)")
        # 本文に少し入力してから（ボタンが増える場合がある）再ダンプ
        try:
            page.keyboard.type("テスト")
            page.wait_for_timeout(1500)
        except Exception:
            pass
        dump(page, "本文入力後")
        print("\n--- ここまで。上の出力を全部コピーして貼ってください ---")
        page.wait_for_timeout(1500)
        ctx.close()


if __name__ == "__main__":
    main()
