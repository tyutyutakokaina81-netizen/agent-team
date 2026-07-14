#!/usr/bin/env python3
"""IndexNow 一括通知 — デプロイ済み _site/sitemap.xml の全URLを検索エンジン(Bing/Yandex/Seznam等)に通知する。

- GitHub Actions（ネット可）から pages デプロイ後に呼ぶ想定。code(A1)からは実行しない。
- 失敗しても常に exit 0（デプロイを壊さない）。IndexNowは無料・APIキー不要（所有権はホスト上のキーファイルで確認）。
- Googleは現状IndexNow非対応だが、Bing/Yandex等には即時通知が届く。Googleの発見はGSCのsitemap送信＋被リンクで別途。
"""
import json
import re
import sys
import urllib.request

KEY = "d0b745641195c59335fc4aed0cdf134b"
HOST = "tyutyutakokaina81-netizen.github.io"
KEY_LOCATION = f"https://{HOST}/agent-team/{KEY}.txt"
SITEMAP = "_site/sitemap.xml"
ENDPOINT = "https://api.indexnow.org/indexnow"


def main() -> int:
    try:
        xml = open(SITEMAP, encoding="utf-8").read()
    except FileNotFoundError:
        print(f"IndexNow: {SITEMAP} が無いのでスキップ")
        return 0
    urls = re.findall(r"<loc>(.*?)</loc>", xml)[:10000]
    if not urls:
        print("IndexNow: URLが0件なのでスキップ")
        return 0
    body = json.dumps(
        {"host": HOST, "key": KEY, "keyLocation": KEY_LOCATION, "urlList": urls}
    ).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT, data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        r = urllib.request.urlopen(req, timeout=30)
        print(f"IndexNow: 通知成功 status={r.status} urls={len(urls)}")
    except Exception as e:  # noqa: BLE001 — 通知失敗はデプロイを壊さない
        print(f"IndexNow: 通知失敗（非致命・スキップ）: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
