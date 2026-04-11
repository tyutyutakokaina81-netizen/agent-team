#!/usr/bin/env python3
"""
mac_pipeline.py — Lancers/CW 全自動パイプライン（Mac版）
セッション自動管理・自動応募・自動納品
"""
import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

AGENT_DIR = Path(__file__).parent
PIPELINE_DIR = AGENT_DIR / "projects/2026-04-08_月30万自動化/D_エクセル入力スクレイピング/pipeline"
SESSION_DIR = AGENT_DIR / ".sessions"
LOG_DIR = AGENT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)


def notify(title: str, message: str):
    script = f'display notification "{message}" with title "{title}" sound name "Glass"'
    subprocess.run(["osascript", "-e", script], capture_output=True)


def run_phase(phase: str):
    env = os.environ.copy()
    env["AUTO_APPLY"] = "1"
    env["AUTO_APPLY_THRESHOLD"] = "80"
    env["PYTHONPATH"] = str(PIPELINE_DIR)

    cmd = [sys.executable, str(PIPELINE_DIR / "run_pipeline.py"), phase]
    print(f"[{datetime.now().strftime('%H:%M')}] パイプライン実行: {phase}")

    result = subprocess.run(
        cmd,
        cwd=str(PIPELINE_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    # ログ保存
    log_entry = {
        "phase": phase,
        "time": datetime.now().isoformat(),
        "returncode": result.returncode,
        "stdout": result.stdout[-2000:],
    }
    log_file = LOG_DIR / "pipeline_history.json"
    history = []
    if log_file.exists():
        try:
            history = json.loads(log_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    history.append(log_entry)
    history = history[-100:]  # 最新100件のみ
    log_file.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

    return result.returncode == 0


def check_sessions():
    platforms = []
    for p in ["crowdworks", "lancers"]:
        if (SESSION_DIR / f"{p}_session.json").exists():
            platforms.append(p)
    return platforms


def main():
    phase = sys.argv[1] if len(sys.argv) > 1 else "search"

    platforms = check_sessions()
    if not platforms:
        print(f"[{datetime.now().strftime('%H:%M')}] セッション未設定 — スキップ")
        print("  Lancersに手動ログインして")
        print("  python projects/.../pipeline/00_session_setup.py を実行してください")
        return

    print(f"[{datetime.now().strftime('%H:%M')}] 対象: {', '.join(platforms)}")

    ok = run_phase(phase)

    if ok:
        notify("パイプライン完了", f"{phase} フェーズが正常終了しました")
    else:
        notify("パイプライン確認", f"{phase} フェーズを確認してください")


if __name__ == "__main__":
    main()
