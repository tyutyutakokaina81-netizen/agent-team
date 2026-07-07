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
PROFILE_DIR = Path.home() / ".note_publisher_profile"   # 永続プロファイル（OAuth状態も含めて全部保存）
NOTE_LOGIN_URL = "https://note.com/login"
NOTE_NEW_URL = "https://note.com/notes/new"
# note はエディタを editor.note.com へ移行中（2026-07 UI変更で /notes/new が一覧へリダイレクトする事象を確認）。
# 上から順に試し、タイトル欄が出た入口を採用する。
NOTE_NEW_URL_CANDIDATES = [
    "https://editor.note.com/new",
    "https://note.com/notes/new",
    "https://note.com/new",
]
# タイトル欄のセレクタ（旧UI input/textarea ＋ 新エディタの contenteditable も拾う）
TITLE_SELECTOR = (
    'textarea[placeholder="記事タイトル"], '  # 2026-07 新エディタ実測の本命
    'input[placeholder*="タイトル"], textarea[placeholder*="タイトル"], '
    '[contenteditable="true"][data-placeholder*="タイトル"], '
    'h1[contenteditable="true"], div[role="textbox"][aria-label*="タイトル"]'
)

AUTHOR_ID = "safe_canna441"
# 既公開記事のローカル台帳（公開成功のたびに本スクリプトが自動追記する）。
# note上の全記事はカバーしない（seedは台帳由来の一部のみ）ため、これは第1層の高速チェック。
# 第2層＝公開直前の note 検索（online_dedup_check）が最終ゲート。
REGISTRY_PATH = Path(__file__).resolve().parent / "published_registry.json"


# ---------- 重複ゲート（2026-06-12 重複公開インシデント対策・2026-07-04 実装） ----------

def _norm_title(s: str) -> str:
    """タイトル比較用の正規化（空白・記号を除去して casefold）"""
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[「」『』【】\[\]（）()｛｝{}、。，．,.!！?？:：;；・･\-ー—–〜~…※★☆|｜/／\\]", "", s)
    return s.casefold()


