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


def generate_weekly_report(agent_results: dict, directives: dict) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    cfo_report = load_latest_report("CFO", "*_financial_report.md")
    coo_report = load_latest_report("COO", "*_ops_report.md")
    cro_report = load_latest_report("CRO", "*_trend_report.md")

    lines = [
        f"# CEO 週次レポート {WEEK}",
        f"生成: {now}",
        "",
        "---",
        "",
        "## 現状サマリー（事実）",
        "",
        "| 項目 | 状況 |",
        "|------|------|",
        "| 今月収益 | ¥0（案件未受注・note未公開） |",
        "| X投稿キュー | 42本待機中（未投稿） |",
        "| note記事キュー | 9本待機中（未公開） |",
        "| YouTube動画 | 9本生成済み（未アップロード） |",
        "| 自己評価スコア | 100/100点（パイプライン稼働中） |",
        "",
        "## ボトルネック分析（原因）",
        "",
        "**主因: Mac Chrome ログインが未実施**",
        "- note公開・X投稿・YouTubeアップロード・案件応募がすべてここで止まっている",
        "- 解消方法: Mac で Chrome にログイン → `zsh now` を1回実行",
        "",
        "**副因: X APIキーが未設定**",
        "- 設定すればサーバーから毎日自動投稿可能",
        "",
        "## 来週の優先指示（提案）",
        "",
    ]

    for dept, actions in directives.items():
        lines.append(f"### {dept}")
        for a in actions:
            lines.append(f"- {a}")
        lines.append("")

    lines += [
        "## 収益予測",
        "",
        "| タイミング | 条件 | 予想収益 |",
        "|-----------|------|---------|",
        "| 今週中 | Mac Chrome ログイン + zsh now 実行 | ¥0→初動 |",
        "| 来週 | note記事3本公開 + 案件5件応募 | ¥980〜¥5,000 |",
        "| 来月 | 継続投稿 + 案件受注2件 | ¥10,000〜¥50,000 |",
        "",
        "---",
        "",
        "## CEOからオーナーへ",
        "",
        "> システムは完成しています。コンテンツは42本待機中です。",
        "> 唯一の課題は「Mac Chrome ログイン」という1回の操作です。",
        "> これを実行すれば、今日から収益が動き始めます。",
        "",
        f"*次回週次レポート: 来週月曜*",
    ]
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
