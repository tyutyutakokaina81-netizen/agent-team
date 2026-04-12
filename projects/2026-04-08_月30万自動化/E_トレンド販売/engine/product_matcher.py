"""
product_matcher.py — トレンドからデジタル商品を企画する

trend_detector.py が検知したトレンドワードを受け取り、
Claude に「このトレンドで売れるデジタル商品」を提案させる。

使い方:
  python product_matcher.py                    # 最新トレンドから自動提案
  python product_matcher.py "AI 副業"          # 指定キーワードで提案
"""

import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

MATCH_PROMPT = """
あなたはデジタル商品の企画専門家です。
以下のトレンドキーワードに対して、「今すぐ作って売れる無店舗デジタル商品」を3つ提案してください。

# トレンド情報
キーワード: {keyword}
トラフィック: {traffic}
関連ニュース: {news}

# 制約条件
- 無店舗販売（note / BOOTH / Gumroad / Brain で販売）
- 在庫なし・発送なし（デジタルダウンロード商品のみ）
- AI（Claude）で1時間以内に作成可能な商品
- 価格帯: ¥500〜¥5,000
- ターゲット: このトレンドに興味を持った一般消費者

# 商品カテゴリ例
- テンプレート（Excel / Google Sheets / Notion）
- チェックリスト・ガイドPDF
- プロンプト集（ChatGPT / Claude用）
- まとめ資料・解説レポート
- ワークシート・計画表

# 出力形式（JSONのみ、説明不要）
[
  {{
    "product_name": "商品名（30字以内）",
    "description": "商品説明（100字以内）",
    "format": "テンプレート / PDF / プロンプト集 等",
    "platform": "note / BOOTH / Gumroad",
    "price": 価格（数値）,
    "target": "ターゲット（20字以内）",
    "production_time_min": 作成時間（分）,
    "selling_points": ["セールスポイント1", "セールスポイント2", "セールスポイント3"],
    "trend_relevance": "なぜ今このトレンドで売れるか（50字以内）",
    "confidence": 1-10の自信度
  }},
  ...
]
"""


def call_claude(prompt: str, model: str = "claude-haiku-4-5-20251001") -> str:
    if not ANTHROPIC_API_KEY:
        raise EnvironmentError("ANTHROPIC_API_KEY が設定されていません")
    payload = json.dumps({
        "model": model,
        "max_tokens": 2048,
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


def _rule_based_match(keyword: str) -> list[dict]:
    """APIキー不要のルールベース商品提案"""
    templates = [
        {
            "product_name": f"【{keyword}】完全ガイド — 初心者向けステップ解説",
            "description": f"{keyword}について初心者が最初に知るべきことをまとめたPDFガイド",
            "format": "PDF",
            "platform": "note",
            "price": 980,
            "target": f"{keyword}に興味がある初心者",
            "production_time_min": 60,
            "selling_points": ["初心者向け", "ステップ形式で分かりやすい", "最新トレンド対応"],
            "trend_relevance": f"「{keyword}」が急上昇中。情報を求める人が増えている",
            "confidence": 5,
            "generated_by": "rule_based",
        },
        {
            "product_name": f"【{keyword}】チェックリスト & テンプレート集",
            "description": f"{keyword}に必要な準備・手順をチェックリスト化。テンプレートで即実行可能",
            "format": "Google Sheets テンプレート",
            "platform": "BOOTH",
            "price": 1480,
            "target": f"{keyword}を実践したい人",
            "production_time_min": 45,
            "selling_points": ["コピペで使える", "チェックリスト形式", "実践的"],
            "trend_relevance": f"「{keyword}」で検索した人がすぐ使える実用ツール",
            "confidence": 4,
            "generated_by": "rule_based",
        },
        {
            "product_name": f"【{keyword}】AI プロンプト集 10 選",
            "description": f"{keyword}に関する作業を AI で効率化するためのプロンプト集",
            "format": "プロンプト集（Markdown）",
            "platform": "note",
            "price": 500,
            "target": f"AI を使って{keyword}に取り組みたい人",
            "production_time_min": 30,
            "selling_points": ["コピペで使える", "ChatGPT/Claude両対応", "10種類"],
            "trend_relevance": f"AI × {keyword} の組み合わせ需要",
            "confidence": 3,
            "generated_by": "rule_based",
        },
    ]
    return templates


def match_products(trend: dict) -> list[dict]:
    """トレンドから商品提案を生成"""
    keyword = trend.get("keyword", "")
    traffic = trend.get("traffic", "不明")
    news = json.dumps(trend.get("news", [])[:3], ensure_ascii=False)

    if ANTHROPIC_API_KEY:
        prompt = MATCH_PROMPT.format(keyword=keyword, traffic=traffic, news=news)
        try:
            raw = call_claude(prompt)
            start = raw.find("[")
            end = raw.rfind("]") + 1
            products = json.loads(raw[start:end])
            for p in products:
                p["trend_keyword"] = keyword
                p["generated_by"] = "claude"
            return products
        except Exception:
            pass  # フォールバック

    # ルールベース
    products = _rule_based_match(keyword)
    for p in products:
        p["trend_keyword"] = keyword
    return products


def match_all(trends: list[dict], min_score: int = 50) -> list[dict]:
    """複数トレンドを一括で商品マッチング"""
    filtered = [t for t in trends if t.get("product_score", 0) >= min_score]

    if not filtered:
        print("[商品マッチ] スコア条件を満たすトレンドがありません")
        return []

    print(f"[商品マッチ] {len(filtered)}件のトレンドに対して商品提案中...")
    all_products = []
    for i, trend in enumerate(filtered[:5], 1):  # 上位5件のみ
        print(f"  [{i}/{min(len(filtered), 5)}] {trend['keyword']}...", end=" ", flush=True)
        products = match_products(trend)
        all_products.extend(products)
        print(f"→ {len(products)}商品")

    # confidence順ソート
    all_products.sort(key=lambda x: x.get("confidence", 0), reverse=True)

    # 保存
    out = OUTPUT_DIR / f"{datetime.now().strftime('%Y-%m-%d_%H%M')}_products.json"
    out.write_text(json.dumps(all_products, ensure_ascii=False, indent=2), encoding="utf-8")

    # 表示
    print(f"\n{'─' * 60}")
    print(f"  📦 商品提案 Top 5")
    print(f"{'─' * 60}")
    for i, p in enumerate(all_products[:5], 1):
        print(f"  {i}. {p['product_name']}")
        print(f"     ¥{p['price']:,} | {p['format']} | {p['platform']} | 作成{p['production_time_min']}分")
        print(f"     トレンド: {p.get('trend_keyword', '')}")
        print()
    print(f"[完了] {len(all_products)}商品 → {out}")

    return all_products


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] != "--source":
        # 直接キーワード指定
        keyword = " ".join(sys.argv[1:])
        trend = {"keyword": keyword, "traffic": "", "news": [], "product_score": 100}
        products = match_products(trend)
        for p in products:
            print(f"\n  📦 {p['product_name']}")
            print(f"     ¥{p['price']:,} | {p['format']} | {p['platform']}")
            print(f"     {p['description']}")
    else:
        # 最新トレンドファイルから読み込み
        files = sorted(OUTPUT_DIR.glob("*_trends.json"))
        if not files:
            print("[ERROR] trend_detector.py を先に実行してください")
            sys.exit(1)
        trends = json.loads(files[-1].read_text(encoding="utf-8"))
        match_all(trends)
