#!/usr/bin/env python3
"""公開済みnoteの本文末尾に「有料note案内」を追記する（Mac・Playwright）。

`gen_footers.py --paid-only` が作った文面を、note の編集画面を開いて末尾に貼り、
更新まで済ませる。43本を手で開いて貼る作業をなくすためのもの。

    # 1) 何をするかだけ見る（ブラウザは開くが保存しない・既定）
    python3 CDO/outputs/note_footer/append_paid_footer.py

    # 2) まず2本だけ本当に追記して、note の画面で結果を確かめる
    python3 CDO/outputs/note_footer/append_paid_footer.py --apply --limit 2

    # 3) 問題なければ残り全部
    python3 CDO/outputs/note_footer/append_paid_footer.py --apply

安全側の作り：
  - 既定は dry-run。`--apply` を付けたときだけ保存する。
  - 追記のみ。既存の本文は読みも消しもしない。
  - 既に同じ有料URLが本文にあればスキップ（二重貼り防止）。
  - 有料note自体は対象外（PAID_NOTE_IDS で明示除外）。価格や有料ラインに触れる余地をなくす。
  - 済んだ分は state ファイルに記録。中断しても続きから再開でき、二重実行しても貼り直さない。
"""
import argparse
import json
import sys
import time
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("Playwrightが未インストールです。`bash CDO/outputs/note_publisher/setup.sh` を実行してください。")

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
MANIFEST = HERE / "paid_footer_manifest.json"
STATE = HERE / ".append_state.json"
PROFILE_DIR = Path.home() / ".note_publisher_profile"
EDITOR = "https://editor.note.com/notes/{}/edit/"

# 有料note本体。ここを編集対象に入れない（価格・有料ラインに触れる事故を構造的に防ぐ）。
PAID_NOTE_IDS = {"n589f9a38d45f", "n6fae4ac8e59a", "n9d31ee9d3b0a"}


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"done": [], "failed": []}


def save_state(st: dict) -> None:
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")


def launch(playwright):
    """publish_to_note.py と同じ永続プロファイルを使う（ログインを共用）。"""
    if not PROFILE_DIR.exists() or not any(PROFILE_DIR.iterdir()):
        sys.exit("初回ログインがまだです。"
                 "`python3 CDO/outputs/note_publisher/publish_to_note.py --login` を先に実行してください。")
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


def body_locator(page):
    """本文エディタ（note は contenteditable）。"""
    return page.locator('div[contenteditable="true"], [role="textbox"]').first


def append_footer(page, note_id: str, footer: str, apply: bool) -> str:
    page.goto(EDITOR.format(note_id), wait_until="domcontentloaded")
    page.wait_for_timeout(2500)

    if "login" in page.url or "signin" in page.url:
        return "fail:ログインしていない（--login を実行してください）"

    body = body_locator(page)
    try:
        body.wait_for(state="visible", timeout=15000)
    except Exception:
        return "fail:本文エディタが見つからない（記事が存在しないか、UIが変わった）"

    # 二重貼り防止：本文に同じURLが既にあるか。
    paid_url = next((ln for ln in footer.splitlines() if ln.startswith("https://note.com/")), "")
    if paid_url:
        try:
            if paid_url in body.inner_text(timeout=5000):
                return "skip:既に案内あり"
        except Exception:
            pass  # 読めなくても追記自体は安全（末尾に足すだけ）

    if not apply:
        return "dry-run:ここで追記して更新する"

    # 末尾にカーソルを置いてから流し込む。改行は type だと段落が崩れやすいので1行ずつ。
    body.click()
    page.keyboard.press("Control+End")
    page.keyboard.press("Meta+ArrowDown")  # macOS
    page.wait_for_timeout(300)
    for line in footer.splitlines():
        page.keyboard.press("Enter")
        if line:
            page.keyboard.type(line, delay=8)
    page.wait_for_timeout(1200)

    # 「更新する」→ 確認画面でもう一度。公開済み記事なので新規公開ではなく更新。
    clicked = False
    for label in ("更新する", "公開に進む", "保存"):
        try:
            btn = page.locator(f'button:has-text("{label}")').first
            if btn.is_visible(timeout=2500):
                btn.click()
                page.wait_for_timeout(2500)
                clicked = True
                break
        except Exception:
            continue
    if not clicked:
        return "fail:更新ボタンが見つからない（本文は入力済み・画面で手動更新してください）"

    for label in ("更新する", "投稿する", "OK"):
        try:
            c = page.locator(f'[role="dialog"] >> button:has-text("{label}")').last
            if c.is_visible(timeout=1500):
                c.click()
                page.wait_for_timeout(2000)
                break
        except Exception:
            continue

    page.wait_for_timeout(1500)
    return "ok:更新した"


