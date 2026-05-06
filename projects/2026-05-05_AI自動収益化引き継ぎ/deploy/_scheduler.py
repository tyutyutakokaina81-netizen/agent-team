"""日次スケジュール管理。

dispatcher は毎時起動し、現在時刻±DISPATCH_WINDOW_MIN 分の pending タスクを実行。
当日リセット前提のため日跨ぎは想定しない（00:05 に 23:50 タスクは実行されない）。
"""
from __future__ import annotations

import json
import random
from datetime import date, datetime
from pathlib import Path

BASE = Path.home() / "ai-auto"
SCHEDULE = BASE / "schedule.json"
LOG = BASE / "logs" / "scheduler.log"

DISPATCH_WINDOW_MIN = 15
JITTER_SECONDS_MAX = 300
DAILY_LIMITS = {"note": 1, "x": 3, "reddit": 1, "crowdworks": 3}

TIME_SLOTS = {
    "note": [(7, 9), (12, 13), (21, 22)],
    "x": [(7, 9), (12, 13), (18, 20)],
    "reddit": [(22, 23), (5, 7)],  # 米国の朝（日本の深夜〜早朝）
    "crowdworks": [(10, 12), (13, 17)],  # 平日業務時間帯
}


def _random_time(slot: tuple[int, int]) -> str:
    h_start, h_end = slot
    minute = random.randint(0, 59)
    hour = random.randint(h_start, h_end - 1)
    return f"{hour:02d}:{minute:02d}"


def build_today_schedule() -> dict:
    today = date.today()
    is_weekday = today.weekday() < 5

    tasks: list[dict] = []
    for kind, slots in TIME_SLOTS.items():
        if kind == "crowdworks" and not is_weekday:
            continue
        n = min(DAILY_LIMITS.get(kind, 1), len(slots))
        for slot in random.sample(slots, n):
            tasks.append({
                "time": _random_time(slot),
                "kind": kind,
                "status": "pending",
                "attempted_at": None,
                "result": None,
            })
    tasks.sort(key=lambda t: t["time"])
    return {"date": today.isoformat(), "tasks": tasks}


def save(schedule: dict) -> None:
    SCHEDULE.write_text(json.dumps(schedule, ensure_ascii=False, indent=2), encoding="utf-8")


def load() -> dict | None:
    if not SCHEDULE.exists():
        return None
    sched = json.loads(SCHEDULE.read_text(encoding="utf-8"))
    if sched.get("date") != date.today().isoformat():
        return None
    return sched


def due_tasks(schedule: dict, *, now: datetime | None = None) -> list[dict]:
    now = now or datetime.now()
    out = []
    for task in schedule.get("tasks", []):
        if task.get("status") != "pending":
            continue
        h, m = map(int, task["time"].split(":"))
        target = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if abs((now - target).total_seconds()) <= DISPATCH_WINDOW_MIN * 60:
            out.append(task)
    return out


def mark_completed(schedule: dict, task: dict, *, success: bool, message: str) -> None:
    task["status"] = "done" if success else "failed"
    task["attempted_at"] = datetime.now().isoformat(timespec="seconds")
    task["result"] = message
    save(schedule)


def consecutive_failures(schedule: dict) -> int:
    count = 0
    for t in reversed(schedule.get("tasks", [])):
        if t.get("status") == "failed":
            count += 1
        elif t.get("status") == "done":
            break
    return count


def jitter_sleep_seconds() -> int:
    return random.randint(0, JITTER_SECONDS_MAX)


def log(message: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')} {message}\n")
