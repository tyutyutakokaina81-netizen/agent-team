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
    return set(load_swept_at().keys())


def load_swept_at() -> dict:
    """url -> 最後に巡回した日時(文字列)。同じ url が何度も並ぶので**最後の行**を採る。"""
    if not SWEEP.exists():
        return {}
    out = {}
    with SWEEP.open(encoding="utf-8") as fh:
        for row in csv.reader(fh, delimiter="\t"):
            if len(row) >= 2 and row[0].startswith("https://"):
                out[row[0]] = row[1]
    return out


def _days_since(ts: str) -> float:
    """巡回日時から何日経ったか。読めなければ大きい値＝『ずっと見ていない』扱いにする
    （読めないことを『最近見た』に倒すと、見落としが静かに続く）。"""
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            return (datetime.datetime.now() - datetime.datetime.strptime(ts[:19], fmt)).total_seconds() / 86400
        except Exception:
            continue
    return 9999.0


def targets_from_registry(limit: int, include_swept: bool, restale_days: float = 0.0):
    """巡回する記事を選ぶ。

    ★2026-10-06 に直したところ:
      これまでは **一度巡回した記事を二度と見に行かなかった**（`url in swept` で捨てていた）。
      2026-10-04 に全253本の巡回が終わったので、**それ以降に来たコメントは構造的に見えない**。
      実際この日、オーナーには見えているコメントを「新規0件」と報告していた。
      `--rescan` は最初から在ったが、日次では一度も使われていなかった＝
      **道具はあったのに繋がっていない**（マガジン196本・英語141本・フォロー導線と同じ型）。
      `restale_days` を渡すと、**その日数より前に見たきりの記事を見直す**。
      並べ方は「一度も見ていない」→「最後に見たのが古い順」。
    """
    try:
        entries = json.loads(REGISTRY.read_text(encoding="utf-8"))
    except Exception as e:
        sys.exit(f"✗ published_registry.json を読めない: {e}")
    swept_at = {} if include_swept else load_swept_at()
    fresh, stale = [], []
    for e in entries:
        url = (e.get("url") or "").strip()
        if not url.startswith("https://note.com/"):
            continue
        if url not in swept_at:
            fresh.append((url, e.get("title", "")))
            continue
        if restale_days > 0:
            age = _days_since(swept_at[url])
            if age >= restale_days:
                stale.append((age, url, e.get("title", "")))
    fresh.reverse()                      # 新しい記事から（registry は古い順に積まれている）
    stale.sort(key=lambda x: -x[0])      # 最後に見たのが古い順
    out = fresh + [(u, t) for _a, u, t in stale]
    return out[:limit] if limit > 0 else out


_STATE_JS = """() => {
  try {
    const s = window.__NUXT__ && window.__NUXT__.state;
    const nd = s && s.noteDetail && s.noteDetail.data;
    if (!nd) return null;
    return {status: nd.status || null,
            commentCount: (typeof nd.commentCount === 'number') ? nd.commentCount : null};
  } catch (e) { return null; }
}"""


# ★2026-10-06: **この経路が丸ごと死んでいた。**
#   note は Nuxt から **Next.js** に移っていて、`window.__NUXT__` は**1件も無い**
#   （保存HTMLで確認: __NUXT__=0 / self.__next_f=1）。つまり上の _STATE_JS は常に null を返し、
#   「確実に読める」はずの経路が使われないまま、推測で書いた DOM セレクタだけに頼っていた。
#   その結果が **セレクタ外れ12件**（2026-10-07 の朝の便）。
#   Next.js の埋め込みデータには `\"commentCount\":N` と `\"status\":\"published\"` が入っている。
#   ただし**おすすめ記事の分も一緒に入っている**ので、数だけ拾うと他人の記事の数を読む。
#   直前に現れる `\"key\":\"nXXXXXXXXXXXX\"` で**その記事自身のものだけ**を取る。
#   保存済みHTML 9件で検証済み（公開2件は自記事のcommentCountを正しく0と読み、下書きは0件）。
_OWN_KEY_RE = r'\\"key\\":\\"(n[0-9a-f]{12})\\"'


def read_state_from_payload(html: str, note_key: str):
    """Next.js の埋め込みデータから、**その記事自身の** (status, commentCount) を取る。

    取れなければ (None, None)。**推測しない**＝分からないときは分からないと言う。
    """
    if not html:
        return None, None
    # 下書きは埋め込みデータ自体が無い（保存HTML 5件で確認）。画面に出る言葉で拾う＝
    # ここを落とすと「下書きだからコメント欄が無い」が「セレクタ外れ」に化ける。
    if "公開前の下書き" in html or "これは下書き" in html:
        return "draft", 0
    if not note_key:
        return None, None
    status = count = None
    for m in re.finditer(r'\\"commentCount\\":(\d+)', html):
        back = html[max(0, m.start() - 4000):m.start()]
        keys = re.findall(_OWN_KEY_RE, back)
        if keys and keys[-1] == note_key:
            count = int(m.group(1))
            st = re.search(r'\\"status\\":\\"([a-z]+)\\"', back[-4000:])
            if st:
                status = st.group(1)
            break
    return status, count


