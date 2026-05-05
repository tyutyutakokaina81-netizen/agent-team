"""CrowdWorks応募文生成。

カテゴリ別テンプレを切替：
    --kind data        : データ入力・リスト作成（L1・¥3〜10K）
    --kind writer      : SEOライティング・記事執筆（L2・¥10〜30K）★推奨
    --kind ai_support  : AI活用支援・プロンプト作成（L2/L3・¥30〜100K）
    --kind consultant  : 業務改善・SNS運用代行（L3・¥50K〜）

例:
    python3 cw_apply.py "ECサイト商品500件入力" --kind data
    python3 cw_apply.py "SEO記事3000字 健康ジャンル" --kind writer
    python3 cw_apply.py "プロンプト設計支援" --kind ai_support
    python3 cw_apply.py --from-json /path/to/job.json
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

OUT = Path.home() / "ai-auto" / "outputs"

PORTFOLIO = {
    "data": "Excel・スプレッドシート500件以上の整形実績",
    "writer": "note・ブログ累計100本以上の執筆実績、SEO構成設計対応可能",
    "ai_support": "Claude / GPT を用いた業務自動化スクリプト10件以上の実装実績",
    "consultant": "個人事業主・小規模事業者のSNS運用設計、月次レポート作成経験",
}

TEMPLATES = {
    "data": {
        "category": "データ入力・リスト作成",
        "tools": ["Excel / Google スプレッドシート", "Word / Google ドキュメント", "簡易な調査・要約・データ整形"],
        "approach": "納期厳守、丁寧な作業、ご報告の早さを大切にしています。",
        "proposal": "まずは少量から着手し、品質をご確認いただいた上で本数量へ進める形でも問題ございません。",
    },
    "writer": {
        "category": "SEOライティング・記事執筆",
        "tools": [
            "WordPress入稿対応",
            "Google検索意図分析・キーワード設計",
            "見出し構成（H2/H3）設計と本文執筆",
            "画像挿入位置の指定・altテキスト案",
        ],
        "approach": "検索意図に沿った構成設計と、読了率を高める導入文・見出しの最適化を心がけています。",
        "proposal": "テストライティング1本を低価格でお引き受けし、トーン・構成のすり合わせ後に本契約というステップでも対応可能です。1記事あたり3,000字を3営業日以内で納品します。",
    },
    "ai_support": {
        "category": "AI活用支援・プロンプト作成",
        "tools": [
            "Claude / ChatGPT / Gemini の業務適用設計",
            "プロンプトテンプレート作成と社内マニュアル化",
            "Python による自動化スクリプト実装",
            "API連携（Anthropic / OpenAI）の構築",
        ],
        "approach": "属人化しない『誰でも使える形』に落とし込むことを重視しています。",
        "proposal": "現状の業務フローを30分のヒアリングで把握し、最小構成のPoCを1週間で提出。ご評価後に本実装へ進むスモールスタート方式を提案します。",
    },
    "consultant": {
        "category": "SNS運用代行・業務改善",
        "tools": [
            "X / Instagram / note 運用設計",
            "コンテンツカレンダー作成・週次投稿計画",
            "月次レポート（投稿数・反応・改善提案）",
            "AI活用での投稿文生成基盤構築",
        ],
        "approach": "数字で示せる改善提案と、継続可能な運用設計を両立させることを重視しています。",
        "proposal": "初月は現状分析と運用設計に集中し、2ヶ月目から定常運用に入る形を推奨します。月額¥50K〜の継続契約でご相談可能です。",
    },
}


def build(title: str, kind: str = "data", *, score: float | None = None,
          reason: str | None = None) -> str:
    if kind not in TEMPLATES:
        raise ValueError(f"--kind は {sorted(TEMPLATES)} のいずれか")
    t = TEMPLATES[kind]
    score_line = f"\n（評価スコア: {score:.1f} / 採用理由: {reason}）\n" if score is not None else ""
    tools = "\n".join(f"- {x}" for x in t["tools"])
    return f"""はじめまして。
ご案件「{title}」を拝見し、ぜひお力になりたくご応募いたしました。{score_line}
【自己紹介】
{t["category"]} を中心に対応している個人事業主です。
{t["approach"]}
過去実績：{PORTFOLIO[kind]}

【対応可能ツール・スキル】
{tools}

【作業可能時間】
平日 9:00〜18:00 を中心に、夜間・土日も柔軟に対応可能です。
ご連絡には2営業時間以内に返信いたします。

【ご提案】
{t["proposal"]}
不明点はその都度ご確認のうえ、品質と納期を両立した納品を心がけます。

ご検討のほど、どうぞよろしくお願いいたします。
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="CrowdWorks応募文生成")
    parser.add_argument("title", nargs="?", default="データ入力・リスト作成のお仕事")
    parser.add_argument("--kind", default="data", choices=sorted(TEMPLATES))
    parser.add_argument("--from-json", dest="from_json",
                        help="既存パイプラインのスコアリング結果JSON（kindも含められる）")
    args = parser.parse_args()

    if args.from_json:
        data = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
        title = data["title"]
        kind = data.get("kind", args.kind)
        score = data.get("score")
        reason = data.get("reason")
    else:
        title = args.title
        kind = args.kind
        score = None
        reason = None

    body = build(title, kind, score=score, reason=reason)
    OUT.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d_%H%M")
    safe_title = title.replace("/", "_").replace(" ", "_")[:40]
    path = OUT / f"{today}_cw_apply_{kind}_{safe_title}.txt"
    path.write_text(body, encoding="utf-8")
    print(f"生成完了: {path}")


if __name__ == "__main__":
    main()