def main():
    ap = argparse.ArgumentParser(description="公開済みnoteに有料note案内を追記する")
    ap.add_argument("--apply", action="store_true", help="実際に保存する（既定は dry-run）")
    ap.add_argument("--limit", type=int, default=0, help="先頭N本だけ処理（まず少数で試す用）")
    ap.add_argument("--only", help="このnote ID 1本だけ処理")
    ap.add_argument("--retry-failed", action="store_true", help="前回失敗した分だけやり直す")
    args = ap.parse_args()

    if not MANIFEST.exists():
        sys.exit(f"マニフェストがありません: {MANIFEST}\n"
                 "先に `python3 CDO/outputs/note_footer/gen_footers.py --paid-only` を実行してください。")
    items = json.loads(MANIFEST.read_text(encoding="utf-8"))
    st = load_state()

    if args.only:
        items = [i for i in items if i["note_id"] == args.only]
    elif args.retry_failed:
        items = [i for i in items if i["note_id"] in st["failed"]]
    else:
        items = [i for i in items if i["note_id"] not in st["done"]]
    items = [i for i in items if i["note_id"] not in PAID_NOTE_IDS]
    if args.limit:
        items = items[:args.limit]

    if not items:
        print("対象がありません（すべて処理済みか、条件に合う記事なし）。")
        return

    mode = "本番（保存する）" if args.apply else "dry-run（保存しない・既定）"
    print(f"🚦 モード: {mode} ／ 対象 {len(items)} 本")
    if not args.apply:
        print("   実際に追記するには --apply を付けてください。まずは --apply --limit 2 を推奨します。\n")

    ok = skip = fail = 0
    try:
        pw_cm = sync_playwright()
        p = pw_cm.__enter__()
    except Exception as e:
        # ここで落ちると従来は「結果行なし」になり原因が分からなかった → 必ず結果行を出す
        print(f"\n=== 結果: 更新 0 / スキップ 0 / 失敗 0（起動失敗: {type(e).__name__}: {e}） ===")
        sys.exit("Playwright 起動に失敗（ブラウザ未導入/プロフィールロック等）。")
    try:
        try:
            ctx = launch(p)
        except Exception as e:
            print(f"\n=== 結果: 更新 0 / スキップ 0 / 失敗 0（コンテキスト起動失敗: {type(e).__name__}: {e}） ===")
            print("→ 既存プロフィールのロック/ログイン切れの可能性。`--login` で再ログインしてください。")
            return
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        for n, it in enumerate(items, 1):
            print(f"--- [{n}/{len(items)}] {it['title'][:38]}")
            try:
                r = append_footer(page, it["note_id"], it["footer"], args.apply)
            except Exception as e:
                r = f"fail:{type(e).__name__}"
            print(f"    {r}")
            if r.startswith("ok"):
                ok += 1
                st["done"].append(it["note_id"])
                st["failed"] = [x for x in st["failed"] if x != it["note_id"]]
                save_state(st)
            elif r.startswith("skip"):
                skip += 1
                st["done"].append(it["note_id"])
                save_state(st)
            elif r.startswith("fail"):
                fail += 1
                if it["note_id"] not in st["failed"]:
                    st["failed"].append(it["note_id"])
                save_state(st)
            time.sleep(1.5)  # note 側に連続負荷をかけない
        ctx.close()
    finally:
        try:
            pw_cm.__exit__(None, None, None)
        except Exception:
            pass

    print(f"\n=== 結果: 更新 {ok} / スキップ {skip} / 失敗 {fail} ===")
    if fail:
        print("失敗分は `--retry-failed` でやり直せます。")
    if not args.apply:
        print("※ dry-run だったので何も保存していません。")


if __name__ == "__main__":
    main()
