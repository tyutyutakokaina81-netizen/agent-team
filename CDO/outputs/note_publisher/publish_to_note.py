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


# ---------- UI操作ヘルパー（noteのUI変更に強くする） ----------

def _try_click(page, candidates, timeout=3000):
    """candidates を順に試し、最初に見えたボタンをクリックして True を返す。
    candidates の要素:
      - 文字列 → CSS/text セレクタ（例 'button:has-text("投稿する")'）
      - ("role", "名前") → get_by_role("button", name="名前")
    どれも押せなければ False（呼び出し側で手動フォールバック）。
    """
    for sel in candidates:
        try:
            if isinstance(sel, tuple) and sel[0] == "role":
                loc = page.get_by_role("button", name=sel[1]).first
            else:
                loc = page.locator(sel).first
            loc.wait_for(state="visible", timeout=timeout)
            loc.click()
            return True
        except Exception:
            continue
    return False


def set_eyecatch_from_gallery(page, keywords):
    """note の『みんなのフォトギャラリー』(無料素材)から見出し画像を自動選択する。
    keywords: 検索語の候補リスト（先頭から試し、結果が出たものを使う）。
    UI変更に備え全ステップ多候補＋非ブロッキング。失敗時 False（公開は継続）。
    """
    try:
        # 1) エディタ上部の「見出し画像を追加」エリアを開く
        if not _try_click(page, [
            'button:has-text("見出し画像を追加")',
            'button:has-text("記事に画像を追加")',
            'button:has-text("画像を追加")',
            'button:has-text("見出し画像")',
            ('role', '見出し画像を追加'),
            '[aria-label*="見出し画像"]',
        ], timeout=3000):
            return False
        page.wait_for_timeout(800)
        # 2) 「みんなのフォトギャラリー」を選ぶ
        if not _try_click(page, [
            'button:has-text("みんなのフォトギャラリー")',
            'a:has-text("みんなのフォトギャラリー")',
            'button:has-text("フォトギャラリー")',
            ('role', 'みんなのフォトギャラリー'),
        ], timeout=3000):
            return False
        page.wait_for_timeout(1200)
        # 3) キーワード検索（候補を順に試す）。検索欄が無ければデフォルト表示から選ぶ
        for kw in keywords:
            try:
                search = page.locator(
                    'input[type="search"], input[placeholder*="検索"], input[placeholder*="キーワード"]'
                ).first
                search.wait_for(state="visible", timeout=2500)
                search.click()
                search.fill(kw)
                page.keyboard.press("Enter")
                page.wait_for_timeout(1800)
                # 検索結果に画像があれば break（無ければ次のキーワード）
                imgs = page.locator(
                    'div[role="dialog"] img, [class*="modal"] img, [class*="gallery"] img'
                )
                if imgs.count() > 0:
                    break
            except Exception:
                continue
        # 4) 最初の画像を選択（モーダル内に限定）
        if not _try_click(page, [
            'div[role="dialog"] img',
            '[class*="modal"] img',
            '[class*="gallery"] img',
            '[class*="Gallery"] img',
        ], timeout=4000):
            return False
        page.wait_for_timeout(800)
        # 5) 「この画像を見出し画像にする」/適用/保存/決定
        if not _try_click(page, [
            'button:has-text("この画像を見出し画像にする")',
            'button:has-text("見出し画像にする")',
            'button:has-text("この画像を挿入")',
            'button:has-text("保存")',
            'button:has-text("適用")',
            'button:has-text("決定")',
            'button:has-text("完了")',
            ('role', '保存'),
        ], timeout=4000):
            return False
        page.wait_for_timeout(1000)
        return True
    except Exception:
        return False


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


def find_article_by_date(target_date_str: str | None = None):
    """ファイル名の日付(YYYY-MM-DD)が target_date と一致するものを返す。
    無ければ target_date 以降の最も早い未来日付の記事を返す。
    全て過去なら最も新しい過去日付。CAO日次運用ではこちらをデフォルトに使う。"""
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
    # exact match
    for d, p in dated:
        if d == target_date_str:
            return p
    # next future
    for d, p in dated:
        if d > target_date_str:
            return p
    # fallback: most recent past
    return dated[-1][1]


