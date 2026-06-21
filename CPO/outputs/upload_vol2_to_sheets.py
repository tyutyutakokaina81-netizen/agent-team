#!/usr/bin/env python3
"""
CPO/CDO: テンプレVol.2 → Google Sheets 自動アップロード

用途: generate_vol2_sheet.py が生成したカレンダーを、実際の Google Sheets に
      フォーマット付き（色分け・週見出し・テンプレ全文）でアップロードする。

前提（オーナーが一度だけ行う認証準備）:
  1. Google Cloud Console でプロジェクト作成
  2. Google Sheets API + Google Drive API を有効化
  3. サービスアカウント作成 → JSON鍵をダウンロード → credentials.json として保存
  4. pip install gspread google-auth

実行:
  python3 upload_vol2_to_sheets.py \
      --credentials credentials.json \
      --month 7 --year 2026 \
      --share-email your@gmail.com

出力: 共有可能な Google Sheets URL（販売テンプレの本体）

※ コンテナ内（外部ネットブロック）では実行不可。オーナーのMac/PCで実行する。
"""

import argparse
import sys
from datetime import datetime

# generate_vol2_sheet.py からテンプレ・カレンダーを再利用
try:
    from generate_vol2_sheet import TEMPLATES, generate_calendar
except ImportError:
    print("❌ generate_vol2_sheet.py と同じディレクトリで実行してください")
    sys.exit(1)


def build_rows(year: int, month: int):
    """Google Sheets に書き込む行データ（フォーマット情報付き）を構築"""
    calendar_data = generate_calendar(year, month)

    header = ["週", "日付", "曜日", "テンプレID", "カテゴリ", "タイトル", "投稿本文（コピペ用）"]
    rows = [header]
    color_map = {}  # 行番号 → 背景色（カテゴリ別）

    for i, (key, data) in enumerate(sorted(calendar_data.items()), start=2):
        rows.append([
            key.split("_")[0],
            data["date"],
            data["day"],
            data["template"],
            data["category"],
            data["title"],
            data["content"],  # ← 全文（truncateしない）
        ])
        color_map[i] = data["color"]

    return rows, color_map


def hex_to_rgb(hex_color: str):
    """#RRGGBB → gspread 用 0-1 RGB dict"""
    h = hex_color.lstrip("#")
    return {
        "red": int(h[0:2], 16) / 255,
        "green": int(h[2:4], 16) / 255,
        "blue": int(h[4:6], 16) / 255,
    }


def upload(credentials_path: str, year: int, month: int, share_email: str | None):
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)
    client = gspread.authorize(creds)

    title = f"SNS Content Calendar Vol.2 — {year}年{month}月"
    sheet = client.create(title)
    ws = sheet.sheet1
    ws.update_title(f"{month}月カレンダー")

    rows, color_map = build_rows(year, month)
    ws.update(f"A1:G{len(rows)}", rows, value_input_option="RAW")

    # ヘッダー太字 + 列幅 + カテゴリ色分け
    ws.format("A1:G1", {
        "textFormat": {"bold": True},
        "backgroundColor": hex_to_rgb("#2D3436"),
        "horizontalAlignment": "CENTER",
    })
    ws.format("A1:G1", {"textFormat": {"foregroundColor": hex_to_rgb("#FFFFFF"), "bold": True}})

    for row_num, color in color_map.items():
        ws.format(f"A{row_num}:F{row_num}", {"backgroundColor": hex_to_rgb(color)})

    # 本文列を折り返し表示
    ws.format(f"G2:G{len(rows)}", {"wrapStrategy": "WRAP"})

    if share_email:
        sheet.share(share_email, perm_type="user", role="writer")

    # 「リンクを知っている全員が閲覧可」= 購入者へ配布できる状態
    sheet.share(None, perm_type="anyone", role="reader")

    print(f"✅ アップロード完了")
    print(f"📊 タイトル: {title}")
    print(f"🔗 共有URL（購入者配布用）: {sheet.url}")
    print(f"\n【次のステップ】")
    print(f"1. このURLを note/Gumroad の販売ページに『コピーして使ってください』として掲載")
    print(f"2. 購入者は ファイル → コピーを作成 で自分専用版を取得")
    return sheet.url


def main():
    parser = argparse.ArgumentParser(description="Vol.2 を Google Sheets にアップロード")
    parser.add_argument("--credentials", default="credentials.json",
                        help="サービスアカウントJSON鍵のパス")
    parser.add_argument("--month", type=int, default=datetime.now().month)
    parser.add_argument("--year", type=int, default=datetime.now().year)
    parser.add_argument("--share-email", default=None,
                        help="編集権限を渡す自分のGmailアドレス")
    parser.add_argument("--dry-run", action="store_true",
                        help="API接続せず、行データ件数だけ確認")
    args = parser.parse_args()

    if args.dry_run:
        rows, color_map = build_rows(args.year, args.month)
        print(f"✅ dry-run: {len(rows)-1}行のデータを生成（ヘッダー除く）")
        print(f"   色分け対象: {len(color_map)}行")
        print(f"   本番実行: --credentials credentials.json を指定してください")
        return

    upload(args.credentials, args.year, args.month, args.share_email)


if __name__ == "__main__":
    main()
