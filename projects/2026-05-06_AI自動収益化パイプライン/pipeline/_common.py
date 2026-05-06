"""パイプライン共通ユーティリティ。"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = PROJECT_ROOT / "outputs"
LOGS = PROJECT_ROOT / "logs"
PROMPTS = PROJECT_ROOT / "prompts"

OUTPUTS.mkdir(exist_ok=True)
LOGS.mkdir(exist_ok=True)


def stamp(now: datetime | None = None) -> str:
    """ファイル名先頭の日時スタンプ（YYYY-MM-DD_HHMM）。"""
    now = now or datetime.now()
    return now.strftime("%Y-%m-%d_%H%M")


def date_only(now: datetime | None = None) -> str:
    now = now or datetime.now()
    return now.strftime("%Y-%m-%d")


def write_output(filename: str, body: str) -> Path:
    """outputs/ にUTF-8で書き出して、書き出したパスを返す。"""
    path = OUTPUTS / filename
    path.write_text(body, encoding="utf-8")
    return path


def append_log(name: str, message: str) -> None:
    """logs/{name}.log に1行追記。"""
    log_path = LOGS / f"{name}.log"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')} {message}\n")


def write_post_marker(slug: str, kind: str, output_path: Path) -> Path:
    """`logs/posted_{date}_{slug}.log` を作る（公開チェック用マーカ）。"""
    marker = LOGS / f"posted_{date_only()}_{slug}.log"
    line = f"{datetime.now().isoformat(timespec='seconds')} {kind} {output_path.name}\n"
    with marker.open("a", encoding="utf-8") as f:
        f.write(line)
    return marker


def env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)
