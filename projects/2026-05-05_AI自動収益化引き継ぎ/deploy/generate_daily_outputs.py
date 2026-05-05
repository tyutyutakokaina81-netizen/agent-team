"""日次生成：note下書き / Reddit投稿文 / YouTube Shorts台本 / CrowdWorks応募文。

API不要。テーマは prompts/themes.json から日付ベースでローテ選択する。
generate_note / generate_reddit / generate_youtube_short / cw_apply の build() を再利用。
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path

BASE = Path.home() / "ai-auto"
OUT = BASE / "outputs"
LOG = BASE / "logs"
THEMES = BASE / "prompts" / "themes.json"

sys.path.insert(0, str(BASE))
from generate_note import build as build_note  # noqa: E402
from generate_reddit import build as build_reddit  # noqa: E402
from generate_youtube_short import build as build_youtube  # noqa: E402
from cw_apply import build as build_cw  # noqa: E402


def pick(items: list[str]) -> str:
    return items[date.today().toordinal() % len(items)]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    LOG.mkdir(parents=True, exist_ok=True)

    themes = json.loads(THEMES.read_text(encoding="utf-8"))
    note_theme = pick(themes["note"])
    reddit_theme = pick(themes["reddit"])
    youtube_theme = pick(themes["youtube"])

    today = datetime.now().strftime("%Y-%m-%d_%H%M")
    files = {
        f"{today}_note_draft.md": build_note(note_theme),
        f"{today}_reddit_post.md": build_reddit(reddit_theme),
        f"{today}_youtube_short.md": build_youtube(youtube_theme),
        f"{today}_crowdworks_application.txt": build_cw(
            "データ入力・リスト作成のお仕事", "data"
        ),
    }
    for name, body in files.items():
        (OUT / name).write_text(body, encoding="utf-8")

    with (LOG / "daily.log").open("a", encoding="utf-8") as f:
        f.write(
            f"{datetime.now().isoformat(timespec='seconds')}"
            f" note='{note_theme}' reddit='{reddit_theme}' youtube='{youtube_theme}'\n"
        )

    print("生成完了：outputs フォルダを確認してください。")
    for name in files:
        print(f"  - outputs/{name}")


if __name__ == "__main__":
    main()
