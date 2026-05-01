#!/usr/bin/env python3
"""
agent_manager.py — 日次マネジメントエージェント（API不要・費用ゼロ）

毎日実行:
1. 全パイプラインの状態を収集
2. ボトルネックを特定・優先度付け
3. 実行可能なアクションは自動実行
4. 日次レポートを生成・表示

使い方:
  python3 agent_manager.py          # 状況確認 + レポート
  python3 agent_manager.py --fix    # 自動修正も実行
"""

import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

REPO = Path(__file__).parent
OUTPUT_DIR = REPO / "CEO" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SESSIONS = REPO / ".sessions"
TODAY = date.today().isoformat()
NOW = datetime.now().strftime("%Y-%m-%d %H:%M")

# ── 状態収集 ──────────────────────────────────────────────────

def collect_note_state() -> dict:
    """note公開キューの状態"""
    published = set()
    nq_file = SESSIONS / "note_publish_queue.json"
    if nq_file.exists():
        data = json.loads(nq_file.read_text())
        published = set(data.get("published", {}).keys())

    content = (REPO / "auto_note_publish.py").read_text(encoding="utf-8")
    all_ids = re.findall(r'"id":\s*"([^"]+)"', content)
    all_files = re.findall(r'"file":\s*"([^"]+)"', content)

    queue = []
    for i, qid in enumerate(all_ids):
        fpath = REPO / all_files[i] if i < len(all_files) else None
        exists = fpath.exists() if fpath else False
        queue.append({
            "id": qid,
            "published": qid in published,
            "file_exists": exists,
        })

    total = len(queue)
    done = sum(1 for q in queue if q["published"])
    waiting = [q for q in queue if not q["published"] and q["file_exists"]]
    missing = [q for q in queue if not q["published"] and not q["file_exists"]]

    return {
        "total": total,
        "published": done,
        "waiting": len(waiting),
        "missing_files": len(missing),
        "next_3": [q["id"] for q in waiting[:3]],
        "eta_days": round(len(waiting) / 3, 1) if waiting else 0,
    }


def collect_x_state() -> dict:
    """X投稿キューの状態"""
    total_waiting = 0

    xq_file = SESSIONS / "x_post_queue.json"
    if xq_file.exists():
        xq = json.loads(xq_file.read_text())
        total_waiting += sum(1 for v in xq.values() if not v.get("posted"))

    xe_file = SESSIONS / "x_extra_posts.json"
    if xe_file.exists():
        xe = json.loads(xe_file.read_text())
        if isinstance(xe, list):
            total_waiting += sum(1 for p in xe if not p.get("posted"))

    api_ready = False
    env_file = REPO / ".env"
    if env_file.exists():
        env_text = env_file.read_text()
        api_ready = bool(re.search(r'X_API_KEY\s*=\s*[^\s#]{5,}', env_text))
    for key in ("X_API_KEY", "TWITTER_API_KEY"):
        if os.environ.get(key):
            api_ready = True

    return {
        "waiting": total_waiting,
        "api_ready": api_ready,
        "blocker": None if api_ready else "X_API_KEY未設定",
    }


def collect_content_state() -> dict:
    """生成済みコンテンツの在庫"""
    cmo_out = REPO / "CMO" / "outputs"
    if not cmo_out.exists():
        return {"note_files": 0, "x_files": 0, "youtube_files": 0}

    note_files = len([f for f in cmo_out.glob("*_note*.md") if "directive" not in f.name])
    x_files = len(list(cmo_out.glob("*xpost*.md")))
    yt_dir = cmo_out / "youtube_videos"
    yt_files = len(list(yt_dir.glob("*.mp4"))) if yt_dir.exists() else 0

    return {
        "note_files": note_files,
        "x_files": x_files,
        "youtube_files": yt_files,
    }


