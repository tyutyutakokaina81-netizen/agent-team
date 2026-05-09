"""
03_apply.py — 応募文生成（テンプレートベース）
案件情報をもとに採用率の高い応募文を生成する。
送信は人手確認後（規約グレーのため半自動運用）。

注: 有料 API は使用しない。完全テンプレートで動作する。
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
# リポジトリルート上の scripts/notify.sh を呼び出すための解決
REPO_ROOT = Path(__file__).resolve().parents[4]
NOTIFY_SCRIPT = REPO_ROOT / "scripts" / "notify.sh"


def _notify(status: str, message: str) -> None:
    """Mac 通知を出してログに残す（notify.sh が無ければ静かにスキップ）"""
    if not NOTIFY_SCRIPT.exists():
        return
    try:
        subprocess.run(
            ["bash", str(NOTIFY_SCRIPT), status, message],
            check=False,
            timeout=10,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass  # 通知の失敗で本処理を止めない


def _template_application(job: dict) -> str:
    """テンプレートベースの応募文（4要素を含む）

    含める4要素：
      ① タイトルへの具体的応答  ② 品質シグナル（人間ダブルチェック）
      ③ 納期確認の能動姿勢      ④ 継続・追加対応の余白
    """
    title = job.get("title", "")
    title_short = title[:30]
    category = job.get("category", "")
    title_lower = title.lower()

    # カテゴリ別の作業手順（特殊技能 → 一般作業 の順で判定）
    if "scraping" in category or "スクレイピング" in title or "収集" in title:
        skill = "PythonとPlaywrightを用いたWebスクレイピング"
        method = (
            "対象サイトの構造を事前に確認のうえ、必要項目を正確に取得し、"
            "Excel/CSV形式で整形して納品いたします"
        )
    elif any(k in title for k in ["VBA", "マクロ", "自動化"]):
        skill = "Excel VBA／Pythonによる業務自動化"
        method = (
            "現在の手作業フローをヒアリングのうえ、再利用可能なマクロ・スクリプトとして実装いたします"
        )
    elif any(k in title for k in ["リスト", "一覧", "転記", "名簿"]):
        skill = "リスト作成・転記作業"
        method = (
            "指定フォーマットに沿って漏れなく転記し、重複・表記ゆれをチェックして納品いたします"
        )
    elif "excel" in category or "エクセル" in title_lower or "excel" in title_lower:
        skill = "ExcelおよびPythonを用いたデータ処理・入力"
        method = (
            "テンプレートに沿って正確に入力し、入力後にチェックリストでダブル確認を行います"
        )
    else:
        skill = "データ入力・収集作業"
        method = "ご指定の手順・形式に沿って丁寧かつ正確に対応いたします"

    # 応募文（4要素を順に配置）
    return (
        # ① タイトルへの具体的応答 ＋ スキル提示
        f"はじめまして。{skill}を専門としており、ご依頼の「{title_short}」を確実に対応できます。\n\n"
        # 作業方法の具体化
        f"作業方法：{method}。"
        # ② 品質シグナル（AI 訴求は単価下押し圧力のため「人間監修」訴求に統一）
        "構成設計から納品前のダブルチェックまで人間が監修する体制で品質を担保しております。\n\n"
        # ③ 納期確認の能動姿勢
        "納期は厳守いたします。件数・希望納期・出力形式を教えていただければ、所要時間を即お見積もりします。"
        # ④ 継続・追加対応の余白
        "定期的なご依頼や、追加作業（集計・グラフ化など）にも対応可能ですので、お気軽にご相談ください。"
    )


def generate_application(job: dict) -> dict:
    title = job.get("title", "（タイトル不明）")
    try:
        text = _template_application(job)
        if not text.strip():
            raise ValueError("応募文が空です")
        _notify("success", title)
        return {**job, "application_text": text, "status": "template"}
    except Exception as e:
        _notify("failure", f"{title} - {e}")
        raise


def run(jobs: list[dict] | None = None):
    if jobs is None:
        files = sorted(OUTPUT_DIR.glob("*_evaluated.json"))
        if not files:
            print("[ERROR] 評価済みファイルが見つかりません。02_evaluate.py を先に実行してください")
            return []
        all_jobs = json.loads(files[-1].read_text(encoding="utf-8"))
        jobs = [j for j in all_jobs if j.get("recommend")]

    print(f"[応募文生成] {len(jobs)}件")
    applications = [generate_application(j) for j in jobs]

    out_path = OUTPUT_DIR / f"{datetime.now().strftime('%Y-%m-%d_%H%M')}_applications.json"
    out_path.write_text(
        json.dumps(applications, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 人間確認用のサマリを表示
    print("\n" + "=" * 60)
    print("【要確認】以下の応募文を送信してよいか確認してください")
    print("=" * 60)
    for i, app in enumerate(applications, 1):
        print(f"\n[{i}] {app['title']}")
        print(f"    URL: {app['url']}")
        print(f"    応募文:\n{app.get('application_text', '')}")
        print("-" * 40)

    print(f"\n[完了] {len(applications)}件の応募文を生成 → {out_path}")
    print("[次のステップ] 内容確認後、各プラットフォームから手動で送信してください")
    return applications


if __name__ == "__main__":
    run()
