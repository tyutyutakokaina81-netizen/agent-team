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


def _template_application_writing(job: dict) -> str:
    """ライティング案件向けテンプレ応募文（CSO 5パターン）

    job["recommended_template"] で①〜⑤を切替。
    関連：CSO/outputs/2026-05-20_クラウドワークス応募文テンプレ.md
    """
    title = job.get("title", "")
    template_id = job.get("recommended_template", "①SEO汎用")
    kw_hint = title[:25] if title else "ご依頼内容"

    if "②継続" in template_id:
        return f"""ご担当者様

「{kw_hint}」の継続執筆案件、拝見しました。
SEOライティングの○○と申します。

継続案件はトーン・構成パターンを早期に揃えることが重要と考えます。
初回1〜2本は私側の検証も兼ねて以下の体制でお受けします。

【ご提案】
・初回1本目：構成案を3パターンご提示 → ご選択後に執筆
・2本目以降：1本目で確定したフォーマットに沿って効率納品
・週次定例（15分・任意）でテーマ・優先度をすり合わせ

【納品ペース】週3本まで安定対応、繁忙期は事前相談で週5本まで可

【ご質問】
過去納品いただいている記事のうち「特に評価が高かった1本」のURLを
共有いただけますと、トーンを正確に揃えられます。

ご検討よろしくお願いいたします。"""

    if "③初心者歓迎" in template_id:
        return f"""ご担当者様

「初心者歓迎」とのことで、応募させていただきました。
SEOライティングを始めて間もない○○と申します。

クラウドワークスでの実績はこれからですが、以下の点でご期待にお応えできます。

【お約束できること】
・初回ご返信は24時間以内
・執筆前に必ず構成案をご提示し、方向性合意後に本文着手
・修正は2回まで無料
・納期は厳守

【サンプル記事】
2,000字程度のSEO記事サンプルを3本ご用意しております。
ご希望のジャンルをお知らせいただければ、リンクをお送りします。

【スタートアッププラン（5名様限定）】
ご評価をいただくため、2,000字を 4,000円（通常 8,000円）で承ります。
納品後にご評価コメントをお願いできれば幸いです。

ご質問・ご要望ありましたらお気軽にお知らせください。"""

    if "④専門" in template_id:
        return f"""ご担当者様

「{kw_hint}」の記事案件、拝見しました。
○○と申します。

このテーマは「読者の比較検討段階で読まれる記事が多く、信頼性と網羅性のバランスが鍵」と理解しており、以下の方針でご提案いたします。

【執筆方針案】
・構成：H2を3〜4個の比較軸で構成（読者の検討項目に対応）
・差別化要素：実体験ベースの具体例＋公的データの引用
・参考データ：公的統計・公式情報を最低2点引用

【納期】ご提示の納期で対応可能です

【ご質問】
ターゲット読者の検討段階（認知／比較／決定）はどの位置でしょうか？
上記方針でよろしければ、構成案を本日中にお送りすることも可能です。

ご検討よろしくお願いいたします。"""

    if "⑤AI可" in template_id:
        return f"""ご担当者様

「AI執筆可」とのこと、ご応募させていただきます。
執筆支援ツールを活用しつつ、必ず人間がレビュー・編集を行う方針で
ライティングを行っております、○○と申します。

【ワークフロー】
1. ヒアリング（キーワード・読者像・トーン）
2. 構成案ご提示・合意
3. 執筆支援ツールで初稿生成 → 事実確認・文章調整・固有名詞チェック
4. メタディスクリプション含めて納品

【品質保証】
・コピペチェックツール通過済みを納品基準とします
・事実関係は公的情報・公式サイトを参照しソースを併記可
・修正は2回まで無料

【ご質問】
ツール出力をベースにする旨、記事末尾やメタデータに表記が必要でしょうか？

ご検討よろしくお願いいたします。"""

    # デフォルト：①SEO汎用
    return f"""ご担当者様

「{kw_hint}」の記事執筆案件、興味深く拝見しました。
SEOライティングを中心に活動しております、○○と申します。

【ご提案できること】
・キーワード分析〜競合上位記事の構成把握〜本文執筆まで一貫対応
・執筆着手前に必ず構成案（H2/H3）をご提示し、方向性合意後に本文へ進みます
・初回ご返信は24時間以内、修正は2回まで無料で承ります

【ご提示単価への対応】
ご提示の文字単価で承ります。初回は実績作りも兼ねて、
通常より丁寧にレビューを行います。

【ご質問】
1点だけ確認させてください。
ターゲット読者像と、参考にされている記事URLがあれば共有いただけますか？
合っていれば、本日中に構成案ドラフトをお送りすることも可能です。

ご検討よろしくお願いいたします。"""


def _template_application(job: dict) -> str:
    """APIキー不要のテンプレートベース応募文

    search_category が writing なら writing 向けテンプレへ分岐。
    既存挙動（data_entry）は不変。
    """
    if job.get("search_category") == "writing" or job.get("category") == "writing":
        return _template_application_writing(job)

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