def _extract_tags(text: str) -> list[str]:
    """## ハッシュタグ 直下の ``` から #xxx を取り出す（無ければ空）。"""
    tag_m = re.search(r"##\s*ハッシュタグ.*?\n```\n(.+?)\n```", text, re.S)
    if not tag_m:
        return []
    return [t.lstrip("#").strip() for t in re.findall(r"#\S+", tag_m.group(1))]


def _affiliate_block(text: str) -> str:
    """じゃらん等のPR表記＋アフィリリンク行を取り出す（コードブロック外にあっても拾う）。
    景表法のPR表記と収益リンクは必ず本文に含める必要があるため。"""
    out, seen = [], set()
    for ln in text.splitlines():
        s = re.sub(r"^[-*]\s*", "", ln.strip())
        if ("アフィリエイト広告" in s) or ("px.a8.net" in s) or ("a8mat=" in s):
            if s and s not in seen:
                seen.add(s); out.append(s)
    return "\n".join(out)


def _finalize(title: str, body: str, text: str):
    """本文末に取りこぼしがちな PR/アフィリ行を補完し、placeholder/タグを揃えて返す。"""
    aff = _affiliate_block(text)
    if aff and "px.a8.net" not in body and "a8mat=" not in body:
        body = body.rstrip() + "\n\n" + aff
    placeholders = re.findall(r"\[(?:ここに)?写真[①②③④⑤⑥⑦⑧⑨⑩\d]+[^\]]*\]", body)
    return title, body, placeholders, _extract_tags(text)


