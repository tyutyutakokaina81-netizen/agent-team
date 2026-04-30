#!/usr/bin/env python3
"""
agent_coo.py — COO（運用・総務）自動実行

毎日実行:
1. システム健全性チェック（ログ・キュー・スクリプト）
2. 案件パイプライン状況確認
3. 運用レポートをCOO/outputs/に出力
4. 異常があればCDO/CEOへの警告を生成
"""

import json
import subprocess
import sys
from datetime import datetime, date, timedelta
from pathlib import Path

REPO = Path(__file__).parent
SESSIONS = REPO / ".sessions"
LOGS_DIR = REPO / "logs"
OUTPUT_DIR = REPO / "COO" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TODAY = date.today().isoformat()

PIPELINE_FILE = SESSIONS / "job_pipeline.json"


def load_pipeline() -> dict:
    if PIPELINE_FILE.exists():
        return json.loads(PIPELINE_FILE.read_text())
    return {"jobs": []}


def save_pipeline(data: dict):
    SESSIONS.mkdir(exist_ok=True)
    PIPELINE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


# ── システム健全性チェック ───────────────────────────────────
def check_queues() -> dict:
    """キュー残数チェック"""
    results = {}

    # X投稿キュー
    x_queue = SESSIONS / "x_post_queue.json"
    x_extra = SESSIONS / "x_extra_posts.json"
    x_count = 0
    if x_queue.exists():
        q = json.loads(x_queue.read_text())
        x_count = sum(1 for v in q.values() if not v.get("posted"))
    if x_extra.exists():
        extras = json.loads(x_extra.read_text())
        x_count += sum(1 for p in extras if not p.get("posted"))
    results["x_queue"] = {"count": x_count, "status": "OK" if x_count >= 10 else "警告: 補充必要"}

    # note記事キュー
    note_queue = SESSIONS / "note_publish_queue.json"
    note_count = 0
    if note_queue.exists():
        try:
            state = json.loads(note_queue.read_text())
            published = state.get("published", {})
            from auto_note_publish import ARTICLE_QUEUE
            note_count = sum(1 for a in ARTICLE_QUEUE if a["id"] not in published)
        except Exception:
            note_count = -1
    results["note_queue"] = {"count": note_count, "status": "OK" if note_count >= 5 else "警告: 補充必要"}

    # YouTube動画
    shorts_dir = REPO / "CMO" / "outputs" / "youtube_videos" / "shorts"
    video_dir = REPO / "CMO" / "outputs" / "youtube_videos"
    shorts = len(list(shorts_dir.glob("*.mp4"))) if shorts_dir.exists() else 0
    videos = len(list(video_dir.glob("*.mp4"))) if video_dir.exists() else 0
    results["youtube"] = {"shorts": shorts, "videos": videos, "status": "OK" if shorts >= 3 else "警告"}

    return results


def check_logs() -> dict:
    """直近ログのエラー数チェック"""
    if not LOGS_DIR.exists():
        return {"error_count": 0, "status": "ログなし（正常）"}

    recent = sorted(LOGS_DIR.glob("cron_*.log"), reverse=True)[:3]
    error_count = 0
    for log in recent:
        content = log.read_text(errors="ignore")
        error_count += content.count("ERROR") + content.count("Traceback") + content.count("  NG")

    return {
        "error_count": error_count,
        "log_files": len(recent),
        "status": "OK" if error_count == 0 else f"警告: エラー{error_count}件",
    }


def check_scripts() -> dict:
    """主要スクリプトの存在確認"""
    required = [
        "auto_content_loop.py",
        "auto_youtube_shorts.py",
        "auto_youtube_produce.py",
        "auto_x_api_post.py",
        "auto_self_eval.py",
        "cron_run.sh",
        "now",
    ]
    missing = [s for s in required if not (REPO / s).exists()]
    return {
        "total": len(required),
        "missing": missing,
        "status": "OK" if not missing else f"警告: {missing} が存在しない",
    }