def read_note_state(page, note_key: str = ""):
    """埋め込み状態から (status, commentCount) を取る。取れなければ (None, None)。

    まず旧 Nuxt、次に現行の Next.js ペイロードを見る（note 側がまた変わっても片方は残る）。
    """
    try:
        st = page.evaluate(_STATE_JS)
    except Exception:
        st = None
    if st and (st.get("status") or st.get("commentCount") is not None):
        return st.get("status"), st.get("commentCount")
    try:
        html = page.content()
    except Exception:
        return None, None
    return read_state_from_payload(html, note_key)


# ★2026-10-08: **コメント本文はページに入っていない。**
#   保存した実ページで数えると `commentCount` は 2/1/1 と実在するのに、
#   本文の文字列はどこにも無い＝コメントは**別の通信であとから読み込まれている**。
#   DOM のセレクタを当て続けるより、**note 自身が使っている API をそのまま呼ぶ**ほうが確実で、
#   note の画面が変わっても壊れにくい。ログイン済みのブラウザから呼ぶので認証も通る。
#   どの形か確かめられない（A1）ので、**候補を順に試し、応答をそのまま保存する**。
#   保存さえされれば、次の実行で正しい形に直せる。
_API_PATHS = [
    "https://note.com/api/v3/notes/{key}/comments",
    "https://note.com/api/v1/note/{key}/comments",
    "https://note.com/api/v3/notes/{key}/comments?page=1",
    "https://note.com/api/v2/notes/{key}/comments",
]