def parse_article(md_path: Path):
    """記事mdから タイトル・本文・写真placeholder順序・ハッシュタグ を取り出す。
    2書式に対応：
      (A) 旧書式: 「## タイトル」「## 本文」「## ハッシュタグ」の ``` コードブロック方式
      (B) 英語ファースト書式: 先頭H1=タイトル、「## English」「## 日本語版」の ``` を本文に
    """
    text = md_path.read_text(encoding="utf-8")

    # --- (A) 旧書式（タイトル＋本文の両コードブロックが揃う時のみ採用） ---
    title_m = re.search(r"メイン.*?\n```\n(.+?)\n```", text, re.S) \
        or re.search(r"##\s*タイトル.*?\n```\n(.+?)\n```", text, re.S)
    body_m = re.search(r"##\s*本文.*?\n```\n(.+?)\n```", text, re.S)
    if title_m and body_m:
        title = title_m.group(1).strip().splitlines()[0].strip()
        body = body_m.group(1).strip()
        return _finalize(title, body, text)

    # --- (B) 英語ファースト等の別書式：H1＝タイトル、見出し別コードブロックを本文に連結 ---
    h1 = re.search(r"^#\s+(.+)$", text, re.M)
    if not h1:
        sys.exit("タイトル(H1 '# ...')も タイトルブロックも見つかりませんでした。")
    title = re.sub(r"^note記事[：:]\s*", "", h1.group(1).strip())

    body_parts: list[str] = []
    # "## " で章に分割し、English/日本語/本文 を含む章の最初の ``` を本文とする（出現順＝英語→日本語）
    for sec in re.split(r"^##\s+", text, flags=re.M)[1:]:
        head_line = sec.splitlines()[0] if sec.strip() else ""
        if re.search(r"English|日本語|本文", head_line, re.I):
            cb = re.search(r"```\n(.+?)\n```", sec, re.S)
            if cb:
                body_parts.append(cb.group(1).strip())
    if not body_parts:
        sys.exit("本文が抽出できませんでした（## English / ## 日本語版 / ## 本文 の ``` が必要）。")
    body = "\n\n".join(body_parts)
    return _finalize(title, body, text)


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

        # 【見出し画像（サムネ）】noteではエディタ画面で設定する（「公開に進む」より前）。
        # 優先順位: ①用意した画像ファイル(--photos / thumbnails/{stem}.jpg)があればアップロード
        #           ②無ければ『みんなのフォトギャラリー』(無料素材)からキーワードで自動選択
        thumb_to_use = photos[0] if photos else auto_thumb
        if thumb_to_use and Path(str(thumb_to_use)).exists():
            try:
                if not _try_click(page, [
                    'button:has-text("見出し画像を追加")',
                    'button:has-text("画像を追加")',
                    'button:has-text("見出し画像")',
                    '[aria-label*="見出し画像"]',
                ], timeout=2500):
                    raise RuntimeError("見出し画像ボタンが見つからない")
                page.wait_for_timeout(500)
                # アップロードを選ぶ（ギャラリーと選択肢が並ぶ場合）
                _try_click(page, [
                    'button:has-text("画像をアップロード")',
                    'button:has-text("アップロード")',
                ], timeout=1500)
                with page.expect_file_chooser() as fc:
                    page.locator('input[type="file"]').first.click()
                fc.value.set_files(str(thumb_to_use))
                page.wait_for_timeout(1500)
                _try_click(page, [
                    'button:has-text("保存")', 'button:has-text("適用")',
                    'button:has-text("決定")', 'button:has-text("完了")',
                ], timeout=1500)
                print(f"✅ サムネ(見出し画像)に {thumb_to_use.name} を設定")
            except Exception as e:
                print(f"⚠️  サムネ(ファイル)設定に失敗: {e}")
        else:
            # 画像ファイルが無い → note標準ギャラリーから自動選択
            kw = [t for t in (tags[:3] if tags else [])] + ["富山", "日本", "風景"]
            if set_eyecatch_from_gallery(page, kw):
                print(f"✅ サムネをみんなのフォトギャラリーから自動選択（検索語: {kw[0] if kw else '-'}）")
            else:
                print("ℹ️  写真サムネは未設定（noteの既定サムネ=タイトル画像が自動適用されます）")

        # 【公開は2段階】エディタ「公開に進む」→ 設定画面 →「投稿する」。
        # ハッシュタグ・投稿ボタンは "公開に進む" 後の設定画面にある。
        if not draft:
            if _try_click(page, [
                'button:has-text("公開に進む")',
                ('role', '公開に進む'),
                'button:has-text("公開設定")',
                ('role', '公開設定'),
            ], timeout=5000):
                print("✅ 公開設定画面へ遷移")
                page.wait_for_timeout(1500)
            else:
                print("⚠️  「公開に進む」が見つからず（UI変更の可能性）。現画面のまま続行を試みます")

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

        # 公開 or 下書き（全自動：手動Enterは廃止。失敗時は非ゼロ終了でキューに残す）
        publish_failed = False
        if draft:
            print("\n📋 ドラフトモード：投稿ボタンは押しません。画面で内容確認してください。")
            input("Enterで閉じる ...")
        else:
            print("\n🚀 投稿ボタンを押します（全自動）...")
            page.wait_for_timeout(1500)
            posted = _try_click(page, [
                'button:has-text("投稿する")',
                ('role', '投稿する'),
                'button:has-text("公開する")',
                ('role', '公開する'),
                'button:has-text("公開")',
                ('role', '公開'),
            ], timeout=5000)
            if posted:
                page.wait_for_timeout(2000)
                # 確認ダイアログ（モーダル）が出る場合に備え、最終ボタンをもう一度だけ試す
                _try_click(page, [
                    'button:has-text("投稿する")',
                    'button:has-text("公開する")',
                ], timeout=2000)
                page.wait_for_timeout(3000)
                print("✅ 公開リクエストを送信しました。note側で反映を確認してください。")
            else:
                print("⚠️  投稿ボタンを自動で見つけられませんでした（noteのUI変更の可能性）。")
                print("    この記事はキューに残します（公開済み扱いにしません）。")
                publish_failed = True

        ctx.close()
        if publish_failed:
            sys.exit(1)


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
        md_path = find_article_by_date(args.by_date)
    if not md_path.exists():
        sys.exit(f"記事が見つかりません: {md_path}")

    photo_dir = Path(args.photos).expanduser() if args.photos else None
    publish(md_path, photo_dir, draft=args.draft, text_only=args.text_only)


if __name__ == "__main__":
    main()