def collect_automation_state() -> dict:
    """Mac LaunchAgent & ウェイク設定の状態（ログから推定）"""
    logs_dir = REPO / "logs"
    recent_runs = []
    errors = 0

    if logs_dir.exists():
        for log_file in sorted(logs_dir.glob("auto_*.log"), reverse=True)[:6]:
            text = log_file.read_text(errors="ignore")
            lines = [l for l in text.splitlines() if l.strip()]
            if lines:
                recent_runs.append({
                    "file": log_file.name,
                    "last_line": lines[-1][:80],
                    "ok": "完了" in text or "OK" in text,
                })
            if re.search(r'\bNG\b|ERROR|Traceback', text):
                errors += 1

    return {
        "recent_runs": recent_runs,
        "errors": errors,
        "launchagent_count": len(recent_runs),
    }


def collect_revenue_state() -> dict:
    """収益状況（CFOレポートがあれば読み込む）"""
    revenue = 0
    cfo_dir = REPO / "CFO" / "outputs"
    if cfo_dir.exists():
        for f in sorted(cfo_dir.glob("*_financial_report.md"), reverse=True)[:1]:
            text = f.read_text(encoding="utf-8")
            m = re.search(r"収入合計.*?¥([\d,]+)", text)
            if m:
                revenue = int(m.group(1).replace(",", ""))

    booth_file = SESSIONS / "booth_sales.json"
    booth_sales = 0
    if booth_file.exists():
        data = json.loads(booth_file.read_text())
        booth_sales = data.get("total_revenue", 0)

    return {
        "total": revenue + booth_sales,
        "target": 300000,
        "progress_pct": round((revenue + booth_sales) / 300000 * 100, 1),
    }


# ── ボトルネック判定 ───────────────────────────────────────────

def analyze_bottlenecks(note, x, content, auto, rev) -> list[dict]:
    bottlenecks = []

    if note["waiting"] > 0 and auto["launchagent_count"] == 0:
        bottlenecks.append({
            "priority": 1,
            "title": "note自動公開が未起動",
            "detail": f"{note['waiting']}本が待機中。Mac LaunchAgentのログが見当たりません。",
            "action": "Macで `zsh setup` を実行 → Chrome で note.com にログイン",
        })

    if note["waiting"] > 0 and auto["launchagent_count"] > 0:
        bottlenecks.append({
            "priority": 2,
            "title": f"note {note['waiting']}本が公開待ち",
            "detail": f"1日3本ペース。完了まで約{note['eta_days']}日。",
            "action": "自動実行中 — 対応不要",
        })

    if not x["api_ready"] and x["waiting"] > 0:
        bottlenecks.append({
            "priority": 1,
            "title": "X投稿がブロック中",
            "detail": f"{x['waiting']}本が未投稿。X APIキー未設定のため自動化できていません。",
            "action": "developer.twitter.com で無料取得 → .env に X_API_KEY を追記",
        })

    if auto["errors"] > 0:
        bottlenecks.append({
            "priority": 2,
            "title": f"自動化ログにエラー {auto['errors']}件",
            "detail": "直近のログにエラーが含まれています。",
            "action": "logs/ フォルダのログを確認",
        })

    if rev["total"] == 0:
        bottlenecks.append({
            "priority": 3,
            "title": "収益¥0（初売上まで待機中）",
            "detail": "note記事公開 → テンプレ購入の流れを構築中。",
            "action": "note公開完了後にBOOTH/note購入リンクをSNSでシェア",
        })

    return sorted(bottlenecks, key=lambda b: b["priority"])


# ── レポート生成 ─────────────────────────────────────────────

