#!/usr/bin/env python3
"""CMO/outputs/ の記事を drafts/queue/ に staging するヘルパー。

Cowork はここから pickup して note 公開する。
"""
from __future__ import annotations

import argparse
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "CMO" / "outputs"
QUEUE = ROOT / "drafts" / "queue"
PUBLISHED = ROOT / "drafts" / "published"


def already_published(name: str) -> bool:
    return (PUBLISHED / name).exists()


def stage_one(src: pathlib.Path) -> str:
    if not src.exists():
        return f"SKIP (not found): {src}"
    if not src.name.endswith(".md"):
        return f"SKIP (not markdown): {src.name}"
    if already_published(src.name):
        return f"SKIP (already published): {src.name}"
    QUEUE.mkdir(parents=True, exist_ok=True)
    dest = QUEUE / src.name
    if dest.exists():
        return f"SKIP (already queued): {src.name}"
    shutil.copy2(src, dest)
    return f"STAGED: {src.name}"


def main() -> None:
    p = argparse.ArgumentParser(description="stage CMO articles for publish")
    p.add_argument("files", nargs="*", help="CMO/outputs/*.md to stage")
    p.add_argument("--date", help="stage all CMO/outputs/<date>_*.md")
    p.add_argument("--all-pending", action="store_true",
                   help="stage every article in CMO/outputs/ not yet published")
    args = p.parse_args()

    targets: list[pathlib.Path] = []
    if args.files:
        targets.extend(pathlib.Path(f) for f in args.files)
    if args.date:
        targets.extend(sorted(SRC.glob(f"{args.date}_*.md")))
    if args.all_pending:
        targets.extend(sorted(SRC.glob("*.md")))

    if not targets:
        print("nothing to stage. pass files, --date YYYY-MM-DD, or --all-pending")
        sys.exit(1)

    seen: set[str] = set()
    for t in targets:
        if t.name in seen:
            continue
        seen.add(t.name)
        print(stage_one(t))


if __name__ == "__main__":
    main()
