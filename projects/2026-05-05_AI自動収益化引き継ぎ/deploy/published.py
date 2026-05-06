"""公開記録：published.csv に1行追記する。

使い方:
    python3 published.py note "https://note.com/xxx/n/abc" "タイトル" 0
    python3 published.py paid_note "https://..." "タイトル" 980
    python3 published.py reddit "https://reddit.com/..." "Title" 0
    python3 published.py shorts "https://youtube.com/shorts/..." "タイトル" 0
    python3 published.py crowdworks "案件名" "応募" 0

カラム: timestamp, kind, url_or_id, title, revenue_jpy
"""
from __future__ import annotations

import csv
import sys
from datetime import datetime
from pathlib import Path

BASE = Path.home() / "ai-auto"
CSV_PATH = BASE / "published.csv"

VALID_KINDS = {
    "note", "paid_note", "reddit", "shorts", "x", "crowdworks",
    "writer", "seo_article", "ai_support", "consultant", "proposal",
}
HEADER = ["timestamp", "kind", "url_or_id", "title", "revenue_jpy"]


def append(kind: str, url: str, title: str, revenue: int) -> None:
    if kind not in VALID_KINDS:
        raise ValueError(f"kind は {sorted(VALID_KINDS)} のいずれか")
    write_header = not CSV_PATH.exists()
    with CSV_PATH.open("a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(HEADER)
        w.writerow([datetime.now().isoformat(timespec="seconds"), kind, url, title, revenue])


def main() -> None:
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    kind = sys.argv[1]
    url = sys.argv[2]
    title = sys.argv[3]
    revenue = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    append(kind, url, title, revenue)
    print(f"記録：{kind} / {title} / ¥{revenue} → {CSV_PATH}")


if __name__ == "__main__":
    main()
