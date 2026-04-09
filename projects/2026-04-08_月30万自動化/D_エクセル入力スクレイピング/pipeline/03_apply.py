"""
03_apply.py — 応募文生成
案件情報をもとに Claude が最適な応募文を生成する。
送信は人手確認後（規約グレーのため半自動運用）。
"""

import json
import os
import urllib.request
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

APPLY_PROMPT = """
あなたはクラウドソーシングの応募文を作成するプロフェッショナルです。
以下の案件に対して、受注率の高い応募文を作成してください。

# 案件情報
タイトル: {title}
URL: {url}
カテゴリ: {category}
想定単価: ¥{price}

# 自己PR（使用可能なスキル）
- Pythonによるデータ処理・自動化
- Excel/CSVの高精度データ入力（AI支援＋人間確認）
- Webスクレイピング（BeautifulSoup/Playwright）
- 納期厳守・丁寧なコミュニケーション

# 応募文の条件
- 200〜300文字
- 具体的な作業方法に触れる
- 納期・品質への姿勢を示す
- 自然な日本語で、押しつけがましくない

応募文のみ出力してください（説明・前置き不要）。
"""


def call_claude(prompt: str) -> str:
    if not ANTHROPIC_API_KEY:
        raise EnvironmentError("ANTHROPIC_API_KEY が設定されていません")

    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 512,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        body = json.loads(res.read().decode("utf-8"))
    return body["content"][0]["text"]


def _template_application(job: dict) -> str:
    """APIキー不要のテンプレートベース応募文"""
    title = job.get("title", "")
    category = job.get("category", "")
    price = job.get("estimated_price_jpy", 0)

    if "scraping" in category or "スクレイピング" in title:
        skill = "PythonとPlaywrightを使ったWebスクレイピング"
        detail = "対象サイトの構造を確認し、正確にデータを収集いたします。"
    elif "excel" in category or "エクセル" in title.lower() or "Excel" in title:
        skill = "ExcelおよびPythonを使ったデータ処理・入力作業"
        detail = "正確性を重視し、入力後に必ずダブルチェックを行います。"
    else:
        skill = "データ入力・収集作業"
        detail = "丁寧かつ正確に対応いたします。"

    return f"""はじめまして。{skill}を得意としております。

ご依頼の「{title[:30]}」について、{detail}

納期は厳守いたします。不明点があれば事前に確認させていただきますので、安心してお任せください。ぜひご検討よろしくお願いいたします。"""


def generate_application(job: dict) -> dict:
    if ANTHROPIC_API_KEY:
        prompt = APPLY_PROMPT.format(
            title=job.get("title", ""),
            url=job.get("url", ""),
            category=job.get("category", ""),
            price=job.get("estimated_price_jpy", "不明"),
        )
        try:
            text = call_claude(prompt)
            return {**job, "application_text": text, "status": "draft"}
        except Exception:
            pass

    # APIキーなし → テンプレート応募文
    text = _template_application(job)
    return {**job, "application_text": text, "status": "template"}


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
