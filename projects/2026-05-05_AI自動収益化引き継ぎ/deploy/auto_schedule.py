"""朝に1日分のランダム時刻スケジュールを schedule.json に書き出す。"""
from __future__ import annotations

import _scheduler


def main() -> None:
    schedule = _scheduler.build_today_schedule()
    _scheduler.save(schedule)
    print(f"今日の予定（{schedule['date']}）:")
    for t in schedule["tasks"]:
        print(f"  {t['time']}  {t['kind']}")
    _scheduler.log(f"scheduled {len(schedule['tasks'])} tasks for {schedule['date']}")


if __name__ == "__main__":
    main()
