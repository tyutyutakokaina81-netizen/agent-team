#!/usr/bin/env python3
"""
agent_dispatch.py — タスクディスパッチャー（分業・カバー制御）

役割:
1. タスクキューからタスクを取り出し、担当エージェントに割り振る
2. 担当が「ビジー」なら、カバー可能なエージェントに自動転送
3. 依存関係に基づいてフェーズ分割、フェーズ内は並列実行
4. 全タスクの実行ログを残す

カバールール:
  CRO ←→ CDO  (調査・分析)
  CMO ←→ CPO  (コンテンツ・制作)
  CSO ←→ CGO  (営業・開拓)
  COO ←→ CFO  (運用・管理)
  CBO ←→ CEO  (意思決定)
"""

import json
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, date
from pathlib import Path

REPO = Path(__file__).parent
SESSIONS = REPO / ".sessions"
SESSIONS.mkdir(exist_ok=True)

TASK_QUEUE_FILE = SESSIONS / "task_queue.json"
AGENT_STATUS_FILE = SESSIONS / "agent_status.json"
DISPATCH_LOG_FILE = SESSIONS / "dispatch_log.json"
TODAY = date.today().isoformat()

# ── カバールール（主担当 → バックアップ） ────────────────────
COVERAGE = {
    "CRO": ["CDO", "CMO"],
    "CMO": ["CPO", "CDO"],
    "CPO": ["CMO", "CCO"],
    "CSO": ["CGO", "COO"],
    "CGO": ["CSO", "CMO"],
    "COO": ["CFO", "CDO"],
    "CFO": ["COO", "CEO"],
    "CBO": ["CEO", "CDO"],
    "CDO": ["COO", "CRO"],
    "CCO": ["CPO", "CMO"],
    "CEO": ["CBO", "COO"],
}

# ── エージェント → スクリプト マッピング ─────────────────────
AGENT_SCRIPTS = {
    "CRO": "agent_cro.py",
    "CMO": "auto_content_loop.py",
    "CPO": None,
    "CSO": "auto_job_apply.py",
    "CGO": None,
    "COO": "agent_coo.py",
    "CFO": "agent_cfo.py",
    "CBO": "agent_cbo.py",
    "CDO": "auto_self_eval.py",
    "CCO": None,
    "CEO": "agent_ceo.py",
}

# ── タスク定義（depends_on: 先行タスクIDリスト） ──────────────
DEFAULT_TASKS = [
    # フェーズ0: 依存なし（並列実行）
    {"id": "T001", "name": "トレンド調査",       "owner": "CRO", "priority": 1, "script": "agent_cro.py",           "depends_on": []},
    {"id": "T002", "name": "コンテンツ生成",      "owner": "CMO", "priority": 1, "script": "auto_content_loop.py",   "depends_on": []},
    {"id": "T003", "name": "YouTube動画生成",     "owner": "CMO", "priority": 2, "script": "auto_youtube_produce.py","depends_on": []},
    {"id": "T004", "name": "Shorts生成",          "owner": "CMO", "priority": 2, "script": "auto_youtube_shorts.py", "depends_on": []},
    {"id": "T005", "name": "案件サーチ",           "owner": "CSO", "priority": 1, "script": "auto_job_hunt.py",       "depends_on": []},
    {"id": "T006", "name": "運用チェック",         "owner": "COO", "priority": 2, "script": "agent_coo.py",           "depends_on": []},
    {"id": "T007", "name": "財務レポート",         "owner": "CFO", "priority": 3, "script": "agent_cfo.py",           "depends_on": []},
    {"id": "T009", "name": "自己評価",             "owner": "CDO", "priority": 3, "script": "auto_self_eval.py",      "depends_on": []},
    {"id": "T010", "name": "写真素材取得",         "owner": "CMO", "priority": 3, "script": "auto_wikimedia_photos.py","depends_on": []},
    {"id": "T011", "name": "アフィリエイト処理",  "owner": "CCO", "priority": 3, "script": "auto_affiliate.py",      "depends_on": []},
    {"id": "T012", "name": "横断変換",             "owner": "CMO", "priority": 3, "script": "auto_repurpose.py",      "depends_on": []},
    # フェーズ1: CROのトレンド結果に依存
    {"id": "T008", "name": "稟議生成",             "owner": "CBO", "priority": 2, "script": "agent_cbo.py",           "depends_on": ["T001"]},
    # フェーズ2: CBO稟議結果に依存（週次のみ）
    {"id": "T013", "name": "週次統括",             "owner": "CEO", "priority": 1, "script": "agent_ceo.py",           "depends_on": ["T008"]},
]


# ── エージェント状態管理 ─────────────────────────────────────
def load_status() -> dict:
    if AGENT_STATUS_FILE.exists():
        return json.loads(AGENT_STATUS_FILE.read_text())
    return {agent: {"status": "available", "current_task": None, "completed": 0, "failed": 0}
            for agent in COVERAGE}


def save_status(status: dict):
    AGENT_STATUS_FILE.write_text(json.dumps(status, ensure_ascii=False, indent=2))


def load_log() -> dict:
    if DISPATCH_LOG_FILE.exists():
        return json.loads(DISPATCH_LOG_FILE.read_text())
    return {"runs": []}


def save_log(log: dict):
    log["runs"] = log["runs"][-200:]
    DISPATCH_LOG_FILE.write_text(json.dumps(log, ensure_ascii=False, indent=2))


