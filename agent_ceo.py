#!/usr/bin/env python3
"""
agent_ceo.py — CEO（統括マネジャー）自動実行

週次実行（月曜20時推奨）:
1. CRO/COO/CFOのレポートを集約
2. ボトルネックを特定
3. 来週の優先指示を生成
4. 週次レポートをCEO/outputs/に出力・オーナーに提示
"""

import json
import subprocess
import sys
from datetime import datetime, date
from pathlib import Path

REPO = Path(__file__).parent
OUTPUT_DIR = REPO / "CEO" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TODAY = date.today().isoformat()
WEEK = datetime.now().strftime("%Y-W%V")

AUTO_APPROVE_THRESHOLD = 100  # 100点以上の稟議は自動承認→即実行指示


def run_agent(script: str, label: str) -> dict:
    """サブエージェントを実行して結果を取得"""
    print(f"\n  [{label}] 実行中...")
    try:
        result = subprocess.run(
            [sys.executable, REPO / script],
            capture_output=True, text=True, timeout=60
        )
        # 標準出力に結果を表示
        if result.stdout:
            for line in result.stdout.strip().split("\n")[-5:]:  # 最後の5行だけ表示
                print(f"    {line}")
        return {"status": "OK", "script": script}
    except subprocess.TimeoutExpired:
        print(f"    タイムアウト（60秒）")
        return {"status": "timeout", "script": script}
    except Exception as e:
        print(f"    エラー: {e}")
        return {"status": "error", "script": script}


def load_latest_report(folder: str, pattern: str) -> str:
    """最新レポートを読み込む"""
    dir_path = REPO / folder / "outputs"
    files = sorted(dir_path.glob(pattern), reverse=True)
    if files:
        return files[0].read_text(encoding="utf-8")
    return ""


def auto_approve_ringi() -> list[dict]:
    """100点以上の稟議を自動承認し、実行指示を各部署に発行する"""
    ringi_dir = REPO / "CBO" / "outputs"
    summary_files = sorted(ringi_dir.glob("*_ringi_summary.json"), reverse=True)
    if not summary_files:
        return []

    summary = json.loads(summary_files[0].read_text())
    proposals = summary.get("top_proposals", [])
    approved = []

    approval_log = REPO / "CBO" / "approvals.json"
    log = json.loads(approval_log.read_text()) if approval_log.exists() else {"approved": [], "pending": [], "rejected": []}

    for p in proposals:
        already = any(a["id"] == p["id"] for a in log["approved"])
        if already:
            continue

        if p["score"] >= AUTO_APPROVE_THRESHOLD:
            # 自動承認
            p["approved_at"] = TODAY
            p["approved_by"] = "CEO（自動承認: スコア{}点≥{}点）".format(p["score"], AUTO_APPROVE_THRESHOLD)
            log["approved"].append(p)
            approved.append(p)
            print(f"  ✅ 自動承認: [{p['score']}点] {p['title']}")

            # 実行指示ファイルを各部署に発行
            _issue_directive(p)
        else:
            if not any(a["id"] == p["id"] for a in log["pending"]):
                log["pending"].append({**p, "reason": f"スコア{p['score']}点 < {AUTO_APPROVE_THRESHOLD}点（手動承認待ち）"})
            print(f"  ⏳ 保留: [{p['score']}点] {p['title']}（手動承認が必要）")

    approval_log.write_text(json.dumps(log, ensure_ascii=False, indent=2))

    # 稟議サマリーのステータスを現在の承認状況に基づいて更新
    all_approved_ids = {a["id"] for a in log["approved"]}
    all_proposal_ids = {p["id"] for p in proposals}
    if all_proposal_ids and all_proposal_ids <= all_approved_ids:
        summary["status"] = "全件承認済み"
    elif log["approved"]:
        summary["status"] = f"{len(log['approved'])}件承認済み・{len(log['pending'])}件保留"
    summary_files[0].write_text(json.dumps(summary, ensure_ascii=False, indent=2))

    return approved


def _issue_directive(proposal: dict):
    """承認された稟議の実行指示を担当部署フォルダに配置"""
    directives = {
        "CMO": f"【実行指示】{proposal['title']} のコンテンツを作成してください（CEO自動承認済み・{TODAY}）",
        "CPO": f"【実行指示】{proposal['title']} を商品化・出品ページを作成してください（CEO自動承認済み・{TODAY}）",
        "CSO": f"【実行指示】{proposal['title']} の営業・応募を開始してください（CEO自動承認済み・{TODAY}）",
    }
    for dept, msg in directives.items():
        dept_dir = REPO / dept / "outputs"
        dept_dir.mkdir(parents=True, exist_ok=True)
        out = dept_dir / f"{TODAY}_directive_{proposal['id']}.md"
        out.write_text(f"# CEO指示書\n\n{msg}\n\n## 事業概要\n- タイトル: {proposal['title']}\n- 単価: ¥{proposal['price']:,}\n- プラットフォーム: {proposal['platform']}\n- 優先度: 第{proposal.get('rank',1)}位（スコア{proposal['score']}点）\n", encoding="utf-8")


