"""投稿の生存確認（BAN早期発見）。

published.csv の直近 CHECK_WINDOW_DAYS 件の URL を HTTP HEAD で確認し、
404/410/403/451 を返したものを「BANまたは削除の疑い」として警告。

cron: 0 9 * * * cd ~/ai-auto && python3 ban_detector.py >> logs/ban_check.log 2>&1
"""
from __future__ import annotations

import csv
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path.home() / "ai-auto"
CSV_PATH = BASE / "published.csv"
LOG = BASE / "logs" / "ban_check.log"

CHECK_WINDOW_DAYS = 14
SUSPICIOUS_STATUS = {403, 404, 410, 451}
TIMEOUT_SEC = 10
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0)"


def _check_url(url: str) -> int | None:
    if not url.startswith(("http://", "https://")):
        return None
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None


def _load_recent() -> list[dict]:
    if not CSV_PATH.exists():
        return []
    cutoff = datetime.now() - timedelta(days=CHECK_WINDOW_DAYS)
    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return [r for r in rows if datetime.fromisoformat(r["timestamp"]) >= cutoff]


def main() -> int:
    rows = _load_recent()
    if not rows:
        print("チェック対象なし（published.csv が空 or 期間内記録なし）")
        return 0

    suspicious = []
    for r in rows:
        url = r.get("url_or_id", "")
        status = _check_url(url)
        if status in SUSPICIOUS_STATUS:
            suspicious.append((r["kind"], r["title"], url, status))

    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')} checked={len(rows)} suspicious={len(suspicious)}\n")
        for kind, title, url, status in suspicious:
            f.write(f"  [{status}] {kind} {title} {url}\n")

    if not suspicious:
        print(f"OK：{len(rows)} 件すべて生存")
        return 0

    print(f"⚠ BAN/削除疑い {len(suspicious)} 件：")
    for kind, title, url, status in suspicious:
        print(f"  [{status}] {kind} '{title}' → {url}")
    print("\n対処：該当サービスの自動投稿を即停止（.env で DRY_RUN=1）")
    return 1


if __name__ == "__main__":
    sys.exit(main())