def _titles_match(a: str, b: str) -> bool:
    """正規化後の完全一致、または両者12文字以上での包含を重複とみなす"""
    na, nb = _norm_title(a), _norm_title(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    if len(na) >= 12 and len(nb) >= 12 and (na in nb or nb in na):
        return True
    return False


def load_registry() -> list:
    if REGISTRY_PATH.exists():
        try:
            return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def registry_check(title: str):
    """ローカル台帳との重複チェック。ヒットしたエントリ or None"""
    for e in load_registry():
        if _titles_match(title, e.get("title", "")):
            return e
    return None


def registry_add(title: str, url: str):
    """公開成功後に台帳へ自動追記（自己保全。次回以降の第1層ゲートになる）"""
    reg = load_registry()
    reg.append({
        "title": title,
        "url": url,
        "recorded_at": datetime.now().isoformat(timespec="seconds"),
    })
    REGISTRY_PATH.write_text(
        json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"📒 published_registry.json に追記しました（{len(reg)}件）")


# ---------- 題材(トピック)重複ゲート（2026-07-07 追加・タイトル違いの同一題材を捕捉） ----------
# 背景: タイトル照合だけでは「氷見牛は地元でも…」と「氷見牛は里山で…」のような
#   タイトル違いの同一題材を素通りさせた（実インシデント）。題材トークンでも判定する。
TOPIC_STOPWORDS = {
    "富山", "高岡", "氷見", "富山県", "高岡市", "氷見市", "富山市", "富山湾", "北陸",
    "保存版", "ガイド", "決定版", "完全版", "まとめ", "前編", "後編", "北前船",
}


def _topic_tokens(title: str) -> set:
    """タイトルから識別性のある題材トークン(漢字含む語 or 3字以上カタカナ語)を抽出。
    句読点・空白・記号で分割→末尾助詞を除去→ストップワード/短語を除外。"""
    segs = re.split(r"[、。，．,\.\s・「」『』【】\[\]（）()＝=＋+\-—–~〜…!！?？:：;；|｜/／]+", title or "")
    toks = set()
    for seg in segs:
        seg = re.sub(r"(?:は|が|の|を|に|へ|と|で|も|や|から|まで|など|という|だ|です)+$", "", seg)
        if len(seg) < 3 or seg in TOPIC_STOPWORDS:
            continue
        if re.search(r"[一-鿿]", seg) or re.fullmatch(r"[ァ-ヶー]{3,}", seg):
            toks.add(seg)
    return toks


def topic_conflict(title: str):
    """既公開記事と題材が重なるものを探す。(entry, 共有トークン集合) or None。
    判定=①識別トークンの完全一致 ②識別トークン(3字以上)が相手タイトルに包含
    （「バタバタ茶」が「バタバタ茶をもう一度」に含まれる等、句に埋もれた同一題材も捕捉）。"""
    new_toks = _topic_tokens(title)
    if not new_toks:
        return None
    new_norm = _norm_title(title)
    for e in load_registry():
        pt = e.get("title", "")
        pub_toks = _topic_tokens(pt)
        pub_norm = _norm_title(pt)
        shared = set(pub_toks & new_toks)  # ①完全一致
        for t in pub_toks:                 # ②既公開トークンが新タイトルに包含
            if len(t) >= 3 and _norm_title(t) in new_norm:
                shared.add(t)
        for t in new_toks:                 # ②新トークンが既公開タイトルに包含
            if len(t) >= 3 and _norm_title(t) in pub_norm:
                shared.add(t)
        if shared:
            return e, shared
    return None


def online_dedup_check(page, title: str):
    """note検索で自アカウント(safe_canna441)の同名記事を探す（最終ゲート・公開直前に実行）。
    返り値: 重複URLのリスト（空=重複なし）／ None=検索結果が確認できず判定不能。
    判定不能時の扱いは呼び出し側で fail-closed（公開中断）とする。"""
    from urllib.parse import quote
    try:
        page.goto(
            f"https://note.com/search?context=note&q={quote(title)}",
            wait_until="domcontentloaded", timeout=30000,
        )
        page.wait_for_timeout(3500)
        # 検索ページ自体が開けたかの確認（結果0件は正常＝重複なし）
        if "/search" not in page.url:
            return None
        links = page.locator(f'a[href*="/{AUTHOR_ID}/n/"]')
        n = links.count()
        nt = _norm_title(title)
        hits = []
        for i in range(min(n, 30)):
            a = links.nth(i)
            href = a.get_attribute("href") or ""
            try:
                card_text = a.inner_text(timeout=1500)
            except Exception:
                card_text = ""
            # カード文言（タイトル+抜粋）の中に記事タイトルが含まれていれば重複とみなす
            if card_text and nt and nt in _norm_title(card_text):
                m = re.search(r"/n/[a-z0-9]+", href)
                if m:
                    hits.append(f"https://note.com/{AUTHOR_ID}{m.group(0)}")
        return sorted(set(hits))
    except Exception as e:
        print(f"⚠️  note検索での重複確認に失敗: {e}")
        return None


# ---------- セッション管理（persistent profile方式 ＋ 本物Chrome優先） ----------

def _launch_with_chrome_then_chromium(playwright):
    """本物Chrome(channel='chrome')を優先、失敗時はChromiumにフォールバック。
    Google OAuth が Playwright/Chromium の自動化を検知するのを回避するため。"""
    try:
        ctx = playwright.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="chrome",   # 本物のGoogle Chromeを使う(macOS既存インストール想定)
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],  # webdriver検知も最小限抑制
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


