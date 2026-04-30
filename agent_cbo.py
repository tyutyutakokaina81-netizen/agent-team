#!/usr/bin/env python3
"""
agent_cbo.py — CBO（新規事業開発・稟議）自動実行

CROのトレンドレポートを受け取り:
1. 新規事業候補を自動スクリーニング
2. 採算性を試算
3. 稟議書をCBO/outputs/に出力（CEO承認待ち）
"""

import json
from datetime import datetime, date
from pathlib import Path

REPO = Path(__file__).parent
OUTPUT_DIR = REPO / "CBO" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TODAY = date.today().isoformat()
APPROVAL_FILE = REPO / "CBO" / "approvals.json"


# ── 事業候補データベース ─────────────────────────────────────
# CROのトレンドと照合して優先順位をつける候補
BUSINESS_IDEAS = [
    {
        "id": "B001",
        "title": "高岡市日帰り旅行PDFガイド",
        "category": "コンテンツ販売",
        "price": 980,
        "cost": 0,
        "time_to_market": "3日",
        "monthly_potential": 30000,
        "fit_keywords": ["旅行", "日帰り", "穴場", "GW", "高岡"],
        "platform": "note",
        "risk": "低",
    },
    {
        "id": "B002",
        "title": "フリーランス案件管理Excelテンプレ",
        "category": "テンプレ販売",
        "price": 1480,
        "cost": 0,
        "time_to_market": "2日",
        "monthly_potential": 50000,
        "fit_keywords": ["フリーランス", "副業", "Excel", "案件管理"],
        "platform": "BOOTH",
        "risk": "低",
    },
    {
        "id": "B003",
        "title": "SNS運用代行（個人・小規模店舗向け）",
        "category": "サービス提供",
        "price": 30000,
        "cost": 0,
        "time_to_market": "即日",
        "monthly_potential": 90000,
        "fit_keywords": ["SNS運用", "Instagram", "副業"],
        "platform": "Lancers/直接契約",
        "risk": "中（継続コミット必要）",
    },
    {
        "id": "B004",
        "title": "高岡市観光YouTube チャンネル収益化",
        "category": "広告収益",
        "price": 0,
        "cost": 0,
        "time_to_market": "3〜6ヶ月",
        "monthly_potential": 50000,
        "fit_keywords": ["旅行", "観光", "YouTube", "HiddenJapan"],
        "platform": "YouTube",
        "risk": "中（時間かかる）",
    },
    {
        "id": "B005",
        "title": "データ入力・スクレイピング受注（柱D）",
        "category": "受託案件",
        "price": 10000,
        "cost": 0,
        "time_to_market": "即日",
        "monthly_potential": 100000,
        "fit_keywords": ["データ入力", "スクレイピング", "Excel", "副業", "自動化", "フリーランス"],
        "platform": "CrowdWorks/Lancers",
        "risk": "低",
    },
]


# ── 採算スクリーニング ─────────────────────────────────────
def screen_ideas(ideas: list, cro_trends: list = None) -> list:
    """採算基準でスクリーニングし、優先順位をつける"""
    trend_keywords = []
    if cro_trends:
        for t in cro_trends:
            trend_keywords.extend(t.get("keyword", "").split())

    scored = []
    for idea in ideas:
        score = 0
        # 即時収益性（price > 0 and 短期）
        if idea["price"] > 0:
            score += 30
        if idea["time_to_market"] in ["即日", "2日", "3日"]:
            score += 25
        # トレンド適合度
        fit = sum(1 for k in idea["fit_keywords"] if any(k in tw for tw in trend_keywords))
        score += fit * 10
        # 月次ポテンシャル
        if idea["monthly_potential"] >= 50000:
            score += 20
        elif idea["monthly_potential"] >= 10000:
            score += 10
        # リスク
        if idea["risk"] == "低":
            score += 15
        elif idea["risk"] == "中":
            score += 5

        scored.append({**idea, "score": score})

    return sorted(scored, key=lambda x: x["score"], reverse=True)


