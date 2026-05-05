"""note_draft.md の解析共通モジュール。

publish_note.py と post_x.py から共通利用される。
"""
from __future__ import annotations

import re
from pathlib import Path

OUT = Path.home() / "ai-auto" / "outputs"


def latest_note_path() -> Path | None:
    files = sorted(OUT.glob("*note_draft*.md"), reverse=True)
    return files[0] if files else None


def parse(text: str) -> tuple[str, str]:
    m = re.match(r"#\s+(.+?)\n(.*)", text, flags=re.DOTALL)
    if not m:
        return "本日の記事", text.strip()
    return m.group(1).strip(), m.group(2).strip()


def latest_title_and_body() -> tuple[str, str] | None:
    p = latest_note_path()
    if p is None:
        return None
    return parse(p.read_text(encoding="utf-8"))
