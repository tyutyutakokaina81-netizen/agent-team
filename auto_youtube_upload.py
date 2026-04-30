#!/usr/bin/env python3
"""
auto_youtube_upload.py — Playwright でYouTube Studioに動画を自動アップロード

OAuth不要・Google Cloud設定不要
Chrome の既存ログインセッションをそのまま利用する
"""

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).parent
VIDEO_DIR = REPO / "CMO" / "outputs" / "youtube_videos"
SHORTS_DIR = VIDEO_DIR / "shorts"
SESSIONS = REPO / ".sessions"
SESSIONS.mkdir(exist_ok=True)
URLS_FILE = SESSIONS / "note_article_urls.json"
YT_SESSION_FILE = SESSIONS / "youtube_session.json"
YT_UPLOAD_LOG = SESSIONS / "youtube_upload_log.json"

VIDEO_META = {
    "title": "【高岡市観光】架空の女子アナが案内する富山・高岡の魅力｜瑞龍寺・高岡大仏・金屋町",
    "description": """富山県高岡市の観光スポットを女性アナウンサーがご案内します！

📍 紹介スポット
・国宝 瑞龍寺（禅宗の美しい古刹）
・高岡大仏（日本三大仏のひとつ・無料）
・金屋町（400年続く鋳物の石畳）
・氷見うどん・高岡コロッケ

🚄 アクセス
東京から北陸新幹線で約2時間10分 / 金沢から30分

#高岡市 #富山観光 #TakaokaToyama #JapanTravel #瑞龍寺 #高岡大仏 #北陸観光 #隠れた名所""",
    "tags": ["高岡市", "富山観光", "TakaokaToyama", "JapanTravel",
             "瑞龍寺", "高岡大仏", "金屋町", "北陸観光"],
}

# Shorts ごとのメタデータ（auto_youtube_shorts.py の short_id に対応）
SHORTS_META = {
    "s1_daibutsu_free": {
        "title": "【知らなかった】高岡大仏が無料な理由 #高岡市 #Shorts",
        "description": "日本三大仏のひとつ・高岡大仏が無料で入れる理由を解説。奈良・鎌倉と比べてみた。\n#高岡市 #富山観光 #高岡大仏 #日本三大仏 #Shorts",
    },
    "s2_kyoto_vs": {
        "title": "【衝撃】京都より高岡に行けばよかった #高岡市 #Shorts",
        "description": "混んでいる京都より、高岡市で貸し切り国宝を体験する方法。\n#高岡市 #富山観光 #穴場 #隠れた名所 #Shorts",
    },
    "s3_takaoka_cost": {
        "title": "【実費公開】高岡市日帰り¥2,450の全内訳 #富山 #Shorts",
        "description": "東京から日帰りで高岡市を観光した全費用を公開。新幹線・食事・入場料の内訳。\n#高岡市 #富山観光 #旅費 #節約旅行 #Shorts",
    },
    "s4_english_hidden": {
        "title": "Japan's Hidden Tourism Gem Nobody Knows #HiddenJapan #Shorts",
        "description": "Takaoka City, Toyama — Japan's best kept secret for travelers.\n#HiddenJapan #JapanTravel #TakaokaToyama #Shorts",
    },
    "s5_zuiryuji": {
        "title": "【貸し切り】国宝・瑞龍寺の朝は別世界 #高岡市 #Shorts",
        "description": "国宝5棟を誇る瑞龍寺。朝一番に行けば貸し切りになれる。\n#高岡市 #富山観光 #瑞龍寺 #国宝 #Shorts",
    },
}


def install_deps():
    import subprocess
    # Mac Homebrew Python は --break-system-packages が必要
    for attempt in [
        [sys.executable, "-m", "pip", "install", "playwright", "-q", "--break-system-packages"],
        [sys.executable, "-m", "pip", "install", "playwright", "-q"],
    ]:
        r = subprocess.run(attempt, capture_output=True)
        if r.returncode == 0:
            break
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium",
                    "--with-deps"], capture_output=True)


