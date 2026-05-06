"""投稿補助：最新生成物のパス・本文・コピー用テキストを表示する。

完全自動投稿ではなく、『生成→確認→人間が公開』方式の補助。
"""
from __future__ import annotations

from pathlib import Path

BASE = Path.home() / "ai-auto"
OUT = BASE / "outputs"

TIMESTAMP_SEGMENTS = 2  # YYYY-MM-DD_HHMM is two underscore-separated tokens


def _kind(name: str) -> str:
    parts = name.split("_", TIMESTAMP_SEGMENTS)
    return parts[TIMESTAMP_SEGMENTS] if len(parts) > TIMESTAMP_SEGMENTS else name


def latest(files: list[Path], *, kind_prefix: str, suffix: str) -> Path | None:
    for p in files:
        if p.name.endswith(suffix) and _kind(p.name).startswith(kind_prefix):
            return p
    return None


def show(label: str, path: Path | None) -> None:
    print(f"\n===== {label} =====")
    if path is None:
        print("(該当ファイルなし)")
        return
    print(f"path: {path}")
    print("-" * 40)
    print(path.read_text(encoding="utf-8"))


def main() -> None:
    files = sorted((p for p in OUT.iterdir() if p.is_file()), reverse=True)
    show("note draft", latest(files, kind_prefix="note_draft", suffix=".md")
         or latest(files, kind_prefix="note_", suffix=".md"))
    show("paid note", latest(files, kind_prefix="paid_note_", suffix=".md"))
    show("reddit", latest(files, kind_prefix="reddit_post", suffix=".md"))
    show("youtube short", latest(files, kind_prefix="youtube_short", suffix=".md"))
    show("crowdworks", latest(files, kind_prefix="crowdworks_application", suffix=".txt")
         or latest(files, kind_prefix="cw_apply", suffix=".txt"))
    print("\nヒント：上のテキストをそのままコピーして公開・応募に使ってください。")


if __name__ == "__main__":
    main()
