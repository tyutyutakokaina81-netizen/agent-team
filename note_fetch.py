#!/usr/bin/env python3
"""note.com creator article fetcher.

note.com の指定ユーザーの全記事を取得し、URL とタイトル（任意でメタデータ）を
出力するスクリプト。

Usage:
    # URL+タイトルを TSV で urls.txt に書き出す
    python3 note_fetch.py --user <username> --list --out urls.txt

    # JSON 形式でフルメタデータを書き出す
    python3 note_fetch.py --user <username> --json --out urls.json

    # 標準出力に流す
    python3 note_fetch.py --user <username>

設計方針:
  - 公開 API (/api/v2/creators/{user}/contents) を主経路として利用
  - 一時的なネットワーク失敗にはリトライ（指数バックオフ）で耐える
  - 403/レート制限などで API が継続的に失敗した場合は HTML
    フォールバックを試みる（Nuxt の埋め込み JSON を抽出）
  - HTML フォールバックも失敗した場合は明確なエラーメッセージで終了
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from typing import Iterator

try:
    import requests
except ImportError:
    print(
        "ImportError: requests not installed. "
        "Run: pip install requests",
        file=sys.stderr,
    )
    sys.exit(2)


API_URL = "https://note.com/api/v2/creators/{user}/contents"
USER_PAGE_URL = "https://note.com/{user}"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Referer": "https://note.com/",
    "X-Requested-With": "XMLHttpRequest",
}

MAX_RETRIES = 4
BACKOFF_SEC = (2.0, 4.0, 8.0, 16.0)


def _request_with_retry(
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
) -> requests.Response:
    """403/5xx/ネットワーク失敗時は指数バックオフでリトライする。"""
    last_err: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(
                url, params=params, headers=headers or HEADERS, timeout=30
            )
            if resp.status_code == 429 or 500 <= resp.status_code < 600:
                raise requests.HTTPError(
                    f"{resp.status_code} {resp.reason}", response=resp
                )
            return resp
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
            last_err = e
            if attempt < MAX_RETRIES:
                wait = BACKOFF_SEC[attempt]
                print(
                    f"  retry {attempt + 1}/{MAX_RETRIES} after {wait}s: {e}",
                    file=sys.stderr,
                )
                time.sleep(wait)
            else:
                break
    assert last_err is not None
    raise last_err


def _normalize(c: dict, user: str) -> dict:
    """API レスポンス 1 件 → 正規化済み dict。"""
    key = c.get("key") or ""
    note_url = c.get("noteUrl") or (
        f"https://note.com/{user}/n/{key}" if key else ""
    )
    title = (c.get("name") or "").replace("\t", " ").replace("\n", " ").strip()
    return {
        "url": note_url,
        "title": title,
        "key": key,
        "type": c.get("type"),
        "status": c.get("status"),
        "publish_at": c.get("publishAt"),
        "like_count": c.get("likeCount"),
        "comment_count": c.get("commentCount"),
        "price": c.get("price"),
        "description": (c.get("description") or "").strip(),
    }


def fetch_via_api(user: str, kind: str = "note", sleep_sec: float = 0.4) -> list[dict]:
    """公開 API でページングしながら全記事を収集。"""
    items: list[dict] = []
    page = 1
    while True:
        print(f"[api] page {page} …", file=sys.stderr)
        resp = _request_with_retry(
            API_URL.format(user=user),
            params={"kind": kind, "page": page},
        )
        if resp.status_code == 404:
            raise LookupError(f"User not found: {user}")
        resp.raise_for_status()
        payload = resp.json()
        data = payload.get("data", {})
        contents = data.get("contents", [])
        if not contents:
            break
        for c in contents:
            norm = _normalize(c, user)
            if norm["url"]:
                items.append(norm)
        if data.get("isLastPage", True):
            break
        page += 1
        time.sleep(sleep_sec)
    return items


_NUXT_RE = re.compile(r"window\.__NUXT__\s*=\s*(.+?);\s*</script>", re.DOTALL)


def _iter_nested_articles(node) -> Iterator[dict]:
    """埋め込み JSON 内で記事らしき dict を再帰的に走査する。"""
    if isinstance(node, dict):
        if (node.get("key") or node.get("noteUrl")) and node.get("name"):
            yield node
        for v in node.values():
            yield from _iter_nested_articles(v)
    elif isinstance(node, list):
        for v in node:
            yield from _iter_nested_articles(v)


def fetch_via_html(user: str) -> list[dict]:
    """HTML 経由のフォールバック。Nuxt の埋め込み JSON を抽出する。"""
    print("[html] fallback: parsing user page HTML …", file=sys.stderr)
    resp = _request_with_retry(USER_PAGE_URL.format(user=user))
    if resp.status_code == 404:
        raise LookupError(f"User not found: {user}")
    resp.raise_for_status()
    html = resp.text
    m = _NUXT_RE.search(html)
    if not m:
        raise RuntimeError("Could not locate __NUXT__ block in user page HTML")
    raw = m.group(1).strip()
    if raw.startswith("(function"):
        raise RuntimeError(
            "Nuxt block is in function-form; static parse unsupported. "
            "Please use the API path or supply urls.txt manually."
        )
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse Nuxt JSON: {e}") from e
    seen = set()
    items: list[dict] = []
    for c in _iter_nested_articles(data):
        norm = _normalize(c, user)
        if norm["url"] and norm["url"] not in seen:
            seen.add(norm["url"])
            items.append(norm)
    return items


def fetch_articles(user: str, kind: str = "note") -> list[dict]:
    """API → HTML の順で取得を試み、最初に成功した結果を返す。"""
    try:
        items = fetch_via_api(user, kind=kind)
        if items:
            return items
        print(
            "[api] returned 0 items — trying HTML fallback", file=sys.stderr
        )
    except (requests.HTTPError, requests.ConnectionError, requests.Timeout) as e:
        print(f"[api] failed ({e}) — trying HTML fallback", file=sys.stderr)
    return fetch_via_html(user)


def main() -> int:
    p = argparse.ArgumentParser(
        description="Fetch note.com article list for a user."
    )
    p.add_argument("--user", required=True, help="note.com username (URL slug)")
    p.add_argument("--list", action="store_true", help="emit TSV list (url<TAB>title)")
    p.add_argument("--json", action="store_true", help="emit JSON with full metadata")
    p.add_argument("--out", default="urls.txt", help="output file path")
    p.add_argument("--kind", default="note", choices=["note", "magazine"])
    args = p.parse_args()

    try:
        items = fetch_articles(args.user, kind=args.kind)
    except LookupError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 3
    except (requests.HTTPError, requests.ConnectionError, requests.Timeout) as e:
        print(
            f"ERROR: network failure after retries: {e}\n"
            "  Hint: check egress allowlist for note.com, "
            "or run from a machine with internet access.",
            file=sys.stderr,
        )
        return 4
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 5

    if not items:
        print("WARN: 0 articles found", file=sys.stderr)

    if args.json:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        print(f"Wrote {len(items)} entries (JSON) to {args.out}", file=sys.stderr)
    elif args.list:
        with open(args.out, "w", encoding="utf-8") as f:
            for it in items:
                f.write(f"{it['url']}\t{it['title']}\n")
        print(f"Wrote {len(items)} entries (TSV) to {args.out}", file=sys.stderr)
    else:
        for it in items:
            print(f"{it['url']}\t{it['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