# ── 稟議書生成 ────────────────────────────────────────────
def generate_ringi(idea: dict, rank: int) -> str:
    monthly = idea["monthly_potential"]
    annual = monthly * 12
    roi = "∞（初期投資¥0）"

    lines = [
        f"# 稟議書 No.{idea['id']} — {idea['title']}",
        f"申請日: {TODAY} | 申請者: CBO | 承認者: CEO",
        f"優先順位: 第{rank}位（採算スコア: {idea['score']}点）",
        "",
        "---",
        "",
        "## 事業概要",
        f"- **サービス名**: {idea['title']}",
        f"- **カテゴリ**: {idea['category']}",
        f"- **販売価格**: ¥{idea['price']:,}",
        f"- **プラットフォーム**: {idea['platform']}",
        f"- **市場投入まで**: {idea['time_to_market']}",
        "",
        "## 収益試算",
        f"| 指標 | 金額 |",
        f"|------|------|",
        f"| 初期費用 | ¥{idea['cost']:,} |",
        f"| 単価 | ¥{idea['price']:,} |",
        f"| 月次ポテンシャル | ¥{monthly:,} |",
        f"| 年次ポテンシャル | ¥{annual:,} |",
        f"| ROI | {roi} |",
        "",
        "## リスク評価",
        f"- リスクレベル: **{idea['risk']}**",
        f"- トレンド適合キーワード: {', '.join(idea['fit_keywords'][:3])}",
        "",
        "## 実行に必要なリソース",
        "- 追加費用: ¥0",
        "- 実装担当: CDO（自動化）+ CMO（コンテンツ）",
        f"- 想定工数: {idea['time_to_market']}",
        "",
        "## 推奨判断",
        "",
    ]

    if idea["score"] >= 60:
        verdict = "✅ **実施推奨**"
        reason = "採算性高・リスク低・即時実行可能"
    elif idea["score"] >= 40:
        verdict = "⚠️ **条件付き実施**"
        reason = "中期的に有望だが優先度は中程度"
    else:
        verdict = "❌ **保留**"
        reason = "時間・リソース効率が低い"

    lines += [
        f"{verdict}",
        f"理由: {reason}",
        "",
        "---",
        "",
        "## CEO承認欄",
        "```",
        "[ ] 承認  [ ] 差し戻し  [ ] 却下",
        "",
        "コメント:",
        "承認日:",
        "```",
    ]
    return "\n".join(lines)


def load_approvals() -> dict:
    if APPROVAL_FILE.exists():
        return json.loads(APPROVAL_FILE.read_text())
    return {"approved": [], "rejected": [], "pending": []}


def run() -> list:
    print("━" * 45)
    print("  CBO — 新規事業開発・稟議")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("━" * 45)

    # CROのトレンドデータを読み込む
    cro_dir = REPO / "CRO" / "outputs"
    cro_trends = []
    latest_cro = sorted(cro_dir.glob("*_trend_data.json"), reverse=True)
    if latest_cro:
        data = json.loads(latest_cro[0].read_text())
        cro_trends = data.get("seasonal_trends", [])
        print(f"\n  CROレポート読み込み: {latest_cro[0].name}")
    else:
        print("\n  CROレポートなし（デフォルト分析）")

    print("\n  事業候補をスクリーニング中...")
    ranked = screen_ideas(BUSINESS_IDEAS, cro_trends)

    print(f"\n  採算性ランキング TOP5:")
    for i, idea in enumerate(ranked[:5], 1):
        print(f"  {i}. [{idea['score']}点] {idea['title']} ¥{idea['price']:,}/件")

    # 上位3件の稟議書を生成
    print("\n  稟議書を生成中...")
    ringi_list = []
    for rank, idea in enumerate(ranked[:3], 1):
        ringi = generate_ringi(idea, rank)
        fname = f"{TODAY}_ringi_{idea['id']}_{idea['title'][:15]}.md"
        out = OUTPUT_DIR / fname.replace("/", "").replace(" ", "_")
        out.write_text(ringi, encoding="utf-8")
        ringi_list.append(idea)
        print(f"  ✅ 稟議書{rank}: {idea['title']}")

    # CEO向けサマリーJSON
    summary_out = OUTPUT_DIR / f"{TODAY}_ringi_summary.json"
    summary_out.write_text(json.dumps({
        "date": TODAY,
        "top_proposals": ranked[:3],
        "status": "CEO承認待ち",
    }, ensure_ascii=False, indent=2))

    print(f"\n  稟議書 → CEO/承認待ち")
    print("━" * 45)
    return ranked[:3]


if __name__ == "__main__":
    run()
