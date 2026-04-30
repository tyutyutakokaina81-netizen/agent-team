#!/usr/bin/env python3
"""
agent_dispatch.py — タスクディスパッチャー（分業・カバー制御）

役割:
1. タスクキューからタスクを取り出し、担当エージェントに割り振る
2. 担当が「ビジー」なら、カバー可能なエージェントに自動転送
3. 全タスクの実行ログを残す

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
import time
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
    "CRO": ["CDO", "CMO"],   # 調査が詰まったらCDO・CMOがカバー
    "CMO": ["CPO", "CDO"],   # コンテンツ制作はCPOがカバー
    "CPO": ["CMO", "CCO"],   # 商品制作はCMOがカバー
    "CSO": ["CGO", "COO"],   # 営業はCGOがカバー
    "CGO": ["CSO", "CMO"],   # 新規開拓はCSOがカバー
    "COO": ["CFO", "CDO"],   # 運用はCFOがカバー
    "CFO": ["COO", "CEO"],   # 会計はCOOがカバー
    "CBO": ["CEO", "CDO"],   # 事業開発はCEOがカバー
    "CDO": ["COO", "CRO"],   # 技術はCOOがカバー
    "CCO": ["CPO", "CMO"],   # コマースはCPOがカバー
    "CEO": ["CBO", "COO"],   # 統括はCBOがカバー
}

# ── エージェント → スクリプト マッピング ─────────────────────
AGENT_SCRIPTS = {
    "CRO": "agent_cro.py",
    "CMO": "auto_content_loop.py",
    "CPO": None,              # 手動制作中
    "CSO": "auto_job_apply.py",
    "CGO": None,              # 手動開拓中
    "COO": "agent_coo.py",
    "CFO": "agent_cfo.py",
    "CBO": "agent_cbo.py",
    "CDO": "auto_self_eval.py",
    "CCO": None,              # 手動出品中
    "CEO": "agent_ceo.py",
}

# ── タスク定義 ────────────────────────────────────────────────
DEFAULT_TASKS = [
    {"id": "T001", "name": "トレンド調査", "owner": "CRO", "priority": 1, "script": "agent_cro.py"},
    {"id": "T002", "name": "コンテンツ生成", "owner": "CMO", "priority": 1, "script": "auto_content_loop.py"},
    {"id": "T003", "name": "YouTube動画生成", "owner": "CMO", "priority": 2, "script": "auto_youtube_produce.py"},
    {"id": "T004", "name": "Shorts生成", "owner": "CMO", "priority": 2, "script": "auto_youtube_shorts.py"},
    {"id": "T005", "name": "案件サーチ", "owner": "CSO", "priority": 1, "script": "auto_job_hunt.py"},
    {"id": "T006", "name": "運用チェック", "owner": "COO", "priority": 2, "script": "agent_coo.py"},
    {"id": "T007", "name": "財務レポート", "owner": "CFO", "priority": 3, "script": "agent_cfo.py"},
    {"id": "T008", "name": "稟議生成", "owner": "CBO", "priority": 2, "script": "agent_cbo.py"},
    {"id": "T009", "name": "自己評価", "owner": "CDO", "priority": 3, "script": "auto_self_eval.py"},
    {"id": "T010", "name": "写真素材取得", "owner": "CMO", "priority": 3, "script": "auto_wikimedia_photos.py"},
    {"id": "T011", "name": "アフィリエイト処理", "owner": "CCO", "priority": 3, "script": "auto_affiliate.py"},
    {"id": "T012", "name": "横断変換", "owner": "CMO", "priority": 3, "script": "auto_repurpose.py"},
    {"id": "T013", "name": "週次統括", "owner": "CEO", "priority": 1, "script": "agent_ceo.py"},
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
def run_task(task: dict, executor: str, status: dict, log: dict) -> bool:
    script = task.get("script")
    if not script or not (REPO / script).exists():
        print(f"    [{executor}] スクリプトなし: {script} → スキップ")
        return False

    print(f"    [{executor}] 実行: {task['name']} ({script})")
    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, str(REPO / script)],
            capture_output=True, text=True, timeout=90
        )
        elapsed = round(time.time() - start, 1)
        success = result.returncode == 0

        status[executor]["completed"] += 1
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

        icon = "✅" if success else "❌"
        cover_note = f"（{task['owner']}の代理）" if executor != task["owner"] else ""
        print(f"    {icon} {task['name']} {cover_note} {elapsed}秒")
        return success

    except subprocess.TimeoutExpired:
        print(f"    ⏱️ タイムアウト: {task['name']}")
        status[executor]["failed"] += 1
        return False
    except Exception as e:
        print(f"    ❌ エラー: {e}")
        status[executor]["failed"] += 1
        return False


def find_executor(task: dict, status: dict) -> str | None:
    """タスクを実行できるエージェントを探す（ビジーならカバーへ）"""
    owner = task["owner"]

    # 主担当が利用可能なら主担当
    if status.get(owner, {}).get("status") == "available":
        return owner

    # カバールールに従って代替を探す
    for backup in COVERAGE.get(owner, []):
        if status.get(backup, {}).get("status") == "available":
            print(f"    ⚡ {owner}がビジー → {backup}がカバー")
            return backup

    return None  # 全員ビジー


# ── メイン実行 ────────────────────────────────────────────────
def run(tasks: list = None, mode: str = "daily"):
    print("━" * 50)
    print("  DISPATCH — タスク分配・カバー制御")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')} [{mode}モード]")
    print("━" * 50)

    if tasks is None:
        # モードで実行タスクを絞る
        if mode == "daily":
            priority_limit = 2   # 優先度1〜2のみ
        elif mode == "weekly":
            priority_limit = 3   # 全タスク
        else:
            priority_limit = 1
        tasks = [t for t in DEFAULT_TASKS if t["priority"] <= priority_limit]

    tasks_sorted = sorted(tasks, key=lambda t: t["priority"])
    status = load_status()
    log = load_log()

    results = {"success": 0, "failed": 0, "skipped": 0, "covered": 0}

    print(f"\n  実行タスク: {len(tasks_sorted)}件\n")
    for task in tasks_sorted:
        executor = find_executor(task, status)
        if executor is None:
            print(f"    ⏭️  {task['name']}: 全担当ビジー → スキップ")
            results["skipped"] += 1
            continue

        if executor != task["owner"]:
            results["covered"] += 1

        ok = run_task(task, executor, status, log)
        if ok:
            results["success"] += 1
        else:
            results["failed"] += 1

    save_status(status)
    save_log(log)

    print(f"\n{'━'*50}")
    print(f"  完了 ✅{results['success']} ❌{results['failed']} ⏭️{results['skipped']} ⚡カバー{results['covered']}件")
    print("━" * 50)
    return results


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "daily"
    run(mode=mode)
