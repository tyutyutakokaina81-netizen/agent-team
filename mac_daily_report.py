#!/usr/bin/env python3
"""
mac_daily_report.py — 毎朝8時の日次レポート（Mac通知）
"""
import json
import subprocess
from datetime import datetime
from pathlib import Path

AGENT_DIR = Path(__file__).parent
LOG_FILE = AGENT_DIR / "logs" / "booth_sales.json"
ALERT_FILE = AGENT_DIR / "logs" / "booth_alerts.json"


def notify(title: str, message: str):
    script = f'display notification "{message}" with title "{title}" sound name "Ping"'
    subprocess.run(["osascript", "-e", script], capture_output=True)


def main():
    today = datetime.now().strftime("%Y/%m/%d")

    # 売上データ
    total = 0
    last_checked = "未確認"
    if LOG_FILE.exists():
        try:
            data = json.loads(LOG_FILE.read_text(encoding="utf-8"))
            total = data.get("total_revenue", 0)
            last_checked = data.get("last_checked", "未確認")
        except Exception:
            pass

    # 未解決アラート
    unresolved = []
    if ALERT_FILE.exists():
        try:
            alerts = json.loads(ALERT_FILE.read_text(encoding="utf-8"))
            unresolved = [a for a in alerts if not a.get("resolved", False)]
        except Exception:
            pass

    # レポート出力
    print(f"\n{'='*40}")
    print(f"  日次レポート {today}")
    print(f"{'='*40}")
    print(f"  BOOTH 累計売上: ¥{total:,}")
    print(f"  最終確認: {last_checked}")
    if unresolved:
        print(f"  未解決アラート: {len(unresolved)}件")
        for a in unresolved:
            print(f"    - {a.get('type')}: {a.get('date')}")
    else:
        print(f"  アラート: なし")
    print(f"{'='*40}\n")

    # 通知
    msg = f"BOOTH売上 ¥{total:,}"
    if unresolved:
        msg += f" ／ 要対応{len(unresolved)}件"
    notify(f"おはようございます {today}", msg)


if __name__ == "__main__":
    main()