def generate_directives(cro_data: str, coo_data: str, cfo_data: str) -> dict:
    """各部署への来週の優先指示を生成"""
    directives = {
        "CSO（営業）": [
            "CrowdWorks・Lancersにデータ入力・ライティング案件を週5件応募",
            "応募文テンプレートを使って送付スピードを上げる",
        ],
        "CMO（コンテンツ）": [
            "note記事を週3本公開（Macで zsh now を実行）",
            "X投稿を毎日1本投稿（X APIキー設定後は自動化）",
            "YouTube Shortsを週2本アップロード",
        ],
        "COO（運用）": [
            "Macで zsh setup を実行してLaunchAgentを有効化",
            "Chrome で note/X/YouTube にログインして自動化を開通",
        ],
        "CFO（会計）": [
            "note テンプレ販売（¥980）の売上を週次確認",
            "初受注時に請求書テンプレートを準備",
        ],
        "CDO（技術）": [
            "YouTube API対応でサーバーから自動アップロードを実装",
            "X APIキー設定を案内・動作確認",
        ],
    }
    return directives


def _read_live_metrics() -> dict:
    """セッションファイル・各部署レポートから実データを収集する"""
    sessions = REPO / ".sessions"
    metrics = {
        "x_queue": 0, "note_queue": 0,
        "yt_shorts": 0, "yt_videos": 0,
        "revenue": 0, "cost": 3000,
        "eval_score": "N/A",
        "pipeline_jobs": 0,
        "log_errors": 0,
        "x_api_ready": False,
    }

    # X キュー
    xq = sessions / "x_post_queue.json"
    xe = sessions / "x_extra_posts.json"
    if xq.exists():
        q = json.loads(xq.read_text())
        metrics["x_queue"] += sum(1 for v in q.values() if not v.get("posted"))
    if xe.exists():
        extras = json.loads(xe.read_text())
        if isinstance(extras, list):
            metrics["x_queue"] += sum(1 for p in extras if not p.get("posted"))

    # note キュー（CMO/outputs の未公開 note 記事数）
    note_state: set = set()
    nq = sessions / "note_publish_queue.json"
    if nq.exists():
        try:
            note_state = set(json.loads(nq.read_text()).get("published", {}).keys())
        except Exception:
            pass
    cmo_out = REPO / "CMO" / "outputs"
    if cmo_out.exists():
        note_files = [f for f in cmo_out.glob("*_note*.md") if "directive" not in f.name]
        metrics["note_queue"] = sum(1 for f in note_files if f.stem not in note_state)

    # YouTube
    yt_dir = REPO / "CMO" / "outputs" / "youtube_videos"
    if yt_dir.exists():
        metrics["yt_videos"] = len(list(yt_dir.glob("*.mp4")))
        shorts_dir = yt_dir / "shorts"
        if shorts_dir.exists():
            metrics["yt_shorts"] = len(list(shorts_dir.glob("*.mp4")))

    # 自己評価スコア
    eval_log = sessions / "self_eval_log.json"
    if eval_log.exists():
        history = json.loads(eval_log.read_text()).get("history", [])
        if history:
            metrics["eval_score"] = history[-1].get("total", "N/A")

    # 財務 (CFO レポートから収入を取得)
    cfo_dir = REPO / "CFO" / "outputs"
    cfo_files = sorted(cfo_dir.glob("*_financial_report.md"), reverse=True) if cfo_dir.exists() else []
    if cfo_files:
        content = cfo_files[0].read_text(encoding="utf-8")
        for line in content.splitlines():
            if "収入合計" in line:
                import re as _re
                m = _re.search(r"¥([\d,]+)", line)
                if m:
                    metrics["revenue"] = int(m.group(1).replace(",", ""))
                break

    # パイプライン案件数
    pf = sessions / "job_pipeline.json"
    if pf.exists():
        metrics["pipeline_jobs"] = len(json.loads(pf.read_text()).get("jobs", []))

    # ログエラー数
    logs_dir = REPO / "logs"
    if logs_dir.exists():
        recent = sorted(logs_dir.glob("cron_*.log"), reverse=True)[:3]
        import re as _re
        for lf in recent:
            for line in lf.read_text(errors="ignore").splitlines():
                if _re.search(r"\bERROR\b", line) and "NO ERROR" not in line:
                    metrics["log_errors"] += 1
                elif "Traceback" in line or line.rstrip().endswith("  NG"):
                    metrics["log_errors"] += 1

    # X API 設定確認
    env_file = REPO / ".env"
    if env_file.exists():
        metrics["x_api_ready"] = "TWITTER_API_KEY" in env_file.read_text()
    for key in ("TWITTER_API_KEY", "TWITTER_BEARER_TOKEN"):
        import os
        if os.environ.get(key):
            metrics["x_api_ready"] = True
            break

    return metrics


