"""
YouTube 自動アップロードスクリプト
─────────────────────────────────────
オーナーが認証を 1 回行えば、以降はワンコマンドで動画アップロード可能。

【セットアップ（初回・1 回だけ）】
1. pip install google-api-python-client google-auth-oauthlib google-auth-httplib2
2. https://console.cloud.google.com/ で プロジェクト作成 → YouTube Data API v3 を有効化
3. OAuth 同意画面 → 認証情報 → OAuth クライアント ID（デスクトップ）
4. 取得した JSON を `client_secret.json` として本ファイルと同じディレクトリに配置
5. 初回実行時にブラウザが開きログイン → token.json が自動生成される

【使い方】
    python3 YouTube_自動アップロード.py \\
        --video path/to/video.mp4 \\
        --title "【元金融マンが解説】フリーランス確定申告で詰む 3 パターン" \\
        --description-file path/to/description.txt \\
        --tags-file path/to/tags.txt \\
        --thumbnail path/to/thumb.png \\
        --privacy unlisted          # public / unlisted / private
        # 任意:
        # --playlist-id PLxxxxxx
        # --schedule "2026-05-08T20:00:00+09:00"
        # --category 27               # 27 = Education

【コスト】¥0（YouTube API は無料、Google Cloud は本用途で課金されない）
【リスク】
- 認証情報（client_secret.json / token.json）は git にコミット禁止（.gitignore 済）
- アップロード上限：未認証アカウントは 1 日 6 本、認証後は無制限
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
except ImportError:
    sys.exit(
        "依存ライブラリが未導入です。次を実行してください:\n"
        "  pip install google-api-python-client google-auth-oauthlib google-auth-httplib2"
    )

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",  # サムネ・プレイリスト用
]

DEFAULT_CATEGORY = "27"  # Education


def get_authenticated_service(client_secret: Path, token_path: Path):
    creds: Credentials | None = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not client_secret.exists():
                sys.exit(f"client_secret.json が見つかりません: {client_secret}")
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return build("youtube", "v3", credentials=creds)


def upload_video(
    service,
    video_path: Path,
    title: str,
    description: str,
    tags: list[str],
    privacy: str,
    category: str,
    schedule: str | None,
) -> str:
    body = {
        "snippet": {
            "title": title[:100],  # YouTube 上限 100 字
            "description": description[:5000],
            "tags": tags[:500],
            "categoryId": category,
            "defaultLanguage": "ja",
            "defaultAudioLanguage": "ja",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
            "embeddable": True,
        },
    }
    if schedule:
        body["status"]["privacyStatus"] = "private"
        body["status"]["publishAt"] = schedule

    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/*")
    request = service.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"アップロード中: {int(status.progress() * 100)}%")
    video_id = response["id"]
    print(f"✅ アップロード完了: https://youtu.be/{video_id}")
    return video_id


def set_thumbnail(service, video_id: str, thumbnail: Path) -> None:
    if not thumbnail.exists():
        print(f"⚠️  サムネイルファイル無し: {thumbnail}")
        return
    service.thumbnails().set(
        videoId=video_id,
        media_body=MediaFileUpload(str(thumbnail), mimetype="image/png"),
    ).execute()
    print("✅ サムネイル設定完了")


def add_to_playlist(service, video_id: str, playlist_id: str) -> None:
    service.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {"kind": "youtube#video", "videoId": video_id},
            }
        },
    ).execute()
    print(f"✅ プレイリスト追加: {playlist_id}")


def parse_args():
    p = argparse.ArgumentParser(description="YouTube 自動アップロード")
    p.add_argument("--video", required=True, type=Path)
    p.add_argument("--title", required=True)
    p.add_argument("--description-file", required=True, type=Path)
    p.add_argument("--tags-file", type=Path, help="タグ（カンマ区切り or 改行区切り）")
    p.add_argument("--thumbnail", type=Path)
    p.add_argument(
        "--privacy",
        choices=["public", "unlisted", "private"],
        default="unlisted",
    )
    p.add_argument("--category", default=DEFAULT_CATEGORY)
    p.add_argument("--playlist-id")
    p.add_argument(
        "--schedule",
        help="ISO8601（例: 2026-05-08T20:00:00+09:00）。指定時は private 投稿 → 予約公開",
    )
    p.add_argument("--client-secret", type=Path, default=Path("client_secret.json"))
    p.add_argument("--token", type=Path, default=Path("token.json"))
    return p.parse_args()


def main():
    args = parse_args()

    if not args.video.exists():
        sys.exit(f"動画ファイル無し: {args.video}")
    if not args.description_file.exists():
        sys.exit(f"説明文ファイル無し: {args.description_file}")

    description = args.description_file.read_text(encoding="utf-8")
    tags: list[str] = []
    if args.tags_file and args.tags_file.exists():
        raw = args.tags_file.read_text(encoding="utf-8")
        tags = [t.strip() for t in raw.replace("\n", ",").split(",") if t.strip()]

    service = get_authenticated_service(args.client_secret, args.token)

    try:
        video_id = upload_video(
            service,
            video_path=args.video,
            title=args.title,
            description=description,
            tags=tags,
            privacy=args.privacy,
            category=args.category,
            schedule=args.schedule,
        )
        if args.thumbnail:
            set_thumbnail(service, video_id, args.thumbnail)
        if args.playlist_id:
            add_to_playlist(service, video_id, args.playlist_id)
        print("\n🎉 すべて完了")
        print(f"動画 URL: https://youtu.be/{video_id}")
    except HttpError as e:
        sys.exit(f"❌ YouTube API エラー: {e}")


if __name__ == "__main__":
    main()