def login():
    """初回のみ。本物Chromeを永続プロファイル付きで起動→手動ログイン。
    プロファイルにOAuth(Google経由)状態も含めて保存される。"""
    print("ブラウザを起動します。表示されたウィンドウで note にログインしてください。")
    print("ログイン完了後（noteのダッシュボードが見えたら）、このターミナルで Enter を押してください。")
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        ctx = _launch_with_chrome_then_chromium(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(NOTE_LOGIN_URL)
        input("ログインが完了したら Enter ...")
        ctx.close()
        print(f"✅ プロファイルを保存しました: {PROFILE_DIR}")


def load_context(playwright):
    """保存済み永続プロファイルでブラウザを起動（本物Chrome優先）"""
    if not PROFILE_DIR.exists() or not any(PROFILE_DIR.iterdir()):
        sys.exit("初回ログインがまだです。 `python3 publish_to_note.py --login` を実行してください。")
    return _launch_with_chrome_then_chromium(playwright)


# ---------- 記事mdから タイトル/本文/写真placeholder を抽出 ----------

def _count_photo_placeholders(md_path: Path) -> int:
    """本文ブロック内の [写真X] placeholder の個数を返す"""
    text = md_path.read_text(encoding="utf-8")
    body_m = re.search(r"##\s*本文.*?\n```\n(.+?)\n```", text, re.S)
    if not body_m:
        return 0
    return len(re.findall(r"\[(?:ここに)?写真[①②③④⑤⑥⑦⑧⑨⑩\d]", body_m.group(1)))


def find_latest_article(require_photos: bool = False):
    """CMO/outputs/ 配下のnote記事mdを返す。
    require_photos=True なら、写真placeholder「多い順 → 新しい順」で選ぶ。
    （同テーマで3点版/5点版が並存している場合、最新の充実版を自動採用）"""
    candidates = list(ARTICLES_DIR.glob("*_note記事_*.md"))
    if not candidates:
        sys.exit(f"記事が見つかりません: {ARTICLES_DIR}/*_note記事_*.md")
    if require_photos:
        with_photos = [
            (_count_photo_placeholders(c), c.stat().st_mtime, c)
            for c in candidates
        ]
        with_photos = [t for t in with_photos if t[0] > 0]
        if with_photos:
            with_photos.sort(key=lambda x: (-x[0], -x[1]))   # 写真多い順→新しい順
            return with_photos[0][2]
    # 単純に最新（mtime降順）
    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def find_article_by_date(target_date_str: str | None = None, allow_future: bool = False):
    """ファイル名の日付(YYYY-MM-DD)が target_date と一致するものを返す。
    無ければ「本日以前で最も新しい記事」を返す（未来日付ガード）。
    --by-date で明示指定 or allow_future=True のときだけ未来日付を許可する。
    2026-06-12 の未来日付公開インシデント以降、デフォルトでは未来日付を絶対に出さない。"""
    from datetime import date
    today = date.today().isoformat()
    if target_date_str is None:
        target_date_str = today
    dated = []
    for p in ARTICLES_DIR.glob("*_note記事_*.md"):
        m = re.match(r"(\d{4}-\d{2}-\d{2})_", p.name)
        if m:
            dated.append((m.group(1), p))
    if not dated:
        sys.exit(f"記事が見つかりません: {ARTICLES_DIR}/*_note記事_*.md")
    dated.sort()
    # exact match（指定日そのもの）
    for d, p in dated:
        if d == target_date_str:
            return p
    # 未来日付ガード：明示許可時のみ「次の未来」を返す
    if allow_future:
        for d, p in dated:
            if d > target_date_str:
                return p
    # デフォルト：未来は絶対に出さない。本日以前で最も新しいものを返す
    past = [(d, p) for d, p in dated if d <= today]
    if past:
        return past[-1][1]
    sys.exit("✗ 本日以前の日付の記事がありません（未来日付のみ）。誤公開防止のため中断します。"
             "\n  特定記事を出すなら --article <path> で明示指定してください。")


def parse_article(md_path: Path):
    """記事mdから タイトル・本文・写真placeholder順序・ハッシュタグ を取り出す"""
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

    # ハッシュタグ：「## ハッシュタグ」直下の ``` コードブロック → "#xxx" を抽出
    tags = []
    tag_m = re.search(r"##\s*ハッシュタグ.*?\n```\n(.+?)\n```", text, re.S)
    if tag_m:
        tags = [t.lstrip("#").strip() for t in re.findall(r"#\S+", tag_m.group(1))]

    return title, body, placeholders, tags


def find_thumbnail_for(md_path: Path) -> Path | None:
    """thumbnails/{記事stem}.{jpg|png|webp} があれば返す。"""
    thumbs = Path(__file__).resolve().parent / "thumbnails"
    for ext in ("jpg", "jpeg", "png", "webp", "JPG", "PNG"):
        p = thumbs / f"{md_path.stem}.{ext}"
        if p.exists():
            return p
    return None


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

def publish(md_path: Path, photo_dir: Path | None, draft: bool, text_only: bool = False,
            skip_online_dedup: bool = False, skip_topic_check: bool = False):
    title, body, placeholders, tags = parse_article(md_path)
    photos = collect_photos(photo_dir) if photo_dir else []

    # ---- 重複ゲート第1層：ローカル台帳（ブラウザを開く前に即判定） ----
    reg_hit = registry_check(title)
    if reg_hit:
        if draft:
            print(f"⚠️  台帳に既公開の記録があります: {reg_hit.get('url')}（ドラフトなので続行）")
        else:
            sys.exit(f"✗ 重複ゲート(台帳): このタイトルは既に公開済みです → {reg_hit.get('url')}\n"
                     f"  記事: {title}\n  公開を中断しました（published_registry.json 参照）。")

    # ---- 重複ゲート第0層：題材トークン（タイトル違いの同一題材を捕捉・2026-07-07） ----
    if not skip_topic_check:
        tc = topic_conflict(title)
        if tc:
            e, shared = tc
            msg = (f"✗ 題材重複ゲート: 既公開記事と同じ題材『{'・'.join(sorted(shared))}』です → {e.get('url')}\n"
                   f"  既公開: {e.get('title')}\n  今回  : {title}")
            if draft:
                print("⚠️ " + msg + "\n  （ドラフトなので続行。別題材なら --skip-topic-check）")
            else:
                sys.exit(msg + "\n  公開を中断しました。角度が異なり別記事として出す場合のみ --skip-topic-check を付けて再実行。")

    # thumbnails/{stem}.jpg があれば自動でサムネ＆--photos未指定時の見出し画像に使う
    auto_thumb = find_thumbnail_for(md_path)

    print(f"📝 記事: {md_path.name}")
    print(f"🏷️  タイトル: {title}")
    print(f"📸 写真placeholder: {len(placeholders)} 個")
    print(f"🖼️  実写ファイル: {len(photos)} 枚 ({photo_dir})")
    print(f"🖼️  自動サムネ候補: {auto_thumb.name if auto_thumb else 'なし'}")
    print(f"🔖 ハッシュタグ: {len(tags)} 個 ({', '.join(tags[:5])}{'…' if len(tags) > 5 else ''})")
    if text_only:
        print("📝 text-onlyモード: 写真placeholderを除去してテキストのみ投稿します")

    if text_only:
        # placeholder行を消す（前後の空行も整える）
        body = re.sub(r"\n?\[(?:ここに)?写真[①②③④⑤⑥⑦⑧⑨⑩\d][^\]]*\]\n?", "\n\n", body)
        body = re.sub(r"\n{3,}", "\n\n", body).strip()
        placeholders = []  # 以後の写真処理を全部スキップ
        photos = []
    else:
        if placeholders and not photos:
            sys.exit("✗ 写真placeholderはあるが --photos に写真がありません。--text-onlyで写真無し公開も可。")
        if photos and len(photos) < len(placeholders):
            sys.exit(f"✗ 写真不足: {len(placeholders)}枚必要 / {len(photos)}枚しかない。中断します。")

    with sync_playwright() as p:
        ctx = load_context(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        # ---- 重複ゲート第2層：note検索（公開時のみ・fail-closed） ----
        if not draft:
            if skip_online_dedup:
                print("⚠️  --skip-online-dedup 指定: note検索での重複確認をスキップします（非推奨）")
            else:
                dup = online_dedup_check(page, title)
                if dup is None:
                    ctx.close()
                    sys.exit("✗ 重複ゲート: note検索で重複確認ができませんでした（fail-closed で公開中断）。\n"
                             "  note検索UIの変更/回線不調の可能性。目視で重複なしを確認できた場合のみ\n"
                             "  --skip-online-dedup を付けて再実行してください。")
                if dup:
                    ctx.close()
                    sys.exit(f"✗ 重複ゲート(note検索): 同タイトルの公開記事が既にあります → {', '.join(dup)}\n"
                             f"  記事: {title}\n  公開を中断しました。")
                print("✅ 重複ゲート通過（note検索でヒットなし）")

        # ダイアログ内のボタンだけを対象にする（2026-07-03実測：新エディタ本体に常設の
        # 「閉じる」ボタンがあり、page全体からhas-textで拾うと誤クリック→一覧へ離脱＝全滅の真因だった）
        DIALOG_SCOPE = '[role="dialog"], [aria-modal="true"], .ReactModal__Content, .m-modal, .o-modal'

        def close_dialogs():
            # 被っているダイアログ（下書き復元・通知許可・お知らせ等）を閉じる
            for _ in range(3):
                try:
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(250)
                except Exception:
                    pass
            for label in ("閉じる", "あとで", "スキップ", "今はしない", "×"):
                try:
                    b = page.locator(f'{DIALOG_SCOPE} >> button:has-text("{label}")').first
                    if b.is_visible(timeout=300):
                        b.click()
                        page.wait_for_timeout(300)
                except Exception:
                    pass

        # エディタ入口を順に試す（2026-07 UI変更対応）。タイトル欄が出た入口を採用。
        title_input = None
        for entry in NOTE_NEW_URL_CANDIDATES:
            try:
                # 新エディタはSPAで networkidle が発火しない（2026-07実測）→ domcontentloaded で進み、
                # /new → /notes/<id>/edit への自動リダイレクト＋ProseMirrorマウントは wait_for_selector 側で待つ。
                page.goto(entry, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(1500)
            except Exception:
                continue
            if "accounts.google.com" in page.url or "login" in page.url:
                sys.exit("✗ note にログインしていない状態です。 `python3 publish_to_note.py --login` を再実行してください。")
            cand = page.locator(TITLE_SELECTOR).first
            try:
                # まずタイトル欄を素直に待つ（正常時はダイアログ処理を呼ばない＝誤クリック事故ゼロ）。
                # リダイレクト(/new→/notes/<id>/edit)＋ProseMirrorマウントに時間がかかるため長めに待つ（実測対応）
                cand.wait_for(state="visible", timeout=20000)
                title_input = cand
                print(f"🚪 エディタ入口: {entry} → {page.url}")
                break
            except Exception:
                pass
            # タイトル欄が出ない時だけ、ダイアログが被っている可能性を潰して再確認
            close_dialogs()
            try:
                cand.wait_for(state="visible", timeout=5000)
                title_input = cand
                print(f"🚪 エディタ入口: {entry} → {page.url}（ダイアログ除去後）")
                break
            except Exception:
                continue

        # どの入口でも出なければ、旧入口でもう一度だけ長めに待つ（回線遅延ケース）
        if title_input is None:
            page.goto(NOTE_NEW_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1500)
            close_dialogs()
            title_input = page.locator(TITLE_SELECTOR).first
        try:
            title_input.wait_for(state="visible", timeout=30000)
        except Exception:
            print("⚠️  タイトル入力欄が見つかりませんでした。")
            print(f"    現在のURL: {page.url}")
            print("    考えられる原因：noteのログイン切れ／画面にダイアログが残っている／note側のUI変更。")
            print(f"    （この記事のタイトル: {title}）")
            # 対話実行(オーナー)なら開いたまま止めて手動継続できるように。
            # 非対話実行(cowork自動)ならハングさせず失敗(rc=2)で返す。
            if sys.stdin.isatty():
                print("    ブラウザは開いたままにします。画面を確認し、必要なら手動で投稿してください。")
                input("確認したら Enter で閉じる ...")
            ctx.close()
            sys.exit(2)
        title_input.click()
        title_input.fill(title)
        print("✅ タイトル入力完了")

        # 本文エディタにフォーカス
        editor = page.locator('div[contenteditable="true"]').first
        editor.click()

        # 本文を写真placeholderで分割しながら、テキスト→写真→テキスト... で挿入
        # 改行を確実に保持するため、段落ごとに insert_text → Enter
        segments = split_body_by_photo_placeholders(body)
        for kind, val in segments:
            if kind == "text":
                # \n\n で段落に分け、各段落ごとに insert_text → Enter
                paragraphs = val.split("\n")
                for i, para in enumerate(paragraphs):
                    if para:
                        page.keyboard.insert_text(para)
                    if i < len(paragraphs) - 1:
                        page.keyboard.press("Enter")
                        page.wait_for_timeout(30)
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

        # サムネ（見出し画像）：優先順位 = --photos の写真① > thumbnails/{stem}.jpg
        thumb_to_use = photos[0] if photos else auto_thumb
        if thumb_to_use:
            try:
                # 2026-07-03 実測: 新エディタ(editor.note.com)の見出し画像は
                #   ①上部 見出し画像エリアの button[aria-label="画像を追加"] を押す
                #     → パネル(「画像をアップロード / 推奨サイズ：1280×670px」)が開く
                #   ②「画像をアップロード」を押すとOSのファイル選択が開く(input[type=file]はDOMに存在しない)
                #     → expect_file_chooser で捕捉して set_files
                # 旧コードは存在しない input[type=file] を待って30秒Timeoutで失敗していた。
                page.locator(
                    'button[aria-label="画像を追加"], button:has-text("見出し画像"), [aria-label*="見出し画像"]'
                ).first.click()
                page.wait_for_timeout(800)
                with page.expect_file_chooser() as fc:
                    page.locator('button:has-text("画像をアップロード")').first.click()
                fc.value.set_files(str(thumb_to_use))
                page.wait_for_timeout(2500)  # アップロード＆トリミングダイアログ表示待ち
                # トリミング/位置調整ダイアログの確定（「保存」が本命）。
                # 2026-07-03実測: ページには「下書き保存」も存在するため、必ずダイアログ内に
                # スコープして誤クリック(下書き保存)を防ぐ。
                crop_dialog = '[role="dialog"], [aria-modal="true"], .ReactModal__Content'
                for label in ("保存", "適用", "決定", "完了", "この画像を挿入"):
                    try:
                        btn = page.locator(f'{crop_dialog} >> button:has-text("{label}")').last
                        if btn.is_visible(timeout=600):
                            btn.click()
                            page.wait_for_timeout(800)
                            break
                    except Exception:
                        continue
                print(f"✅ サムネ(見出し画像)に {thumb_to_use.name} を設定")
            except Exception as e:
                print(f"⚠️  サムネ自動設定に失敗: {e}（手動で見出し画像を設定）")

        # ---- 公開 or 下書き ----
        # 2026-07-03実測(新エディタ editor.note.com)：
        #   ・「公開に進む」で /publish/ 画面へ遷移
        #   ・その画面にハッシュタグ欄(placeholder=ハッシュタグを追加する)と最終ボタン「投稿する」がある
        #   ・旧UIの「公開する」ボタンは存在しない（＝旧コードは投稿ボタンを押せず公開未完だった）
        if draft:
            # 下書きはエディタ画面で自動保存済み。設定画面へは進まない。
            # （ハッシュタグ欄は /publish/ 画面のみに存在するため、下書きでは設定しない）
            print("\n📋 ドラフトモード：公開ボタンは押しません。画面で内容確認してください。")
            print(f"    （ハッシュタグ {len(tags)} 個は公開時に /publish/ 画面で設定されます）")
            if sys.stdin.isatty():
                input("Enterで閉じる ...")
        else:
            print("\n🚀 公開フロー：下書き保存→『公開に進む』→ ハッシュタグ →『投稿する』")
            # 0) 下書き保存で編集状態を確定させる。
            # 2026-07-03実測: 見出し画像を設定するとfill/insert_textでDOMは埋まっていても
            # note側の公開バリデーションが「タイトル、本文を入力してください」と誤判定し
            # /publish/ へ遷移しない。下書き保存を一度挟むと状態が確定して遷移できる。
            try:
                ds = page.locator('button:has-text("下書き保存")').first
                if ds.is_visible(timeout=2000):
                    ds.click()
                    page.wait_for_timeout(2500)
                    print("✅ 下書き保存で編集状態を確定")
            except Exception as e:
                print(f"⚠️  下書き保存クリック省略: {e}")
            # 1) 公開設定画面へ
            try:
                page.locator('button:has-text("公開に進む")').first.click()
                try:
                    page.wait_for_url("**/publish/**", timeout=15000)
                except Exception:
                    page.wait_for_timeout(3000)
            except Exception as e:
                print(f"⚠️  『公開に進む』クリック失敗: {e}")
            page.wait_for_timeout(1500)
            # 2) ハッシュタグ入力（/publish/ 画面）
            if tags:
                try:
                    tag_input = page.locator(
                        'input[placeholder*="ハッシュタグ"], input[placeholder*="タグ"]'
                    ).first
                    tag_input.wait_for(state="visible", timeout=8000)
                    for t in tags[:10]:
                        tag_input.click()
                        page.keyboard.type(t)
                        page.keyboard.press("Enter")
                        page.wait_for_timeout(200)
                    print(f"✅ ハッシュタグ {len(tags[:10])} 個を入力")
                except Exception as e:
                    print(f"⚠️  ハッシュタグ入力に失敗: {e}（手動で追加してください）")
            # 3) 投稿する（＝公開）。公開は1回のみ。
            page.wait_for_timeout(1000)
            try:
                pub = page.locator('button:has-text("投稿する")').first
                pub.wait_for(state="visible", timeout=10000)
                pub.click()
                page.wait_for_timeout(2500)
                # 確認ダイアログが出る場合のみ、ダイアログ内の確定ボタンを押す
                for lbl in ("投稿する", "公開する", "OK"):
                    try:
                        c = page.locator(f'[role="dialog"] >> button:has-text("{lbl}")').last
                        if c.is_visible(timeout=800):
                            c.click()
                            page.wait_for_timeout(1500)
                            break
                    except Exception:
                        continue
                page.wait_for_timeout(3000)
                print(f"✅ 公開リクエスト送信。最終URL: {page.url}")
                # 公開成功を台帳へ自動追記（次回以降の第1層ゲート）
                m = re.search(r"/n/[a-z0-9]+", page.url)
                registry_add(title, f"https://note.com/{AUTHOR_ID}{m.group(0)}" if m else page.url)
            except Exception as e:
                print(f"⚠️  公開ボタン(投稿する)自動クリック失敗: {e}")
                print(f"    現在URL: {page.url}")
                if sys.stdin.isatty():
                    input("画面で「投稿する」を押したら Enter ...")

        ctx.close()


# ---------- CLI ----------

def main():
    ap = argparse.ArgumentParser(description="note 自動公開ヘルパー")
    ap.add_argument("--login", action="store_true", help="初回セッション保存（手動ログイン）")
    ap.add_argument("--article", type=str, help="記事mdのパス（省略時は最新を自動選択）")
    ap.add_argument("--photos", type=str, help="写真ディレクトリ（photo_01.jpg, photo_02.jpg, ...）")
    ap.add_argument("--draft", action="store_true", help="公開ボタンを押さずに止める（最終確認用）")
    ap.add_argument("--text-only", action="store_true", help="写真placeholderを除去してテキストのみで公開（写真ファイル不要）")
    ap.add_argument("--by-date", default=None, metavar="YYYY-MM-DD",
                    help="ファイル名日付指定で選択。省略時は本日。--photos と排他")
    ap.add_argument("--latest-mtime", action="store_true",
                    help="ファイル名日付ではなくmtime最新を選択（旧デフォルト）")
    ap.add_argument("--allow-future", action="store_true",
                    help="未来日付の記事も公開対象に含める（既定では誤公開防止のため未来は除外）")
    ap.add_argument("--skip-online-dedup", action="store_true",
                    help="note検索での重複確認をスキップ（非推奨・目視確認済みの時のみ）")
    args = ap.parse_args()

    if args.login:
        login()
        return

    # 記事選択ロジック：
    #  --article 指定 → そのファイル
    #  --photos 指定 → 写真placeholderある記事優先（旧仕様、写真投稿向け）
    #  --latest-mtime → mtime最新
    #  デフォルト → ファイル名日付=本日 or 次の未来日付（CAO日次運用）
    if args.article:
        md_path = Path(args.article)
    elif args.photos:
        md_path = find_latest_article(require_photos=True)
    elif args.latest_mtime:
        md_path = find_latest_article(require_photos=False)
    else:
        md_path = find_article_by_date(args.by_date, allow_future=args.allow_future)
    if not md_path.exists():
        sys.exit(f"記事が見つかりません: {md_path}")

    photo_dir = Path(args.photos).expanduser() if args.photos else None
    publish(md_path, photo_dir, draft=args.draft, text_only=args.text_only,
            skip_online_dedup=args.skip_online_dedup, skip_topic_check=args.skip_topic_check)


if __name__ == "__main__":
    main()
