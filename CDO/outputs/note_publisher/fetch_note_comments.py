#!/usr/bin/env python3
"""note の公開記事からコメントを収集し ops/comments/pending.tsv に追記する（Stage1）。

★これは cowork / owner の Mac で動かす。code は note を閲覧できない(A1)。
★認証は publish_to_note.py と**同じ永続プロファイル** (~/.note_publisher_profile) を使う。
  ＝毎日の自動公開が動いている時点でログインは生きているので、新たな認証設定は要らない。

## なぜ code 側でこれを書くか
コメント返信要件(R6)は 2026-09-01 から**実績ゼロ**のまま滞留していた。滞留の理由は
「cowork が取得スクリプトを持っていない」ことであり、それは code が書けば解消する。
待つのではなく、code が制御できる側（スクリプトと日次への組み込み）を直す。

## 使い方
  python3 CDO/outputs/note_publisher/fetch_note_comments.py --limit 20          # 新しい記事から20本を巡回
  python3 CDO/outputs/note_publisher/fetch_note_comments.py --backlog           # backlog_targets.tsv の未スイープを対象
  python3 CDO/outputs/note_publisher/fetch_note_comments.py --url <記事URL>     # 1本だけ
  python3 CDO/outputs/note_publisher/fetch_note_comments.py --limit 3 --debug   # 取れない時にHTMLを保存

## 出力
  ops/comments/pending.tsv   : comment_id  article  author  lang  text  fetched_at
  ops/comments/_sweep.tsv    : url  swept_at  comments_found   （巡回済みの記録＝二重巡回を避ける）
  ops/comments/_debug/*.html : --debug 時のみ。**セレクタが1件も当たらなかったページ**を保存する。

## セレクタが当たらなかった場合
code は note の DOM を見られないため、セレクタは複数候補を順に試す方式にしてある。
すべて外れたら「0件」ではなく **NO-SELECTOR** としてログに出し、--debug で保存したHTMLを
リポジトリに置いて報告してほしい。次のセッションで code が実データからセレクタを直す。
（「0件でした」と「取れませんでした」を混同しないための作り。過去に『成功表示≠成果物あり』で
  何度も失敗しているため、ここは必ず区別する。）
"""
import argparse
import csv
import datetime
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
COMMENT_DIR = ROOT / "ops" / "comments"
PENDING = COMMENT_DIR / "pending.tsv"
SWEEP = COMMENT_DIR / "_sweep.tsv"
DEBUG_DIR = COMMENT_DIR / "_debug"
REGISTRY = ROOT / "CDO/outputs/note_publisher/published_registry.json"
PROFILE_DIR = Path.home() / ".note_publisher_profile"

# note の DOM は変わりうるので候補を順に試す。1つでも当たればそれを使う。
COMMENT_BLOCK_SELECTORS = [
    "[data-name='comment']",
    "div[class*='o-noteComment']",
    "div[class*='comment-list'] li",
    "section[class*='comment'] li",
    "article [class*='Comment'][class*='item']",
    "[class*='commentItem']",
]
AUTHOR_SELECTORS = ["[class*='userName']", "[class*='UserName']", "a[href^='/'][class*='name']", "a[href^='/']"]
BODY_SELECTORS = ["[class*='commentBody']", "[class*='CommentBody']", "[class*='body']", "p"]


def log(msg):
    print(msg, flush=True)


def detect_lang(text: str) -> str:
    """日本語文字を含めば ja、含まなければ en 扱い（それ以外は other）。"""
    if re.search(r"[぀-ヿ一-鿿]", text):
        return "ja"
    if re.search(r"[A-Za-z]", text):
        return "en"
    return "other"


def load_seen_comment_ids() -> set:
    ids = set()
    for f in (PENDING, COMMENT_DIR / "replies.tsv"):
        if not f.exists():
            continue
        with f.open(encoding="utf-8") as fh:
            for row in csv.reader(fh, delimiter="\t"):
                if row and not row[0].startswith("#") and row[0] != "comment_id":
                    ids.add(row[0])
    return ids


def load_swept_urls() -> set:
    if not SWEEP.exists():
        return set()
    with SWEEP.open(encoding="utf-8") as fh:
        return {r[0] for r in csv.reader(fh, delimiter="\t") if r and not r[0].startswith("#")}