def _walk_comments(obj, out):
    """応答の形が分からないので、**本文らしき文字列を持つ辞書**を再帰で拾う。
    キー名は決め打ちしない（note 側が変えても拾えるように）。"""
    if isinstance(obj, dict):
        body = None
        for k in ("body", "text", "comment", "message"):
            v = obj.get(k)
            if isinstance(v, str) and v.strip():
                body = v.strip()
                break
        if body:
            who = ""
            for k in ("user", "author", "creator"):
                u = obj.get(k)
                if isinstance(u, dict):
                    who = (u.get("nickname") or u.get("name") or "").strip()
                    h = (u.get("urlname") or u.get("key") or "").strip()
                    if h:
                        who = f"{who}(@{h})" if who else f"@{h}"
                    break
            if not who:
                who = (obj.get("nickname") or obj.get("name") or "").strip()
            out.append({"author": who, "text": body,
                        "id": str(obj.get("id") or obj.get("key") or "")})
        for v in obj.values():
            _walk_comments(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _walk_comments(v, out)
    return out


def fetch_comments_via_api(page, note_key: str, debug: bool = False):
    """note の API からコメントを取る。取れなければ [] と、保存した応答のパスを返す。"""
    if not note_key:
        return [], None
    saved = None
    for tpl in _API_PATHS:
        url = tpl.format(key=note_key)
        try:
            r = page.request.get(url, timeout=20000)
        except Exception:
            continue
        if r.status != 200:
            continue
        try:
            data = r.json()
        except Exception:
            continue
        if debug and saved is None:
            try:
                DEBUG_DIR.mkdir(parents=True, exist_ok=True)
                saved = DEBUG_DIR / f"api_{note_key}.json"
                saved.write_text(json.dumps(data, ensure_ascii=False, indent=1)[:200000],
                                 encoding="utf-8")
            except Exception:
                saved = None
        got = _walk_comments(data, [])
        # 記事本文そのもの（長すぎるもの）は除く＝コメントだけ残す
        got = [g for g in got if 1 <= len(g["text"]) <= 2000]
        if got:
            log(f"    API命中: {url} （{len(got)}件）")
            return got, saved
    return [], saved


def extract_comments(page, url, debug=False):
    """(comments, status) を返す。status は 'ok' / 'no-selector' / 'draft'（下書きで公開されていない）。"""
    _key = (re.search(r"/n/(n[0-9a-f]{12})", url) or [None, ""])[1] if "/n/n" in url else ""
    _st, _cc = read_note_state(page, _key)
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
        # ★2026-10-06: **件数が分かっているのに本文が取れない**のがいちばん危ない状態＝
        #   「0件」と報告されてコメントが放置される。件数を添えて別扱いにする。
        if _cc:
            # ★まず API を試す（DOM より確実）。取れたらそれを返す。
            _api, _saved = fetch_comments_via_api(page, _key, debug)
            if _api:
                _out = []
                for i, c in enumerate(_api):
                    _cid = c["id"] or f"{_key}-{i}-{c['text'][:20]}"
                    _out.append({"id": f"api_{_cid}", "author": c["author"] or "?",
                                 "text": c["text"]})
                return _out, "ok"
            log(f"    ⚠️ コメントが {_cc}件あるのに本文が取れない"
                f"（API応答を保存: {_saved}）")
            return [], f"has-{_cc}-unreadable"
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
    ap.add_argument("--restale", type=float, default=0.0,
                    help="この日数より前に見たきりの記事を見直す（0=見直さない）。"
                         "既に巡回した記事に後から来たコメントは、これを付けないと永久に見つからない")
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
        targets = targets_from_registry(args.limit, include_swept=args.rescan, restale_days=args.restale)
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
    unreadable, unreadable_urls = 0, []
    visited = found_total = no_selector = not_rendered = 0
    # 2026-09-22: 404等は**巡回では直らない**（削除/非公開/下書き/URL誤り）ので別に数える。
    # 同じ3本が毎日「未描画」に混ざっていて、何をすればいいのか分からない報告になっていた。
    not_found = 0

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
                # 2026-09-22: **HTTPステータスと最終URLを見る**。
                # 同じ3本（冷やしトマト/きのどくな/ひまわり）が毎日 NOT-RENDERED になっており、
                # 「note側のエラーか読み込み失敗」では原因が絞れない＝人が動けない報告だった。
                # 404 なら削除・非公開・下書き・URL誤りのいずれかで、**巡回では直らない**。
                # 200 なのに描画されないのとは対処がまったく違うので、最初から分けて数える。
                _resp = page.goto(url, timeout=45000, wait_until="domcontentloaded")
                _status = getattr(_resp, "status", None) if _resp else None
                _final = page.url
                # 2026-09-16: **「ページが描画されていない」を「セレクタ外れ」と報告していた**。
                # owner の Mac から --debug のHTMLを回収して判明:
                #   ・冷や汁 → note 側の upstream connect error（246バイトのエラーページ）
                #   ・他3本 → <title> が記事名でなく **note の汎用タイトル**のまま＝本文が未描画
                # どちらもセレクタとは無関係で、DOMが出来ていないだけだった。
                # 本文が現れるまで待ち、それでも来なければ NO-SELECTOR ではなく
                # **NOT-RENDERED** として区別する（原因の違う事故を同じ数字に混ぜない）。
                # 2026-09-17: 昨日入れたこの待ちは **偽陰性を出していた**。
                # `[class*='note-common-styles']` 等はSPAの殻にも存在するため、本文が空でも
                # 待ちが成功し、「未描画0件／セレクタ外れ6件」と報告していた。
                # 一方 --debug で保存したHTMLの <title> は **note の汎用タイトルのまま**＝
                # 記事が描画されていない動かぬ証拠だった。要素の有無より **title** が確実な判別材料。
                _NOTE_SHELL_TITLE = "note ――つくる、つながる、とどける。"
                _rendered = False
                for _ in range(15):
                    try:
                        if page.title().strip() != _NOTE_SHELL_TITLE:
                            _rendered = True
                            break
                    except Exception:
                        pass
                    page.wait_for_timeout(1000)
                if not _rendered:
                    if _status and _status >= 400:
                        not_found += 1
                        log(f"    ⚠️ NOT-FOUND（HTTP {_status}）＝削除・非公開・下書き・URL誤りのいずれか。"
                            f"**巡回では直らない。note の管理画面で確認が要る** / 最終URL: {_final}")
                    elif _final.rstrip("/") != url.rstrip("/"):
                        log(f"    ⚠️ REDIRECTED（HTTP {_status}）＝別のURLへ飛ばされた。"
                            f"記事が非公開/移動した可能性 / 最終URL: {_final}")
                    else:
                        log(f"    ⚠️ NOT-RENDERED（HTTP {_status}・URLは同じ）＝本文が描画されない。"
                            "セレクタの問題ではない")
                    if args.debug:
                        try:
                            DEBUG_DIR.mkdir(parents=True, exist_ok=True)
                            _n = re.sub(r"[^A-Za-z0-9]+", "_", url)[-60:] + ".html"
                            (DEBUG_DIR / _n).write_text(page.content(), encoding="utf-8")
                            log(f"    debug: {DEBUG_DIR / _n} を保存")
                        except Exception:
                            pass
                    not_rendered += 1
                    continue
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
            if status.startswith("has-") and status.endswith("-unreadable"):
                # ★2026-10-06: **いちばん危ない状態**＝コメントが在ることは分かっているのに
                #   本文が取れない。黙って 0件 と報告されると、返信されないまま放置される。
                try:
                    _n = int(status.split("-")[1])
                except Exception:
                    _n = 0
                unreadable += _n
                unreadable_urls.append((url, _n))
                log(f"    ❌ コメントが {_n}件 あるのに本文が取れない＝**返信待ちが放置される**。"
                    "--debug の保存HTMLを push すれば code が読んで返信文を書けます")
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
        f" / 未描画 {not_rendered} / **到達不能(404等) {not_found}** / 未公開(draft) {len(drafts)}"
        f" / **コメント有りだが本文が取れない {unreadable}** ===")
    for _u, _n in unreadable_urls:
        log(f"    ❌ 返信待ち {_n}件: {_u}")
    for _u in drafts:
        log(f"  未公開: {_u}  ← registryは公開済みとしているが note 上は下書き")
    if no_selector:
        log("→ セレクタ外れがある。`--debug` で保存したHTMLをリポジトリに置いて報告してください（code が直します）。")
    if not_rendered:
        log("→ 未描画がある。**セレクタの問題ではない**（note側のエラー/読み込み失敗）。"
            "同じ記事で繰り返すなら、その記事がブラウザで開けるかを人が確認すること。")


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
