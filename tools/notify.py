"""Discord Webhook 通知（GitHub Actions から呼ばれる）。

DISCORD_WEBHOOK_URL が未設定なら何もせず終了（GitHub Actions のスキップ条件として使う）。
複数行のメッセージは Discord のメッセージ上限 2000 文字まで自動で切り詰める。

使い方:
    python3 tools/notify.py "メッセージ本文"
    python3 tools/notify.py --type success "本日のドラフト準備完了"
    python3 tools/notify.py --type failure "ワークフローが失敗しました"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DISCORD_LIMIT = 1900

PREFIX = {
    "success": "✅",
    "failure": "🚨",
    "info":    "ℹ️",
}


def send(message: str, *, kind: str = "info") -> int:
    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url:
        print("DISCORD_WEBHOOK_URL 未設定。通知をスキップ。")
        return 0

    text = f"{PREFIX.get(kind, '')} {message}"[:DISCORD_LIMIT]
    payload = json.dumps({"content": text}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            print(f"通知送信: HTTP {r.status}")
            return 0
    except urllib.error.HTTPError as e:
        print(f"通知失敗: HTTP {e.code} {e.reason}")
        return 1
    except Exception as e:
        print(f"通知失敗: {type(e).__name__}: {e}")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("message")
    parser.add_argument("--type", default="info", choices=sorted(PREFIX))
    args = parser.parse_args()
    return send(args.message, kind=args.type)


if __name__ == "__main__":
    sys.exit(main())
