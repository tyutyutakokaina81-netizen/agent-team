"""
01_select_topics.py — 本日の3トピックを選定（毎日違う内容を担保）

topic_pool.md のトピックID群から、state.json の used を除いた未使用を
「食 / 文化 / 歴史・自然」のグループからバランスよく3本選ぶ。
全消化したら used をリセットし、angle（切り口）を進める。
"""

import json
import random
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
STATE = Path(__file__).resolve().parent / "state.json"

# topic_pool.md と対応（IDのみ管理。説明は md 側を正とする）
GROUPS = {
    "food":    ["F01", "F02", "F03", "F04", "F05", "F06", "F07", "F08"],
    "culture": ["C01", "C02", "C03", "C04", "C05", "C06"],
    "history": ["H01", "H02", "H03", "H04", "H05", "H06"],
}
ANGLES = ["一人旅", "家族と", "友人と", "雨の日", "朝いちばん", "夕暮れ"]


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"used": [], "angle_index": 0}


def save_state(state):
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def pick_one(group, used):
    candidates = [t for t in GROUPS[group] if t not in used]
    return random.choice(candidates) if candidates else None


def select_today(n=3):
    state = load_state()
    used = set(state["used"])

    picks = []
    # まず各グループから1本ずつ（バランス）
    for group in ["food", "culture", "history"]:
        t = pick_one(group, used)
        if t:
            picks.append(t)
            used.add(t)

    # 3本に満たない/超える調整
    all_remaining = [t for g in GROUPS.values() for t in g if t not in used]
    while len(picks) < n and all_remaining:
        t = random.choice(all_remaining)
        picks.append(t)
        used.add(t)
        all_remaining.remove(t)
    picks = picks[:n]

    # 全消化チェック → リセットして切り口を進める
    total = sum(len(v) for v in GROUPS.values())
    if len(used) >= total:
        state["used"] = []
        state["angle_index"] = (state.get("angle_index", 0) + 1) % len(ANGLES)
    else:
        state["used"] = list(used)

    save_state(state)
    angle = ANGLES[state.get("angle_index", 0)]
    return [{"topic_id": t, "angle": angle} for t in picks]


if __name__ == "__main__":
    today = select_today()
    print(json.dumps(today, ensure_ascii=False, indent=2))