def extract_youtube_cookies():
    """ChromeからYouTubeのクッキーを取得してPlaywright形式で保存"""
    try:
        import browser_cookie3
        cookies = list(browser_cookie3.chrome(domain_name=".youtube.com"))
        if not cookies:
            cookies = list(browser_cookie3.chrome(domain_name="youtube.com"))
        if not cookies:
            return False
        state = {
            "cookies": [
                {
                    "name": c.name,
                    "value": c.value,
                    "domain": c.domain if c.domain.startswith(".") else f".{c.domain}",
                    "path": c.path or "/",
                    "secure": bool(c.secure),
                    "httpOnly": False,
                    "sameSite": "Lax",
                }
                for c in cookies if c.value
            ],
            "origins": [],
        }
        YT_SESSION_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))
        print(f"  ✅ YouTubeセッション取得: {len(state['cookies'])}件")
        return True
    except Exception as e:
        print(f"  ⚠️  クッキー取得失敗: {e}")
        return False


def find_latest_video() -> Path | None:
    mp4s = sorted(VIDEO_DIR.glob("*.mp4"),
                  key=lambda p: p.stat().st_mtime, reverse=True)
    return mp4s[0] if mp4s else None


def find_unuploaded_shorts() -> list[Path]:
    """未アップロードのShortsを返す"""
    if not SHORTS_DIR.exists():
        return []
    log = _load_upload_log()
    uploaded = set(log.get("uploaded", []))
    shorts = sorted(SHORTS_DIR.glob("*.mp4"), key=lambda p: p.stat().st_mtime)
    return [p for p in shorts if p.stem not in uploaded]


def _load_upload_log() -> dict:
    if YT_UPLOAD_LOG.exists():
        return json.loads(YT_UPLOAD_LOG.read_text())
    return {"uploaded": [], "urls": {}}


def _save_upload_log(log: dict):
    YT_UPLOAD_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2))


def _get_short_meta(video_path: Path) -> dict:
    """Short IDからメタデータを取得（デフォルトは汎用タイトル）"""
    stem = video_path.stem
    if stem in SHORTS_META:
        return SHORTS_META[stem]
    return {
        "title": f"【高岡市】{stem} #高岡市 #Shorts",
        "description": f"富山県高岡市の観光Shorts。\n#高岡市 #富山観光 #Shorts",
    }


