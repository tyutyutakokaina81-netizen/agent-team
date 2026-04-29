#!/usr/bin/env python3
"""
auto_youtube_upload.py — YouTube Data API v3 で動画を自動アップロード

前提（初回のみ）:
  pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
  Google Cloud Console で OAuth2 クライアントIDを作成 → client_secrets.json を配置

認証手順:
  1. https://console.cloud.google.com/ → 新規プロジェクト
  2. YouTube Data API v3 を有効化
  3. 認証情報 → OAuth クライアントID（デスクトップ） → JSONダウンロード
  4. ~/agent-team/.sessions/yt_client_secrets.json として保存
  5. python3 auto_youtube_upload.py --setup  で初回認証（ブラウザで許可）
"""

import json
import sys
from pathlib import Path

SESSIONS = Path(__file__).parent / ".sessions"
SECRETS_FILE = SESSIONS / "yt_client_secrets.json"
TOKEN_FILE = SESSIONS / "yt_token.json"
SESSIONS.mkdir(exist_ok=True)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def check_deps():
    try:
        import googleapiclient
        import google_auth_oauthlib
        return True
    except ImportError:
        import subprocess
        print("📦 YouTube API ライブラリをインストール中...")
        pkgs = ["google-api-python-client", "google-auth-httplib2", "google-auth-oauthlib"]
        ret = subprocess.run([sys.executable, "-m", "pip", "install"] + pkgs + ["-q"],
                             capture_output=True)
        if ret.returncode != 0:
            # Homebrew管理Python（Mac）は --break-system-packages が必要
            subprocess.run([sys.executable, "-m", "pip", "install"] + pkgs +
                           ["-q", "--break-system-packages"])
        return True


def get_credentials():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not SECRETS_FILE.exists():
                print("❌ yt_client_secrets.json がありません")
                print()
                print("  設定手順:")
                print("  1. https://console.cloud.google.com/ を開く")
                print("  2. 新規プロジェクト → YouTube Data API v3 を有効化")
                print("  3. 認証情報 → OAuth クライアントID（デスクトップ）")
                print("  4. JSONダウンロード")
                print(f"  5. {SECRETS_FILE} として保存")
                print("  6. python3 auto_youtube_upload.py --setup")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(str(SECRETS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())

    return creds


def upload(video_path: Path, title: str, description: str, tags: list) -> str | None:
    check_deps()
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = get_credentials()
    if not creds:
        return None

    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "19",  # Travel & Events
            "defaultLanguage": "ja",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True,
                            mimetype="video/mp4")

    print(f"  📤 アップロード中: {video_path.name}")
    request = youtube.videos().insert(
        part=",".join(body.keys()), body=body, media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"     進行: {int(status.progress() * 100)}%")

    video_id = response["id"]
    url = f"https://youtu.be/{video_id}"
    print(f"  ✅ アップロード完了: {url}")
    return url


def upload_latest():
    """CMO/outputs/youtube_videos/ から最新のMP4を自動アップロード"""
    video_dir = Path(__file__).parent / "CMO" / "outputs" / "youtube_videos"
    mp4s = sorted(video_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not mp4s:
        print("❌ アップロードする動画がありません")
        print("   先に python3 auto_youtube_produce.py を実行してください")
        return

    latest = mp4s[0]
    print(f"対象: {latest.name}")

    title = "【高岡市観光】架空の女子アナが案内する富山・高岡の魅力｜瑞龍寺・高岡大仏・金屋町"
    description = """富山県高岡市の観光スポットを女性アナウンサーがご案内します！

📍 紹介スポット
・国宝 瑞龍寺（禅宗の美しい古刹）
・高岡大仏（日本三大仏のひとつ・無料）
・金屋町（400年続く鋳物の石畳）
・氷見うどん・高岡コロッケ

🚄 アクセス
東京から北陸新幹線で約2時間10分
金沢から30分

🗾 高岡市観光公式: https://www.takaoka.or.jp/

#高岡市 #富山観光 #TakaokaToyama #JapanTravel #瑞龍寺 #高岡大仏 #北陸観光"""

    tags = [
        "高岡市", "富山観光", "TakaokaToyama", "JapanTravel",
        "瑞龍寺", "高岡大仏", "金屋町", "北陸観光", "HiddenJapan",
        "日本観光", "インバウンド", "富山県",
    ]

    url = upload(latest, title, description, tags)
    if url:
        # URL保存
        urls_file = Path(__file__).parent / ".sessions" / "note_article_urls.json"
        urls = {}
        if urls_file.exists():
            urls = json.loads(urls_file.read_text())
        urls["youtube_takaoka"] = url
        urls_file.write_text(json.dumps(urls, ensure_ascii=False, indent=2))
        print(f"  URL保存済み → X投稿・note記事に自動挿入されます")

    return url


if __name__ == "__main__":
    if "--setup" in sys.argv:
        check_deps()
        get_credentials()
        print("✅ YouTube認証完了")
    else:
        upload_latest()
