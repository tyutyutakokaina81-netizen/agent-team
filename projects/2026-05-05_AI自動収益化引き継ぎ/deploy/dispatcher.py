"""毎時起動。schedule.json の現在時刻±15分タスクをランダムジッターで実行。

連続CONSECUTIVE_FAIL_LIMIT回失敗で当日停止＋通知。
"""
from __future__ import annotations

import importlib
import sys
import time

import _scheduler

KIND_TO_MODULE = {
    "note": "publish_note",
    "x": "post_x",
    "reddit": "post_reddit",
    "crowdworks": "apply_crowdworks",
}

CONSECUTIVE_FAIL_LIMIT = 5
LIMIT_MSG = f"連続{CONSECUTIVE_FAIL_LIMIT}回失敗：当日の自動化を停止しました"


def notify(message: str) -> None:
    print(f"[NOTIFY] {message}", file=sys.stderr)
    _scheduler.log(f"NOTIFY {message}")


def run_task(task: dict) -> tuple[bool, str]:
    module_name = KIND_TO_MODULE.get(task["kind"])
    if not module_name:
        return False, f"unknown kind: {task['kind']}"
    try:
        mod = importlib.import_module(module_name)
        return mod.run()
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def main() -> None:
    schedule = _scheduler.load()
    if schedule is None:
        _scheduler.log("no schedule for today; run auto_schedule.py first")
        return

    if _scheduler.consecutive_failures(schedule) >= CONSECUTIVE_FAIL_LIMIT:
        notify(LIMIT_MSG)
        return

    for task in _scheduler.due_tasks(schedule):
        wait = _scheduler.jitter_sleep_seconds()
        _scheduler.log(f"jitter sleep {wait}s before {task['kind']}")
        time.sleep(wait)
        success, message = run_task(task)
        _scheduler.mark_completed(schedule, task, success=success, message=message)
        _scheduler.log(f"{task['kind']} -> {'OK' if success else 'FAIL'}: {message}")
        if not success and _scheduler.consecutive_failures(schedule) >= CONSECUTIVE_FAIL_LIMIT:
            notify(LIMIT_MSG)
            return


if __name__ == "__main__":
    main()
