"""
listing_generator.py — 販売ページ生成

product_matcher.py が提案した商品に対して、
そのまま note / BOOTH に貼れる販売ページ文面を生成する。

使い方:
  python listing_generator.py              # 最新の商品提案から生成
  python listing_generator.py --index 0    # 特定の商品のみ
"""

import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

LISTING_PROMPT = """
以下のデジタル商品の販売ページ文面を作成してください。
{platform} にそのまま貼れる形式で出力してください。

# 商品情報
商品名: {product_name}
説明: {description}
形式: {format}
価格: ¥{price}
ターゲット: {target}
セールスポイント: {selling_points}
トレンドとの関連: {trend_relevance}

# 出力に含めること
1. タイトル（SEOを意識、30字以内）
2. キャッチコピー（1行）
3. 本文（800〜1200字、以下の構成）:
   - こんな悩みありませんか？（3つ）
   - この商品で解決できること（3つ）
   - 商品の中身（具体的に）
   - 購入後の使い方（3ステップ）
   - よくある質問（2問）
   - 最後の一押し（行動喚起）
4. 価格表記
5. ハッシュタグ（5〜10個）

販売ページの文面のみ出力してください。
"""


def call_claude(prompt: str) -> str:
    if not ANTHROPIC_API_KEY:
        raise EnvironmentError("ANTHROPIC_API_KEY が設定されていません")
    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
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


def _template_listing(product: dict) -> str:
    """APIキー不要のテンプレート販売ページ"""
    name = product.get("product_name", "")
    desc = product.get("description", "")
    price = product.get("price", 980)
    target = product.get("target", "")
    points = product.get("selling_points", [])
    fmt = product.get("format", "")
    trend_kw = product.get("trend_keyword", "")

    points_text = "\n".join(f"  {p}" for p in points)

    return f"""# {name}

{desc}

---

## こんな方におすすめ

- 「{trend_kw}」について調べたけど、情報がまとまっていない
- 自分でゼロから作るのは時間がかかりすぎる
- すぐに使える実用的なツールが欲しい

## この商品でできること

{points_text}

## 商品の中身

- 形式: {fmt}
- ボリューム: すぐに使える実用コンテンツ
- 対象: {target}

## 使い方（3ステップ）

1. 購入後、ダウンロードリンクからファイルを取得
2. そのままコピーして使用開始
3. 自分の状況に合わせてカスタマイズ

## よくある質問

**Q. 初心者でも使えますか？**
A. はい。専門知識は不要です。ステップ通りに進めるだけで使えます。

**Q. 返金はできますか？**
A. デジタル商品の性質上、購入後の返金はお受けできません。

---

## 価格

**¥{price:,}（税込）**

「{trend_kw}」が話題の今だからこそ、このタイミングで手に入れてください。

---

#{trend_kw} #{fmt.replace(' ', '')} #テンプレート #効率化 #AI活用
"""


def generate_listing(product: dict) -> dict:
    """商品の販売ページ文面を生成"""
    if ANTHROPIC_API_KEY:
        prompt = LISTING_PROMPT.format(
            platform=product.get("platform", "note"),
            product_name=product.get("product_name", ""),
            description=product.get("description", ""),
            format=product.get("format", ""),
            price=product.get("price", 980),
            target=product.get("target", ""),
            selling_points=json.dumps(product.get("selling_points", []), ensure_ascii=False),
            trend_relevance=product.get("trend_relevance", ""),
        )
        try:
            listing_text = call_claude(prompt)
            return {**product, "listing_text": listing_text, "listing_by": "claude"}
        except Exception:
            pass

    listing_text = _template_listing(product)
    return {**product, "listing_text": listing_text, "listing_by": "template"}


def generate_all(products: list[dict], top_n: int = 3) -> list[dict]:
    """上位N商品の販売ページを一括生成"""
    print(f"[販売ページ生成] 上位{top_n}商品")
    listings = []
    for i, product in enumerate(products[:top_n], 1):
        print(f"  [{i}/{top_n}] {product['product_name']}...", end=" ", flush=True)
        listing = generate_listing(product)
        listings.append(listing)
        print("✓")

    # 保存
    out = OUTPUT_DIR / f"{datetime.now().strftime('%Y-%m-%d_%H%M')}_listings.json"
    out.write_text(json.dumps(listings, ensure_ascii=False, indent=2), encoding="utf-8")

    # 個別ファイルとしても保存（コピペ用）
    for i, listing in enumerate(listings, 1):
        md_out = OUTPUT_DIR / f"{datetime.now().strftime('%Y-%m-%d_%H%M')}_listing_{i}.md"
        md_out.write_text(listing.get("listing_text", ""), encoding="utf-8")
        print(f"  → {md_out}")

    print(f"\n[完了] {len(listings)}件の販売ページ生成済み")
    return listings


if __name__ == "__main__":
    files = sorted(OUTPUT_DIR.glob("*_products.json"))
    if not files:
        print("[ERROR] product_matcher.py を先に実行してください")
        sys.exit(1)

    products = json.loads(files[-1].read_text(encoding="utf-8"))

    if "--index" in sys.argv:
        idx = int(sys.argv[sys.argv.index("--index") + 1])
        listing = generate_listing(products[idx])
        print(listing["listing_text"])
    else:
        generate_all(products)