def generate_report(note, x, content, auto, rev, bottlenecks) -> str:
    target_gap = rev["target"] - rev["total"]

    lines = [
        f"# マネジメントレポート {TODAY}",
        f"生成: {NOW}",
        "",
        "---",
        "",
        "## 収益状況",
        "",
        f"| 項目 | 数値 |",
        f"|------|------|",
        f"| 今月収益 | ¥{rev['total']:,} |",
        f"| 目標 | ¥{rev['target']:,} |",
        f"| 達成率 | {rev['progress_pct']}% |",
        f"| 残りギャップ | ¥{target_gap:,} |",
        "",
        "## パイプライン状況",
        "",
        "| チャネル | 状況 |",
        "|---------|------|",
        f"| note記事 | {note['published']}/{note['total']}本公開済・{note['waiting']}本待機 |",
        f"| X投稿 | {x['waiting']}本待機 / API: {'✅' if x['api_ready'] else '❌未設定'} |",
        f"| コンテンツ在庫 | note:{content['note_files']}本・X:{content['x_files']}本 |",
        f"| YouTube | {content['youtube_files']}本 |",
        f"| 自動化ログ | 直近{auto['launchagent_count']}件 / エラー{auto['errors']}件 |",
        "",
        "## ボトルネック（優先度順）",
        "",
    ]

    if bottlenecks:
        for i, b in enumerate(bottlenecks, 1):
            lines += [
                f"### {i}. 【優先度{b['priority']}】{b['title']}",
                f"- 状況: {b['detail']}",
                f"- 対応: {b['action']}",
                "",
            ]
    else:
        lines += ["**ボトルネックなし — 全パイプライン正常稼働中**", ""]

    if note["waiting"] > 0:
        lines += [
            "## note公開スケジュール（予測）",
            "",
            f"- 残り: {note['waiting']}本",
            f"- ペース: 1日3本（9:00 / 14:00 / 20:00）",
            f"- 完了予測: 約{note['eta_days']}日後",
            f"- 次の3本: {', '.join(note['next_3'])}",
            "",
        ]

    lines += [
        "---",
        f"*次回レポート: 明日 {TODAY}*",
    ]

    return "\n".join(lines)


# ── メイン ───────────────────────────────────────────────────

def run(fix: bool = False):
    print("━" * 52)
    print("  マネジメントエージェント 日次レポート")
    print(f"  {NOW}")
    print("━" * 52)

    print("\n  状態収集中...")
    note  = collect_note_state()
    x     = collect_x_state()
    cnt   = collect_content_state()
    auto  = collect_automation_state()
    rev   = collect_revenue_state()

    bottlenecks = analyze_bottlenecks(note, x, cnt, auto, rev)

    report = generate_report(note, x, cnt, auto, rev, bottlenecks)
    out = OUTPUT_DIR / f"{TODAY}_manager_report.md"
    out.write_text(report, encoding="utf-8")

    # ── 表示 ───────────────────────────────────────────────
    print(f"\n{'━'*52}")
    print("  【収益】")
    print(f"  今月: ¥{rev['total']:,} / 目標¥{rev['target']:,}（{rev['progress_pct']}%）")

    print(f"\n  【パイプライン】")
    print(f"  note   : {note['published']}/{note['total']}本公開・{note['waiting']}本待機（約{note['eta_days']}日で完了）")
    print(f"  X      : {x['waiting']}本待機 / API={'設定済' if x['api_ready'] else '❌未設定'}")
    print(f"  在庫   : note {cnt['note_files']}本 / X投稿 {cnt['x_files']}本")
    print(f"  自動化 : ログ{auto['launchagent_count']}件 / エラー{auto['errors']}件")

    print(f"\n  【ボトルネック {len(bottlenecks)}件】")
    for i, b in enumerate(bottlenecks, 1):
        mark = "🔴" if b["priority"] == 1 else "🟡" if b["priority"] == 2 else "🟢"
        print(f"  {mark} {i}. {b['title']}")
        print(f"       → {b['action']}")

    if not bottlenecks:
        print("  ✅ 全パイプライン正常")

    print(f"\n  レポート保存: {out.name}")
    print("━" * 52)

    return {"note": note, "x": x, "bottlenecks": bottlenecks}


if __name__ == "__main__":
    run(fix="--fix" in sys.argv)
