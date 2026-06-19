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

# 公開済みログ（冪等化＝同一記事の二重公開防止・2026-06-12 インシデント再発防止）
PUBLISH_LOG = Path(__file__).resolve().parent / "published_log.tsv"
# note 実態のタイトル一覧（オーナー/coworkが note のダッシュボードから書き出す・1行1タイトル）
#   → コンテナは note に到達できないため、note実態の重複判定はこのファイルで担保する。
TITLE_MANIFEST = Path(__file__).resolve().parent / "published_titles_manifest.txt"


# ---------- 冪等化（重複公開防止） ----------

def _published_stems() -> set[str]:
    """published_log.tsv に記録済みの記事stem集合を返す"""
    if not PUBLISH_LOG.exists():
        return set()
    stems = set()
    for line in PUBLISH_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            stems.add(line.split("\t", 1)[0])
    return stems


def already_published(md_path: Path) -> bool:
    return md_path.stem in _published_stems()


def _normalize_title(t: str) -> str:
    """タイトル完全一致判定用の正規化：前後空白除去＋全空白除去＋末尾「。」除去。
    （表記ゆれの軽微な差を吸収しつつ『ほぼ完全一致』で重複を捕まえる）"""
    t = t.strip().rstrip("。")
    return re.sub(r"\s+", "", t)


def _published_titles() -> set[str]:
    """既公開タイトルの正規化集合を返す。
    ソース＝(1) published_log.tsv の title列 ＋ (2) published_titles_manifest.txt（note実態）。"""
    titles = set()
    if PUBLISH_LOG.exists():
        for line in PUBLISH_LOG.read_text(encoding="utf-8").splitlines():
            line = line.rstrip("\n")
            if line and not line.startswith("#"):
                cols = line.split("\t")
                if len(cols) >= 2 and cols[1].strip():
                    titles.add(_normalize_title(cols[1]))
    if TITLE_MANIFEST.exists():
        for line in TITLE_MANIFEST.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                titles.add(_normalize_title(line))
    return titles


def title_already_published(title: str) -> bool:
    """タイトル完全一致（正規化後）で既公開かどうか。6/14重複インシデントの再発防止。"""
    return _normalize_title(title) in _published_titles()


