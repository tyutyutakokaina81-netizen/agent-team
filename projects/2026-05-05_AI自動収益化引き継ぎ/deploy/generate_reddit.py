"""Reddit投稿文生成（API不要）。

英語タイトル＋本文のテンプレを outputs/ に書き出す。
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

BASE = Path.home() / "ai-auto"
OUT = BASE / "outputs"
OUT.mkdir(parents=True, exist_ok=True)


def build(theme: str) -> str:
    return f"""Title:
{theme}

Body:
I live in a local city in Japan, far from the speed of Tokyo.
There is nothing dramatic here, but that may be exactly why it feels peaceful.

Small streets, quiet mornings, seasonal food, and ordinary routines.
Sometimes, a simple life feels richer than an exciting one.

Do you ever feel the same?

Subreddit candidates:
- r/Japan
- r/JapanTravel
- r/SlowLiving
- r/simpleliving
"""


def main() -> None:
    theme = sys.argv[1] if len(sys.argv) > 1 else "A quiet life in a small Japanese town"
    today = datetime.now().strftime("%Y-%m-%d_%H%M")
    path = OUT / f"{today}_reddit_post.md"
    path.write_text(build(theme), encoding="utf-8")
    print(f"生成完了: {path}")


if __name__ == "__main__":
    main()
