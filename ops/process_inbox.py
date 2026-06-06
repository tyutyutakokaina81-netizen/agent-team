#!/usr/bin/env python3
"""ops/inbox/ の YAML 指示キューを操作する最小限の CLI。

依存ゼロ（PyYAML 不要）。frontmatter は簡易パーサで読む。

使い方は ops/README.md 参照。
"""
from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent
INBOX = ROOT / "inbox"
PROCESSED = ROOT / "processed"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
KV_RE = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*):\s*(.*)$")


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm_block, body = m.group(1), m.group(2)
    fm: dict[str, str] = {}
    for line in fm_block.splitlines():
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue
        km = KV_RE.match(line)
        if km:
            fm[km.group(1)] = km.group(2).strip()
    return fm, body


def render_frontmatter(fm: dict[str, str], body: str) -> str:
    fm_lines = "\n".join(f"{k}: {v}" for k, v in fm.items())
    return f"---\n{fm_lines}\n---\n{body}"


def find_file(task_id: str) -> pathlib.Path:
    for d in (INBOX, PROCESSED):
        for p in d.glob(f"*{task_id}*.yaml"):
            return p
    raise SystemExit(f"task not found: {task_id}")


def cmd_list(args: argparse.Namespace) -> None:
    files = sorted(INBOX.glob("*.yaml"))
    if not files:
        print("(inbox is empty)")
        return
    rows: list[tuple[str, str, str, str, str, str]] = []
    for p in files:
        fm, _ = parse_frontmatter(p.read_text())
        if args.to and fm.get("to") != args.to:
            continue
        if args.status and fm.get("status") != args.status:
            continue
        rows.append((
            fm.get("id", "?"),
            fm.get("from", "?"),
            fm.get("to", "?"),
            fm.get("type", "?"),
            fm.get("priority", "?"),
            fm.get("status", "?") + " " + fm.get("title", ""),
        ))
    if not rows:
        print("(no matching tasks)")
        return
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    for r in rows:
        print("  ".join(c.ljust(w) for c, w in zip(r, widths)))


def cmd_show(args: argparse.Namespace) -> None:
    p = find_file(args.id)
    print(f"# file: {p}")
    print(p.read_text())


def cmd_take(args: argparse.Namespace) -> None:
    p = find_file(args.id)
    fm, body = parse_frontmatter(p.read_text())
    fm["status"] = "in-progress"
    p.write_text(render_frontmatter(fm, body))
    print(f"took: {fm.get('id')}  ({fm.get('title', '')})")


def cmd_done(args: argparse.Namespace) -> None:
    p = find_file(args.id)
    fm, body = parse_frontmatter(p.read_text())
    fm["status"] = "done"
    now = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    result_block = f"\n\n---\n\n## 結果 ({now})\n\n{args.result}\n"
    p.write_text(render_frontmatter(fm, body + result_block))
    PROCESSED.mkdir(parents=True, exist_ok=True)
    dest = PROCESSED / p.name
    shutil.move(str(p), str(dest))
    print(f"done: {fm.get('id')} → {dest.relative_to(ROOT.parent)}")


def cmd_post(args: argparse.Namespace) -> None:
    INBOX.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().isoformat()
    seq = 1
    while True:
        seq_str = f"{seq:03d}"
        name = f"{today}_{seq_str}_{args.from_}_{args.to}.yaml"
        path = INBOX / name
        if not path.exists():
            break
        seq += 1
    task_id = f"{today}_{seq_str}"
    now = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    fm = {
        "id": task_id,
        "from": args.from_,
        "to": args.to,
        "created": now,
        "priority": args.priority,
        "type": args.type,
        "status": "open",
        "title": args.title,
    }
    body = "\n" + (args.body or "(本文未記入)") + "\n"
    path.write_text(render_frontmatter(fm, body))
    print(f"posted: {path.relative_to(ROOT.parent)}  id={task_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="ops/inbox/ task queue CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="list inbox tasks")
    p_list.add_argument("--to", help="filter by recipient")
    p_list.add_argument("--status", help="filter by status")
    p_list.set_defaults(func=cmd_list)

    p_show = sub.add_parser("show", help="print task content")
    p_show.add_argument("id")
    p_show.set_defaults(func=cmd_show)

    p_take = sub.add_parser("take", help="mark in-progress")
    p_take.add_argument("id")
    p_take.set_defaults(func=cmd_take)

    p_done = sub.add_parser("done", help="finish & move to processed/")
    p_done.add_argument("id")
    p_done.add_argument("--result", required=True, help="result summary")
    p_done.set_defaults(func=cmd_done)

    p_post = sub.add_parser("post", help="create a new task")
    p_post.add_argument("--from", dest="from_", required=True)
    p_post.add_argument("--to", required=True)
    p_post.add_argument("--type", default="instruction")
    p_post.add_argument("--priority", default="normal")
    p_post.add_argument("--title", required=True)
    p_post.add_argument("--body", default="")
    p_post.set_defaults(func=cmd_post)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
