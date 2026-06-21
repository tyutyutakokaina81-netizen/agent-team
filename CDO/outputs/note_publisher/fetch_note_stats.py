#!/usr/bin/env python3
"""
note ダッシュボードのアクセス数を自動取得する（オーナーのMacで実行）

publish_to_note.py と同じ永続Chromeプロファイル(~/.note_publisher_profile)を再利用する。
そのため publish_to_note.py --login を一度でも済ませていれば、追加ログインは不要。

note には公開APIが無いため、ダッシュボードが内部的に使う統計エンドポイントを
ログイン済みブラウザ越しに取得する（best-effort）。仕様変更で失敗した場合は
CAO/outputs/note_stats_raw.json に生データを残すので、それをコミット&プッシュすれば
リモートAIがパーサを直す。

使い方:
  python3 fetch_note_stats.py            # 上位20
  python3 fetch_note_stats.py --top 30
"""
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("Playwrightが未インストールです。note_publisher/setup.sh を実行してください。")

PROFILE_DIR = Path.home() / ".note_publisher_profile"
REPO_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = REPO_ROOT / "CAO" / "outputs"
# note ダッシュボードが使う内部統計エンドポイント（filter=all で全期間）
STATS_API = "https://note.com/api/v1/stats/pv?filter=all&page={page}"


def _launch(p):
    if not PROFILE_DIR.exists() or not any(PROFILE_DIR.iterdir()):
        sys.exit("初回ログインがまだです。先に `python3 publish_to_note.py --login` を実行してください。")
    try:
        return p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR), channel="chrome", headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
    except Exception:
        return p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR), headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )


def fetch_all(page, max_pages=20):
    """統計APIをページ送りで全部取る。生データとアイテム配列を返す。"""
    items, raw_pages = [], []
    for n in range(1, max_pages + 1):
        url = STATS_API.format(page=n)
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        text = page.evaluate("() => document.body.innerText")
        try:
            obj = json.loads(text)
        except Exception:
            raw_pages.append({"page": n, "non_json_head": (text or "")[:400]})
            print(f"⚠️  page{n}: JSONでない応答。noteのログインが切れている可能性があります。")
            print("    → `python3 publish_to_note.py --login` を再実行してから、もう一度お試しください。")
            break
        raw_pages.append(obj)
        data = obj.get("data", obj) if isinstance(obj, dict) else {}
        stats = (data.get("note_stats") or data.get("notes")
                 or data.get("noteStats") or [])
        if not stats:
            break
        items.extend(stats)
        if data.get("last_page") is True or data.get("isLastPage") is True:
            break
    return items, raw_pages


def norm(item):
    """APIアイテムから (タイトル, ビュー, スキ, コメント) を取り出す（キー名のゆらぎ吸収）"""
    title = (item.get("name") or item.get("title") or "(タイトル不明)")
    views = item.get("read_count", item.get("readCount", item.get("pv")))
    likes = item.get("like_count", item.get("likeCount"))
    comments = item.get("comment_count", item.get("commentCount"))
    return title, views, likes, comments


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=20)
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        ctx = _launch(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        # まずトップに寄ってから（cookie適用を確実にするため）
        try:
            page.goto("https://note.com/", wait_until="domcontentloaded", timeout=20000)
        except Exception:
            pass
        items, raw = fetch_all(page)
        ctx.close()

    (OUT_DIR / "note_stats_raw.json").write_text(
        json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    if not items:
        print("✗ 統計データを取得できませんでした。")
        print(f"  生データ: {OUT_DIR/'note_stats_raw.json'}")
        print("  → このファイルを `git add -A && git commit -m 'note raw' && git push` してください。")
        print("    リモートAIが中身を見てパーサを直します。")
        return

    rows = [norm(it) for it in items]
    rows.sort(key=lambda r: (r[1] is None, -(r[1] or 0)))  # ビュー降順（None最後）
    top = rows[:args.top]

    lines = [f"# note アクセス上位{args.top}（自動取得）", "",
             f"取得日時: {datetime.now().isoformat(timespec='minutes')}　／　取得記事数: {len(rows)}", "",
             "| 順位 | タイトル | ビュー | スキ | コメント |",
             "|---|---|---|---|---|"]
    for i, (t, v, l, c) in enumerate(top, 1):
        tt = str(t).replace("|", "｜")
        lines.append(f"| {i} | {tt} | {v if v is not None else '-'} | "
                     f"{l if l is not None else '-'} | {c if c is not None else '-'} |")
    md = "\n".join(lines) + "\n"
    (OUT_DIR / "note_stats_top20.md").write_text(md, encoding="utf-8")

    print(md)
    print(f"✅ 保存: {OUT_DIR/'note_stats_top20.md'}")
    print("▶ 次: git add -A && git commit -m 'note統計取得' && git push")


if __name__ == "__main__":
    main()
