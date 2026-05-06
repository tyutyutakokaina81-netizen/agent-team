"""日次まとめ生成。5本＋応募文を順に走らせ、個別失敗があっても続行する。

成功／失敗を logs/run.log と logs/daily.log に記録し、
全件成功した場合は logs/posted_{date}_{slug}.log にマーカを残す
（公開チェック用に「準備完了」を可視化）。
"""
from __future__ import annotations

import sys
import traceback
from datetime import datetime
from pathlib import Path

from _common import LOGS, OUTPUTS, append_log, date_only
from themes import theme_for

# 個別ジェネレータ
from generate_youtube_short import build_youtube_short
from generate_heygen_script import build_heygen_script
from generate_kling_prompt import build_kling_prompt
from generate_sns_posts import build_sns_posts
from generate_paid_note import build_paid_note
from generate_crowdworks_application import build_crowdworks_application


JOBS = [
    ("youtube_short", build_youtube_short),
    ("heygen_script", build_heygen_script),
    ("kling_prompt", build_kling_prompt),
    ("sns_posts", build_sns_posts),
    ("paid_note", build_paid_note),
    ("crowdworks_application", build_crowdworks_application),
]


def run_all() -> int:
    now = datetime.now()
    theme = theme_for(now.date())
    append_log("run", f"=== START {now.isoformat(timespec='seconds')} theme={theme.slug} ===")

    successes: list[str] = []
    failures: list[tuple[str, str]] = []

    for name, fn in JOBS:
        try:
            path = fn(now)
            successes.append(f"{name} -> {path.name}")
            append_log("run", f"OK {name} {path.name}")
        except Exception as exc:  # noqa: BLE001
            tb = traceback.format_exc(limit=2)
            failures.append((name, str(exc)))
            append_log("run", f"FAILED {name} {exc!r}")
            append_log("run", tb.replace("\n", " | "))

    summary = (
        f"{len(successes)}/{len(JOBS)} jobs succeeded "
        f"(failures: {[f[0] for f in failures] or 'none'})"
    )
    append_log("daily", summary)

    # 全件成功なら準備完了マーカ
    if not failures:
        marker = LOGS / f"posted_{date_only(now)}_{theme.slug}.log"
        with marker.open("a", encoding="utf-8") as f:
            f.write(f"{now.isoformat(timespec='seconds')} READY {len(successes)} files\n")
        append_log("run", f"READY marker written: {marker.name}")

    append_log("run", f"=== END {datetime.now().isoformat(timespec='seconds')} ===")

    print(f"[{now:%Y-%m-%d %H:%M}] テーマ: {theme.title_ja} ({theme.slug})")
    for s in successes:
        print(f"  ✓ {s}")
    for name, err in failures:
        print(f"  ✗ {name}: {err}")
    print(f"\n出力先: {OUTPUTS}")
    print(f"ログ: {LOGS}")

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(run_all())