def record_published(md_path: Path, title: str):
    """公開成功した記事を published_log.tsv に追記する"""
    from datetime import datetime, timezone
    new_file = not PUBLISH_LOG.exists()
    with PUBLISH_LOG.open("a", encoding="utf-8") as f:
        if new_file:
            f.write("# stem\ttitle\tpublished_at(UTC)\n")
        f.write(f"{md_path.stem}\t{title}\t{datetime.now(timezone.utc).isoformat()}\n")


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
    無ければ最も新しい「過去日付」の記事にフォールバックする。
    CAO日次運用ではこちらをデフォルトに使う。

    ★未来日付ガード（2026-06-12 インシデント再発防止）：
      デフォルトでは **未来日付の記事を自動選択しない**。
      過去のフォールバックが「next future」を拾ってしまい、未来日付記事が
      誤って公開された事故があったため。未来日付を意図的に公開する場合は
      allow_future=True（CLI: --allow-future）で明示的に解除する。"""
    from datetime import date
    if target_date_str is None:
        target_date_str = date.today().isoformat()
    dated = []
    for p in ARTICLES_DIR.glob("*_note記事_*.md"):
        m = re.match(r"(\d{4}-\d{2}-\d{2})_", p.name)
        if m:
            dated.append((m.group(1), p))
    if not dated:
        sys.exit(f"記事が見つかりません: {ARTICLES_DIR}/*_note記事_*.md")
    dated.sort()
    # exact match（その日付ちょうど）
    for d, p in dated:
        if d == target_date_str:
            return p
    # next future（明示解除時のみ）
    if allow_future:
        for d, p in dated:
            if d > target_date_str:
                return p
    # fallback: 未来日付を除外し、最も新しい「過去日付」を選ぶ
    past = [(d, p) for d, p in dated if d <= target_date_str]
    if past:
        return past[-1][1]
    sys.exit(
        f"✗ 公開対象なし: {target_date_str} 以前の日付の記事が見つかりません。\n"
        f"  未来日付記事の自動公開はガードされています（事故防止）。\n"
        f"  意図的に未来日付を公開する場合のみ --allow-future を付けてください。"
    )


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
            force: bool = False):
    title, body, placeholders, tags = parse_article(md_path)
    photos = collect_photos(photo_dir) if photo_dir else []

    # 冪等化(1)：ファイル単位。同一ファイルの二重公開を防ぐ（--force で解除・--draft時は対象外）
    if not draft and not force and already_published(md_path):
        sys.exit(
            f"✗ この記事は既に公開済みとして記録されています: {md_path.name}\n"
            f"  二重公開を防止するため中断しました（published_log.tsv）。\n"
            f"  意図的に再公開する場合のみ --force を付けてください。"
        )

    # 冪等化(2)：タイトル完全一致。別ファイル/別日付でも同タイトルなら重複公開を防ぐ。
    #   （6/14インシデント＝同タイトルを別ファイルで再生成・再公開 の再発防止）
    if not draft and not force and title_already_published(title):
        sys.exit(
            f"✗ 同じタイトルが既に公開済みです（タイトル完全一致）: 「{title}」\n"
            f"  別ファイルでも重複公開を防ぐため中断しました\n"
            f"  （照合元: published_log.tsv ＋ published_titles_manifest.txt）。\n"
            f"  意図的に再公開する場合のみ --force を付けてください。"
        )

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
        page.goto(NOTE_NEW_URL)
        page.wait_for_load_state("networkidle", timeout=20000)
        # 認証チェック：Googleログイン画面にいるなら中断
        if "accounts.google.com" in page.url or "login" in page.url:
            sys.exit("✗ note にログインしていない状態です。 `python3 publish_to_note.py --login` を再実行してください。")

        # タイトル入力（noteのエディタはplaceholderに「タイトル」を含む）
        title_input = page.locator(
            'input[placeholder*="タイトル"], textarea[placeholder*="タイトル"]'
        ).first
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
                # 「見出し画像」エリアを開く（noteは設定パネルにある）
                page.locator('button:has-text("見出し画像"), [aria-label*="見出し画像"]').first.click()
                page.wait_for_timeout(500)
                with page.expect_file_chooser() as fc:
                    page.locator('input[type="file"]').first.click()
                fc.value.set_files(str(thumb_to_use))
                page.wait_for_timeout(1500)
                # 「適用」「保存」「決定」ボタンがあれば押す
                for label in ("適用", "決定", "保存", "完了"):
                    try:
                        btn = page.locator(f'button:has-text("{label}")').first
                        if btn.is_visible(timeout=400):
                            btn.click()
                            page.wait_for_timeout(600)
                            break
                    except Exception:
                        continue
                print(f"✅ サムネ(見出し画像)に {thumb_to_use.name} を設定")
            except Exception as e:
                print(f"⚠️  サムネ自動設定に失敗: {e}（手動で見出し画像を設定）")

        # ハッシュタグ入力（公開設定パネルに「ハッシュタグ」入力欄がある）
        if tags:
            try:
                tag_input = page.locator(
                    'input[placeholder*="ハッシュタグ"], input[placeholder*="タグ"]'
                ).first
                # 公開設定パネルを開く必要がある場合の保険
                if not tag_input.is_visible(timeout=1500):
                    try:
                        page.locator('button:has-text("公開設定"), button:has-text("公開に進む")').first.click()
                        page.wait_for_timeout(800)
                    except Exception:
                        pass
                    tag_input = page.locator(
                        'input[placeholder*="ハッシュタグ"], input[placeholder*="タグ"]'
                    ).first
                for t in tags[:10]:
                    tag_input.click()
                    page.keyboard.type(t)
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(200)
                print(f"✅ ハッシュタグ {len(tags[:10])} 個を入力")
            except Exception as e:
                print(f"⚠️  ハッシュタグ入力に失敗: {e}（手動で追加してください）")

        # 公開 or 下書き
        if draft:
            print("\n📋 ドラフトモード：公開ボタンは押しません。画面で内容確認してください。")
            input("Enterで閉じる ...")
        else:
            print("\n🚀 公開ボタンを押します（3秒後）...")
            page.wait_for_timeout(3000)
            try:
                page.locator('button:has-text("公開")').last.click()
                page.wait_for_timeout(2000)
                # 確認ダイアログがあれば再度公開
                confirm = page.locator('button:has-text("公開する"), button:has-text("公開")').last
                if confirm.is_visible():
                    confirm.click()
                page.wait_for_timeout(3000)
                print("✅ 公開リクエストを送信しました。note側で反映を確認してください。")
            except Exception as e:
                print(f"⚠️  公開ボタン自動クリック失敗: {e}")
                print("    画面で「公開」ボタンを手動で押してください。")
                input("公開を確認したら Enter ...")
            # 公開成功（または手動公開確認後）→ 冪等化ログに記録
            record_published(md_path, title)
            print(f"📒 published_log.tsv に記録しました: {md_path.stem}")

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
                    help="未来日付の記事の自動選択を許可（既定はガードで禁止・事故防止）")
    ap.add_argument("--force", action="store_true",
                    help="公開済みログにある記事でも再公開する（既定は二重公開を防止）")
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
    publish(md_path, photo_dir, draft=args.draft, text_only=args.text_only, force=args.force)


if __name__ == "__main__":
    main()