def targets_from_registry(limit: int, include_swept: bool):
    try:
        entries = json.loads(REGISTRY.read_text(encoding="utf-8"))
    except Exception as e:
        sys.exit(f"✗ published_registry.json を読めない: {e}")
    swept = set() if include_swept else load_swept_urls()
    out = []
    for e in entries:
        url = (e.get("url") or "").strip()
        if not url.startswith("https://note.com/") or url in swept:
            continue
        out.append((url, e.get("title", "")))
    out.reverse()   # 新しい記事から（registry は古い順に積まれている）
    return out[:limit] if limit > 0 else out


# 2026-09-09: 初回のセレクタ外れ1件を cowork が --debug で保存し、その HTML を読んで分かったこと。
#   note のページには埋め込み状態 `noteDetail.data` があり、`status`（"published"/"draft"）と
#   `commentCount` を持っている。DOMのclass名を推測するより**これを読むほうが確実**で、しかも
#   「下書きだからコメント欄が無い」と「公開済みだがコメント0」を区別できる。
#   実際その1件は **registryに公開済みとして載っているのに note 上は draft** だった（冷やしトマト）。
_STATE_JS = """() => {
  try {
    const s = window.__NUXT__ && window.__NUXT__.state;
    const nd = s && s.noteDetail && s.noteDetail.data;
    if (!nd) return null;
    return {status: nd.status || null,
            commentCount: (typeof nd.commentCount === 'number') ? nd.commentCount : null};
  } catch (e) { return null; }
}"""


def read_note_state(page):
    """埋め込み状態から (status, commentCount) を取る。取れなければ (None, None)。"""
    try:
        st = page.evaluate(_STATE_JS)
    except Exception:
        return None, None
    if not st:
        return None, None
    return st.get("status"), st.get("commentCount")