def upload_via_browser(video_path: Path, meta: dict | None = None) -> str | None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        install_deps()
        from playwright.sync_api import sync_playwright

    use_meta = meta or VIDEO_META
    print(f"  📤 アップロード開始: {video_path.name}")

    with sync_playwright() as p:
        # セッションファイルがあれば読み込む、なければ新規
        ctx_args = {}
        if YT_SESSION_FILE.exists():
            ctx_args["storage_state"] = str(YT_SESSION_FILE)

        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(**ctx_args)
        page = ctx.new_page()

        # YouTube Studio を開く
        page.goto("https://studio.youtube.com/", timeout=30000)
        time.sleep(3)

        # ログイン確認
        if "accounts.google.com" in page.url or "signin" in page.url:
            print("  ⚠️  YouTubeにログインされていません")
            print("  Chromeで https://studio.youtube.com/ を開いてログインしてください")
            browser.close()
            return None

        # 「作成」ボタン → 「動画をアップロード」
        create_sels = [
            'button[aria-label="作成"]',
            'button[aria-label="Create"]',
            '#create-icon',
            'ytcp-button#create-icon',
            'button:has-text("作成")',
            '[id="create-icon-container"]',
        ]
        for sel in create_sels:
            try:
                page.click(sel, timeout=5000)
                break
            except Exception:
                continue
        time.sleep(2)
        upload_sels = [
            'text=動画をアップロード',
            'text=Upload videos',
            'text=Upload video',
            'tp-yt-paper-item:has-text("動画")',
            '#text-item-0',
        ]
        for sel in upload_sels:
            try:
                page.click(sel, timeout=3000)
                break
            except Exception:
                continue
        time.sleep(2)

        # ファイル選択（input[type=file]が出るまで待機してからセット）
        try:
            page.wait_for_selector('input[type="file"]', timeout=15000)
        except Exception:
            # JSで非表示のinputを表示して再試行
            page.evaluate("const i=document.querySelector('input[type=\"file\"]');if(i)i.style.display='block';")
            time.sleep(2)

        file_input = page.query_selector('input[type="file"]')
        if file_input:
            file_input.set_input_files(str(video_path))
        else:
            # フォールバック: ドラッグ&ドロップ領域をクリックしてダイアログ代わりに
            try:
                page.wait_for_selector('[class*="upload-box"], [class*="drag"]', timeout=5000)
            except Exception:
                pass
            raise RuntimeError("ファイル入力欄が見つかりません（YouTube Studioのログインを確認）")

        print("  📁 ファイル選択完了・アップロード中...")
        time.sleep(5)

        # タイトル入力
        title_box = page.query_selector('[placeholder="動画タイトルを追加"], [id="title-textarea"] #input')
        if not title_box:
            title_box = page.query_selector('ytcp-social-suggestions-textbox[id="title-textarea"] #input')
        if title_box:
            title_box.triple_click()
            title_box.fill(use_meta["title"])
            time.sleep(1)

        # 説明文入力
        desc_box = page.query_selector('[placeholder="視聴者に動画の内容を伝えましょう"], [id="description-textarea"] #input')
        if not desc_box:
            desc_box = page.query_selector('ytcp-social-suggestions-textbox[id="description-textarea"] #input')
        if desc_box:
            desc_box.click()
            desc_box.fill(use_meta["description"])
            time.sleep(1)

        # 「子ども向けではない」を選択
        not_for_kids = page.query_selector('[name="VIDEO_MADE_FOR_KIDS_NOT_MFK"]')
        if not_for_kids:
            not_for_kids.click()
            time.sleep(0.5)

        # 「次へ」を3回クリック（詳細→収益化→公開設定）
        for _ in range(3):
            next_btn = page.query_selector('ytcp-button[id="next-button"]')
            if next_btn:
                next_btn.click()
                time.sleep(2)

        # 公開設定「公開」を選択
        public_btn = page.query_selector('[name="PUBLIC"]')
        if public_btn:
            public_btn.click()
            time.sleep(1)

        # 「保存」クリック
        save_btn = page.query_selector('ytcp-button[id="done-button"]')
        if save_btn:
            save_btn.click()
            time.sleep(5)

        # アップロード完了URL取得
        current_url = page.url
        video_url = None

        # URLからvideo_idを抽出
        if "watch?v=" in current_url:
            video_id = current_url.split("watch?v=")[1].split("&")[0]
            video_url = f"https://youtu.be/{video_id}"
        else:
            # ページ内からURLを探す
            links = page.query_selector_all('a[href*="watch?v="]')
            if links:
                href = links[0].get_attribute("href")
                video_id = href.split("watch?v=")[1].split("&")[0]
                video_url = f"https://youtu.be/{video_id}"

        browser.close()

        if video_url:
            print(f"  ✅ アップロード完了: {video_url}")
            _save_url(video_url)
        else:
            print("  ✅ アップロード完了（URLは studio.youtube.com で確認）")
            video_url = "https://studio.youtube.com/"

        return video_url


def _save_url(url: str):
    urls = {}
    if URLS_FILE.exists():
        try:
            urls = json.loads(URLS_FILE.read_text())
        except Exception:
            pass
    urls["youtube_takaoka"] = url
    URLS_FILE.write_text(json.dumps(urls, ensure_ascii=False, indent=2))
    print(f"  URL保存済み → X投稿・note記事に自動挿入されます")


def upload_latest():
    """長尺動画を1本アップロード"""
    video = find_latest_video()
    if not video:
        print("❌ 動画がありません。先に python3 auto_youtube_produce.py を実行してください")
        return None

    print(f"対象動画: {video.name}")
    extract_youtube_cookies()
    return upload_via_browser(video)


def upload_shorts_batch():
    """未アップロードのShortsを全てアップロード"""
    shorts = find_unuploaded_shorts()
    if not shorts:
        print("  ✅ アップロード待ちのShortsなし")
        return

    print(f"  Shorts アップロード対象: {len(shorts)}本")
    extract_youtube_cookies()
    log = _load_upload_log()

    for short_path in shorts:
        meta = _get_short_meta(short_path)
        url = upload_via_browser(short_path, meta)
        if url:
            log["uploaded"].append(short_path.stem)
            log["urls"][short_path.stem] = url
            _save_upload_log(log)
            time.sleep(10)  # YouTube APIレート制限対策


if __name__ == "__main__":
    if "--shorts" in sys.argv:
        upload_shorts_batch()
    elif "--setup" in sys.argv:
        upload_latest()
    else:
        # デフォルト: 長尺 + Shorts 両方
        upload_latest()
        upload_shorts_batch()
