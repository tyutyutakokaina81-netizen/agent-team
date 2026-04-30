#!/usr/bin/env python3
"""
auto_x_api_post.py — X API v2でサーバーから直接投稿（¥0・Chrome不要）

【セットアップ（5分・無料）】
1. https://developer.twitter.com → 「Sign up」→ 無料プラン選択
2. Project作成 → App作成 → 「Keys and Tokens」タブ
3. 以下の4つをコピーして環境変数に設定:

   export X_API_KEY="..."
   export X_API_SECRET="..."
   export X_ACCESS_TOKEN="..."
   export X_ACCESS_SECRET="..."

4. python3 auto_x_api_post.py → 投稿される

無料枠: 月1,500ツイートまで（十分）
"""

import base64
import hashlib
import hmac
import json
import os
import time
import urllib.parse
import urllib.request
import random
import string
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).parent
QUEUE_FILE = REPO / ".sessions" / "x_post_queue.json"
EXTRA_FILE = REPO / ".sessions" / "x_extra_posts.json"
LOG_FILE = REPO / ".sessions" / "x_api_post_log.json"

API_KEY = os.environ.get("X_API_KEY", "")
API_SECRET = os.environ.get("X_API_SECRET", "")
ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN", "")
ACCESS_SECRET = os.environ.get("X_ACCESS_SECRET", "")


# ─── OAuth 1.0a 署名（標準ライブラリのみ） ─────────────────────

def _nonce() -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))


def _percent(s: str) -> str:
    return urllib.parse.quote(str(s), safe='')


def _sign(method: str, url: str, params: dict, consumer_secret: str, token_secret: str) -> str:
    sorted_params = sorted(params.items())
    param_string = "&".join(f"{_percent(k)}={_percent(v)}" for k, v in sorted_params)
    base = "&".join([method.upper(), _percent(url), _percent(param_string)])
    signing_key = f"{_percent(consumer_secret)}&{_percent(token_secret)}"
    hashed = hmac.new(signing_key.encode(), base.encode(), hashlib.sha1)
    return base64.b64encode(hashed.digest()).decode()


def make_auth_header(method: str, url: str, extra_params: dict | None = None) -> str:
    ts = str(int(time.time()))
    oauth_params = {
        "oauth_consumer_key": API_KEY,
        "oauth_nonce": _nonce(),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": ts,
        "oauth_token": ACCESS_TOKEN,
        "oauth_version": "1.0",
    }
    all_params = {**oauth_params, **(extra_params or {})}
    oauth_params["oauth_signature"] = _sign(method, url, all_params, API_SECRET, ACCESS_SECRET)

    header_parts = [f'{k}="{_percent(v)}"' for k, v in sorted(oauth_params.items())]
    return "OAuth " + ", ".join(header_parts)


# ─── X API v2 投稿 ────────────────────────────────────────────

def post_tweet(text: str) -> dict:
    url = "https://api.twitter.com/2/tweets"
    body = json.dumps({"text": text}).encode("utf-8")
    auth = make_auth_header("POST", url)
    req = urllib.request.Request(
        url, data=body,
        headers={
            "Authorization": auth,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as res:
        return json.loads(res.read().decode())


def check_credentials() -> bool:
    return all([API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET])


# ─── キュー管理 ────────────────────────────────────────────────

def get_next_post() -> tuple[str, str] | None:
    """キューから未投稿の1本を取得（key, text）"""
    if QUEUE_FILE.exists():
        q = json.loads(QUEUE_FILE.read_text())
        for key, v in q.items():
            if not v.get("posted") and v.get("text"):
                return key, v["text"], "queue"

    if EXTRA_FILE.exists():
        extras = json.loads(EXTRA_FILE.read_text())
        for i, p in enumerate(extras):
            if not p.get("posted") and p.get("text"):
                return f"extra_{i}", p["text"], "extra"

    return None


def mark_posted(key: str, source: str):
    now = datetime.now().isoformat()
    if source == "queue" and QUEUE_FILE.exists():
        q = json.loads(QUEUE_FILE.read_text())
        if key in q:
            q[key]["posted"] = True
            q[key]["posted_at"] = now
            QUEUE_FILE.write_text(json.dumps(q, ensure_ascii=False, indent=2))

    elif source == "extra" and EXTRA_FILE.exists():
        idx = int(key.split("_")[1])
        extras = json.loads(EXTRA_FILE.read_text())
        if idx < len(extras):
            extras[idx]["posted"] = True
            extras[idx]["posted_at"] = now
            EXTRA_FILE.write_text(json.dumps(extras, ensure_ascii=False, indent=2))


def load_log() -> dict:
    if LOG_FILE.exists():
        return json.loads(LOG_FILE.read_text())
    return {"posts": []}


def save_log(log: dict):
    LOG_FILE.write_text(json.dumps(log, ensure_ascii=False, indent=2))


# ─── メイン ──────────────────────────────────────────────────

def run():
    print("━" * 45)
    print("  X API 直接投稿")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("━" * 45)

    if not check_credentials():
        print("""
  ⚠️  X API 認証情報が未設定です

  【無料セットアップ（5分）】
  1. https://developer.twitter.com にアクセス
  2. 「Sign up for Free Account」
  3. Project → App → Keys and Tokens タブ
  4. 以下を ~/.zshrc に追加:

     export X_API_KEY="your_key"
     export X_API_SECRET="your_secret"
     export X_ACCESS_TOKEN="your_token"
     export X_ACCESS_SECRET="your_token_secret"

  5. source ~/.zshrc && python3 auto_x_api_post.py

  設定後は Mac不要・サーバーから自動投稿されます。
""")
        return False

    item = get_next_post()
    if not item:
        print("  ✅ 投稿キューが空（全投稿済み）")
        return True

    key, text, source = item
    print(f"  投稿: {text[:60]}...")

    try:
        result = post_tweet(text)
        tweet_id = result.get("data", {}).get("id", "")
        print(f"  ✅ 投稿完了: https://x.com/i/web/status/{tweet_id}")

        mark_posted(key, source)

        log = load_log()
        log["posts"].append({
            "key": key, "text": text[:100],
            "tweet_id": tweet_id,
            "posted_at": datetime.now().isoformat(),
        })
        log["posts"] = log["posts"][-100:]
        save_log(log)
        return True

    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  ❌ 投稿失敗: HTTP {e.code}")
        print(f"  {body[:200]}")
        return False
    except Exception as e:
        print(f"  ❌ エラー: {e}")
        return False


if __name__ == "__main__":
    run()
