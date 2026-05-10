#!/usr/bin/env python3
"""note.com creator article fetcher.

Usage:
    python3 note_fetch.py --user <username> --list --out urls.txt

Output (urls.txt) format: one entry per line, tab-separated:
    <url>\t<title>
"""

import argparse
import sys
import time

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


def fetch_articles(user: str, kind: str = "note", sleep_sec: float = 0.4):
    """Page through the public note API and collect articles."""
    items = []
    page = 1
    while True:
        params = {"kind": kind, "page": page}
        resp = requests.get(
            API_URL.format(user=user),
            params=params,
            headers=HEADERS,
            timeout=30,
        )
        if resp.status_code == 404:
            print(f"User not found: {user}", file=sys.stderr)
            sys.exit(3)
        resp.raise_for_status()
        payload = resp.json()
        data = payload.get("data", {})
        contents = data.get("contents", [])
        if not contents:
            break
        for c in contents:
            key = c.get("key") or ""
            note_url = (
                c.get("noteUrl")
                or (f"https://note.com/{user}/n/{key}" if key else "")
            )
            title = (c.get("name") or "").replace("\t", " ").replace("\n", " ").strip()
            if note_url:
                items.append((note_url, title))
        if data.get("isLastPage", True):
            break
        page += 1
        time.sleep(sleep_sec)
    return items


def main():
    p = argparse.ArgumentParser(description="Fetch note.com article list for a user.")
    p.add_argument("--user", required=True, help="note.com username (URL slug)")
    p.add_argument("--list", action="store_true", help="emit list of urls/titles")
    p.add_argument("--out", default="urls.txt", help="output file path")
    p.add_argument("--kind", default="note", choices=["note", "magazine"])
    args = p.parse_args()

    items = fetch_articles(args.user, kind=args.kind)

    if args.list:
        with open(args.out, "w", encoding="utf-8") as f:
            for url, title in items:
                f.write(f"{url}\t{title}\n")
        print(f"Wrote {len(items)} entries to {args.out}", file=sys.stderr)
    else:
        for url, title in items:
            print(f"{url}\t{title}")


if __name__ == "__main__":
    main()
