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

def publish(md_path: Path, photo_dir: Path | None, draft: bool, text_only: bool = False):
    title, body, placeholders, tags = parse_article(md_path)
    photos = collect_photos(photo_dir) if photo_dir else []

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
    publish(md_path, photo_dir, draft=args.draft, text_only=args.text_only)


if __name__ == "__main__":
    main()