def generate_weekly_report(agent_results: dict, directives: dict) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    m = _read_live_metrics()

    revenue_str = f"¥{m['revenue']:,}" if m["revenue"] > 0 else "¥0（案件未受注）"
    x_api_str = "✅ 設定済み" if m["x_api_ready"] else "❌ 未設定"
    error_str = f"{m['log_errors']}件" if m["log_errors"] > 0 else "なし"

    lines = [
        f"# CEO 週次レポート {WEEK}",
        f"生成: {now}",
        "",
        "---",
        "",
        "## 現状サマリー（実測値）",
        "",
        "| 項目 | 状況 |",
        "|------|------|",
        f"| 今月収益 | {revenue_str} |",
        f"| X投稿キュー | {m['x_queue']}本待機 |",
        f"| note記事キュー | {m['note_queue']}本待機 |",
        f"| YouTube長尺 | {m['yt_videos']}本生成済み |",
        f"| YouTube Shorts | {m['yt_shorts']}本生成済み |",
        f"| 自己評価スコア | {m['eval_score']}/100点 |",
        f"| 案件パイプライン | {m['pipeline_jobs']}件 |",
        f"| X API | {x_api_str} |",
        f"| ログエラー | {error_str} |",
        "",
        "## ボトルネック分析（原因）",
        "",
    ]

    bottlenecks = []
    if not m["x_api_ready"]:
        bottlenecks.append(("X APIキー未設定", "developer.twitter.com で無料取得 → `bash setup_x_api.sh`"))
    if m["note_queue"] > 0:
        bottlenecks.append(("note未公開", f"{m['note_queue']}本が待機中 → Mac Chrome ログイン後 `zsh now`"))
    if m["x_queue"] > 0 and not m["x_api_ready"]:
        bottlenecks.append(("X未投稿", f"{m['x_queue']}本が待機中 → X API設定後に自動解消"))
    if m["yt_videos"] > 0:
        bottlenecks.append(("YouTube未アップロード", f"{m['yt_videos']}本が待機中 → YouTube API設定（次フェーズ）"))
    if m["log_errors"] > 0:
        bottlenecks.append(("ログエラーあり", f"{m['log_errors']}件 → CDOが調査中"))

    if bottlenecks:
        for title, detail in bottlenecks:
            lines += [f"**{title}**", f"- {detail}", ""]
    else:
        lines += ["**ボトルネックなし — 全パイプライン稼働中**", ""]

    lines += ["## 来週の優先指示", ""]
    for dept, actions in directives.items():
        lines.append(f"### {dept}")
        for a in actions:
            lines.append(f"- {a}")
        lines.append("")

    lines += [
        "---",
        "",
        "## CEOからオーナーへ",
        "",
    ]
    if m["revenue"] == 0:
        lines += [
            f"> コンテンツ {m['x_queue'] + m['note_queue']}本が配信待ちです。",
            "> 最優先アクション: X APIキー設定（無料・5分）→ サーバーから毎日自動投稿開始。",
            "> 次に: Mac Chrome ログイン → `zsh now` でnote公開・案件応募が走ります。",
        ]
    else:
        lines += [
            f"> 今月収益: ¥{m['revenue']:,}。パイプライン継続稼働中。",
        ]

    lines += ["", f"*次回週次レポート: 来週月曜*"]
    return "\n".join(lines)


def run():
    print("━" * 50)
    print("  CEO — 週次統括レポート")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("━" * 50)

    # 各エージェントを順番に実行
    results = {}
    results["CRO"] = run_agent("agent_cro.py", "CRO トレンド調査")
    results["COO"] = run_agent("agent_coo.py", "COO 運用チェック")
    results["CFO"] = run_agent("agent_cfo.py", "CFO 財務確認")

    # 稟議自動承認（100点以上）
    print(f"\n  稟議自動承認チェック（閾値: {AUTO_APPROVE_THRESHOLD}点）...")
    approved = auto_approve_ringi()

    print("\n  来週の優先指示を生成中...")
    directives = generate_directives("", "", "")

    report = generate_weekly_report(results, directives)
    out = OUTPUT_DIR / f"{TODAY}_weekly_report.md"
    out.write_text(report, encoding="utf-8")

    print(f"\n{'━'*50}")
    print("  【CEO 週次判断】")
    print("━" * 50)
    print(f"\n  自動承認済み稟議: {len(approved)}件")
    for a in approved:
        print(f"    ✅ {a['title']} → CMO/CPO/CSOに指示発行済み")

    print("\n  最優先アクション:")
    print("  1. Mac Chrome ログイン → zsh now（今週中）")
    print("  2. X APIキー設定（developer.twitter.com）")
    print("  3. CRO トレンドに基づきCSO が案件応募開始")
    print(f"\n  週次レポート: {out.name}")
    print("━" * 50)

    return directives


if __name__ == "__main__":
    run()