def extract_comments(page, url, debug=False):
    """(comments, status) を返す。status は 'ok' / 'no-selector' / 'draft'（下書きで公開されていない）。"""
    _st, _cc = read_note_state(page)
    if _st == "draft":
        # 公開されていない記事＝コメント欄が無いのは当然。セレクタの問題ではない。
        return [], "draft"
    if _cc == 0:
        # 埋め込み状態が「コメント0」と言っている＝DOMを探すまでもなく確定。
        return [], "ok"
    blocks = []
    for sel in COMMENT_BLOCK_SELECTORS:
        try:
            found = page.query_selector_all(sel)
        except Exception:
            continue
        if found:
            blocks = found
            log(f"    selector命中: {sel} ({len(found)}ブロック)")
            break
    if not blocks:
        # コメント欄そのものが存在するかを見る。存在するのに0件＝本当にコメント無し。
        try:
            has_area = bool(page.query_selector("[class*='omment']"))
        except Exception:
            has_area = False
        if debug:
            DEBUG_DIR.mkdir(parents=True, exist_ok=True)
            name = re.sub(r"[^A-Za-z0-9]+", "_", url)[-60:] + ".html"
            (DEBUG_DIR / name).write_text(page.content(), encoding="utf-8")
            log(f"    debug: {DEBUG_DIR / name} を保存")
        return [], ("ok" if has_area else "no-selector")

    def first_text(el, selectors):
        for s in selectors:
            try:
                c = el.query_selector(s)
            except Exception:
                continue
            if c:
                t = (c.inner_text() or "").strip()
                if t:
                    return t
        return ""

    comments = []
    for i, el in enumerate(blocks):
        try:
            body = first_text(el, BODY_SELECTORS) or (el.inner_text() or "").strip()
        except Exception:
            continue
        body = re.sub(r"\s+", " ", body).strip()
        if not body:
            continue
        author = first_text(el, AUTHOR_SELECTORS)
        if author and body.startswith(author):
            body = body[len(author):].strip()
        if not body:
            continue
        # comment_id: note側のidが取れなければ URL+順番+本文先頭 で一意化する（再取得しても同じになる）
        cid = ""
        for attr in ("data-comment-id", "id", "data-id"):
            try:
                v = el.get_attribute(attr)
            except Exception:
                v = None
            if v:
                cid = f"{url.rsplit('/', 1)[-1]}#{v}"
                break
        if not cid:
            import hashlib
            cid = f"{url.rsplit('/', 1)[-1]}#h{hashlib.md5(body[:120].encode('utf-8')).hexdigest()[:10]}"
        comments.append({"id": cid, "author": author or "(不明)", "text": body})
    return comments, "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=10, help="巡回する記事数（0=全部）")
    ap.add_argument("--url", default="", help="この記事URLだけを対象にする")
    ap.add_argument("--backlog", action="store_true", help="未スイープの古い記事を優先する")
    ap.add_argument("--rescan", action="store_true", help="スイープ済みも対象に含める")
    ap.add_argument("--debug", action="store_true", help="セレクタが外れたページのHTMLを保存")
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("✗ playwright 未インストール（pip install playwright && playwright install chromium）")

    if not PROFILE_DIR.exists() or not any(PROFILE_DIR.iterdir()):
        sys.exit("✗ note 未ログイン。`python3 CDO/outputs/note_publisher/publish_to_note.py --login` を先に実行。")

    if args.url:
        targets = [(args.url, "")]
    else:
        targets = targets_from_registry(args.limit, include_swept=args.rescan)
        if args.backlog:
            targets = list(reversed(targets))   # 古い記事から
    if not targets:
        log("対象がありません（すべてスイープ済み）。")
        log("=== 結果: 巡回 0 / 新規コメント 0 / セレクタ外れ 0（対象なし＝正常） ===")
        return

    COMMENT_DIR.mkdir(parents=True, exist_ok=True)
    seen = load_seen_comment_ids()
    now = datetime.datetime.now().isoformat(timespec="seconds")
    new_rows, swept_rows, drafts = [], [], []
    visited = found_total = no_selector = 0

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR), channel="chrome", headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        ) if _chrome_ok(p) else p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR), headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        for url, title in targets:
            visited += 1
            log(f"[{visited}/{len(targets)}] {title[:28] or url}")
            try:
                page.goto(url, timeout=45000, wait_until="domcontentloaded")
                page.wait_for_timeout(2500)
                # コメント欄は下部にあるため一度最下部まで送る（遅延読み込み対策）
                page.mouse.wheel(0, 20000)
                page.wait_for_timeout(1500)
                comments, status = extract_comments(page, url, args.debug)
            except Exception as e:
                log(f"    ✗ 取得失敗: {e}")
                continue
            if status == "draft":
                drafts.append(url)
                log("    ⚠️ この記事は note 上で **下書き(draft)** ＝公開されていない。"
                    "published_registry.json の記載と食い違うので確認が要る")
                continue
            if status == "no-selector":
                no_selector += 1
                log("    ⚠️ NO-SELECTOR（コメント欄を特定できず＝0件と断定しない）")
                continue
            swept_rows.append([url, now, str(len(comments))])
            for c in comments:
                if c["id"] in seen:
                    continue
                seen.add(c["id"])
                found_total += 1
                new_rows.append([c["id"], url, c["author"], detect_lang(c["text"]), c["text"], now])
                log(f"    + 新規コメント {c['author']}: {c['text'][:40]}")
        ctx.close()

    if new_rows:
        header = not PENDING.exists() or PENDING.stat().st_size == 0
        with PENDING.open("a", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, delimiter="\t")
            if header:
                w.writerow(["comment_id", "article", "author", "lang", "text", "fetched_at"])
            w.writerows(new_rows)
    if swept_rows:
        header = not SWEEP.exists() or SWEEP.stat().st_size == 0
        with SWEEP.open("a", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, delimiter="\t")
            if header:
                w.writerow(["url", "swept_at", "comments_found"])
            w.writerows(swept_rows)

    # 結果行は**必ず**出す（対象0でも出す）。有料フッターで「結果行なし＝失敗扱い」の事故があったため。
    log(f"=== 結果: 巡回 {visited} / 新規コメント {found_total} / セレクタ外れ {no_selector}"
        f" / 未公開(draft) {len(drafts)} ===")
    for _u in drafts:
        log(f"  未公開: {_u}  ← registryは公開済みとしているが note 上は下書き")
    if no_selector:
        log("→ セレクタ外れがある。`--debug` で保存したHTMLをリポジトリに置いて報告してください（code が直します）。")


def _chrome_ok(p):
    """本物Chromeが使えるか事前に判定（publish_to_note.py と同じ方針）。"""
    try:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR), channel="chrome", headless=True)
        ctx.close()
        return True
    except Exception:
        return False


if __name__ == "__main__":
    main()