# ── タスク実行 ────────────────────────────────────────────────
def run_task(task: dict, executor: str, status: dict, log: dict,
             status_lock: threading.Lock, log_lock: threading.Lock) -> bool:
    script = task.get("script")
    if not script or not (REPO / script).exists():
        print(f"    [{executor}] スクリプトなし: {script} → スキップ")
        return False

    # 実行前にビジーマーク
    with status_lock:
        status[executor]["status"] = "busy"
        status[executor]["current_task"] = task["id"]

    print(f"    [{executor}] 実行: {task['name']} ({script})")
    start = time.time()
    success = False
    try:
        result = subprocess.run(
            [sys.executable, str(REPO / script)],
            capture_output=True, text=True, timeout=90
        )
        elapsed = round(time.time() - start, 1)
        success = result.returncode == 0

        icon = "✅" if success else "❌"
        cover_note = f"（{task['owner']}の代理）" if executor != task["owner"] else ""
        print(f"    {icon} {task['name']} {cover_note} {elapsed}秒")

    except subprocess.TimeoutExpired:
        elapsed = round(time.time() - start, 1)
        print(f"    ⏱️ タイムアウト: {task['name']}")
    except Exception as e:
        elapsed = round(time.time() - start, 1)
        print(f"    ❌ エラー: {e}")

    # 実行後にavailableに戻す＋カウント更新
    with status_lock:
        status[executor]["status"] = "available"
        status[executor]["current_task"] = None
        if success:
            status[executor]["completed"] += 1
        else:
            status[executor]["failed"] += 1

    with log_lock:
        log["runs"].append({
            "at": datetime.now().isoformat(),
            "task": task["id"],
            "name": task["name"],
            "owner": task["owner"],
            "executor": executor,
            "covered": executor != task["owner"],
            "success": success,
            "elapsed_sec": elapsed,
        })

    return success


def find_executor(task: dict, status: dict, status_lock: threading.Lock) -> str | None:
    """タスクを実行できるエージェントを探す（ビジーならカバーへ）"""
    owner = task["owner"]
    with status_lock:
        if status.get(owner, {}).get("status") == "available":
            return owner
        for backup in COVERAGE.get(owner, []):
            if status.get(backup, {}).get("status") == "available":
                print(f"    ⚡ {owner}がビジー → {backup}がカバー")
                return backup
    return None


# ── フェーズ分割ヘルパー ─────────────────────────────────────
def build_phases(tasks: list) -> list[list]:
    """依存関係を解析してフェーズごとのリストに分割する"""
    task_map = {t["id"]: t for t in tasks}
    completed_ids: set = set()
    remaining = list(tasks)
    phases = []

    while remaining:
        # 依存が全て完了しているタスクをこのフェーズに
        ready = [t for t in remaining if all(d in completed_ids for d in t.get("depends_on", []))]
        if not ready:
            # 循環依存などで詰まった場合は残りを全部入れて終了
            phases.append(remaining)
            break
        phases.append(sorted(ready, key=lambda t: t["priority"]))
        completed_ids.update(t["id"] for t in ready)
        remaining = [t for t in remaining if t["id"] not in completed_ids]

    return phases


# ── メイン実行 ────────────────────────────────────────────────
def run(tasks: list = None, mode: str = "daily"):
    print("━" * 50)
    print("  DISPATCH — タスク分配・カバー制御")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')} [{mode}モード]")
    print("━" * 50)

    if tasks is None:
        if mode == "daily":
            priority_limit = 2
        elif mode == "weekly":
            priority_limit = 3
        else:
            priority_limit = 1
        tasks = [t for t in DEFAULT_TASKS if t["priority"] <= priority_limit]

    status = load_status()
    log = load_log()
    status_lock = threading.Lock()
    log_lock = threading.Lock()

    phases = build_phases(tasks)
    total_tasks = sum(len(p) for p in phases)
    results = {"success": 0, "failed": 0, "skipped": 0, "covered": 0}

    print(f"\n  実行タスク: {total_tasks}件 / {len(phases)}フェーズ\n")

    for phase_idx, phase_tasks in enumerate(phases):
        if len(phase_tasks) == 0:
            continue

        parallel_count = len(phase_tasks)
        label = "並列" if parallel_count > 1 else "単独"
        print(f"  ─── フェーズ{phase_idx} ({label} {parallel_count}件) ───")

        if parallel_count == 1:
            # 単独実行
            task = phase_tasks[0]
            executor = find_executor(task, status, status_lock)
            if executor is None:
                print(f"    ⏭️  {task['name']}: 全担当ビジー → スキップ")
                results["skipped"] += 1
            else:
                if executor != task["owner"]:
                    results["covered"] += 1
                ok = run_task(task, executor, status, log, status_lock, log_lock)
                results["success" if ok else "failed"] += 1
        else:
            # 並列実行: 各タスクに executor を事前確定してからスレッド起動
            dispatched = []
            for task in phase_tasks:
                executor = find_executor(task, status, status_lock)
                if executor is None:
                    print(f"    ⏭️  {task['name']}: 全担当ビジー → スキップ")
                    results["skipped"] += 1
                else:
                    if executor != task["owner"]:
                        results["covered"] += 1
                    dispatched.append((task, executor))

            with ThreadPoolExecutor(max_workers=len(dispatched)) as pool:
                futures = {
                    pool.submit(run_task, task, executor, status, log, status_lock, log_lock): task
                    for task, executor in dispatched
                }
                for future in as_completed(futures):
                    ok = future.result()
                    results["success" if ok else "failed"] += 1

    save_status(status)
    save_log(log)

    print(f"\n{'━'*50}")
    print(f"  完了 ✅{results['success']} ❌{results['failed']} ⏭️{results['skipped']} ⚡カバー{results['covered']}件")
    print("━" * 50)
    return results


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "daily"
    run(mode=mode)