# ── 案件パイプライン管理 ─────────────────────────────────────
def update_pipeline() -> dict:
    """案件パイプラインの状況を更新・集計"""
    pipeline = load_pipeline()
    jobs = pipeline.get("jobs", [])

    counts = {
        "応募済み": 0, "返信待ち": 0, "商談中": 0,
        "進行中": 0, "納品済み": 0, "入金確認": 0,
    }
    for job in jobs:
        stage = job.get("stage", "応募済み")
        if stage in counts:
            counts[stage] += 1

    return {"pipeline": counts, "total": len(jobs)}


# ── 警告・アクション生成 ─────────────────────────────────────
def generate_alerts(queues: dict, logs: dict, pipeline: dict) -> list[str]:
    alerts = []

    if queues["x_queue"]["count"] < 10:
        alerts.append(f"⚠️  X投稿残{queues['x_queue']['count']}本 → CMOに補充依頼")
    if queues["note_queue"]["count"] < 5:
        alerts.append(f"⚠️  note記事残{queues['note_queue']['count']}本 → CMOに補充依頼")
    if logs["error_count"] > 0:
        alerts.append(f"⚠️  ログエラー{logs['error_count']}件 → CDOに調査依頼")
    if pipeline["pipeline"].get("返信待ち", 0) > 5:
        alerts.append(f"⚠️  返信待ち{pipeline['pipeline']['返信待ち']}件 → CSOがフォローアップ")

    return alerts


# ── レポート生成 ─────────────────────────────────────────────
def generate_report(queues: dict, logs: dict, scripts: dict, pipeline: dict, alerts: list) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# COO 運用レポート {TODAY}",
        f"生成: {now}",
        "",
        "---",
        "",
        "## コンテンツキュー状況",
        f"- X投稿: **{queues['x_queue']['count']}本** ({queues['x_queue']['status']})",
        f"- note記事: **{queues['note_queue']['count']}本** ({queues['note_queue']['status']})",
        f"- YouTube Shorts: **{queues['youtube']['shorts']}本** / 長尺: **{queues['youtube']['videos']}本**",
        "",
        "## システム状態",
        f"- ログエラー: **{logs['error_count']}件** ({logs['status']})",
        f"- スクリプト: **{scripts['total'] - len(scripts['missing'])} / {scripts['total']}** 正常",
        "",
        "## 案件パイプライン",
        "| ステージ | 件数 |",
        "|---------|------|",
    ]
    for stage, count in pipeline["pipeline"].items():
        lines.append(f"| {stage} | {count}件 |")
    lines.append(f"| **合計** | **{pipeline['total']}件** |")

    lines += ["", "## アラート・要対応事項", ""]
    if alerts:
        for a in alerts:
            lines.append(f"- {a}")
    else:
        lines.append("- なし（全項目正常）")

    lines += ["", "---", f"*次回チェック: 明日 {TODAY} 09:00*"]
    return "\n".join(lines)


def run() -> dict:
    print("━" * 45)
    print("  COO — 運用・システムチェック")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("━" * 45)

    print("\n  [1] キュー確認...")
    queues = check_queues()
    print(f"  X: {queues['x_queue']['count']}本 / note: {queues['note_queue']['count']}本")

    print("\n  [2] ログ確認...")
    logs = check_logs()
    print(f"  エラー数: {logs['error_count']}件")

    print("\n  [3] スクリプト確認...")
    scripts = check_scripts()
    print(f"  正常: {scripts['total'] - len(scripts['missing'])}/{scripts['total']}")

    print("\n  [4] パイプライン確認...")
    pipeline = update_pipeline()
    print(f"  案件総数: {pipeline['total']}件")

    alerts = generate_alerts(queues, logs, pipeline)
    if alerts:
        print(f"\n  ⚠️  アラート {len(alerts)}件:")
        for a in alerts:
            print(f"  {a}")
    else:
        print("\n  ✅ 全項目正常")

    report = generate_report(queues, logs, scripts, pipeline, alerts)
    out = OUTPUT_DIR / f"{TODAY}_ops_report.md"
    out.write_text(report, encoding="utf-8")
    print(f"\n  レポート保存: {out.name}")
    print("━" * 45)

    return {"queues": queues, "logs": logs, "alerts": alerts, "pipeline": pipeline}


if __name__ == "__main__":
    run()
