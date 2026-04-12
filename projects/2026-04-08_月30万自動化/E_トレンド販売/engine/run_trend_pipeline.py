"""
run_trend_pipeline.py — トレンド販売パイプライン統合実行

全フロー:
  1. トレンド検知（Google Trends + Yahoo!）
  2. 商品マッチング（トレンド → デジタル商品提案）
  3. 販売ページ生成（note/BOOTH にそのまま貼れる文面）

使い方:
  python run_trend_pipeline.py           # 全フロー実行
  python run_trend_pipeline.py detect    # トレンド検知のみ
  python run_trend_pipeline.py match     # 商品マッチのみ（要: 検知済み）
  python run_trend_pipeline.py listing   # 販売ページのみ（要: マッチ済み）
"""

import sys
from datetime import datetime
from importlib import import_module


def run_full():
    """フルパイプライン実行"""
    print("\n" + "━" * 60)
    print("  🔥 トレンド販売パイプライン v1.0")
    print(f"  実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("━" * 60)

    # Phase 1: トレンド検知
    print("\n[PHASE 1/3] トレンド検知")
    detector = import_module("trend_detector")
    trends = detector.detect_trends()

    if not trends:
        print("\n[中断] トレンドが検知できませんでした")
        return

    recommended = [t for t in trends if t.get("product_score", 0) >= 50]
    print(f"  商品化候補: {len(recommended)}件")

    if not recommended:
        print("\n[中断] 商品化推奨トレンドがありません")
        return

    # Phase 2: 商品マッチング
    print("\n[PHASE 2/3] 商品マッチング")
    matcher = import_module("product_matcher")
    products = matcher.match_all(trends)

    if not products:
        print("\n[中断] 商品提案を生成できませんでした")
        return

    # Phase 3: 販売ページ生成
    print("\n[PHASE 3/3] 販売ページ生成")
    generator = import_module("listing_generator")
    listings = generator.generate_all(products, top_n=3)

    # サマリ
    print("\n" + "━" * 60)
    print("  ✅ パイプライン完了")
    print("━" * 60)
    print(f"  検知トレンド: {len(trends)}件")
    print(f"  商品化候補:   {len(recommended)}件")
    print(f"  商品提案:     {len(products)}件")
    print(f"  販売ページ:   {len(listings)}件")
    print()

    if listings:
        print("  📋 次のアクション:")
        for i, listing in enumerate(listings[:3], 1):
            platform = listing.get("platform", "note")
            price = listing.get("price", 980)
            name = listing.get("product_name", "")
            print(f"    {i}. {platform} に出品: {name}（¥{price:,}）")
        print()
        print("  出品手順:")
        print("    1. outputs/ フォルダの listing_*.md を開く")
        print("    2. 内容をそのまま note / BOOTH に貼り付ける")
        print("    3. 価格を設定して公開")
        print()
        print("  所要時間: 約10分（1商品あたり3分）")

    print("━" * 60)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "full"

    if cmd == "full":
        run_full()
    elif cmd == "detect":
        detector = import_module("trend_detector")
        detector.detect_trends()
    elif cmd == "match":
        matcher = import_module("product_matcher")
        from pathlib import Path
        import json
        OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
        files = sorted(OUTPUT_DIR.glob("*_trends.json"))
        if not files:
            print("[ERROR] trend_detector.py を先に実行してください")
        else:
            trends = json.loads(files[-1].read_text(encoding="utf-8"))
            matcher.match_all(trends)
    elif cmd == "listing":
        generator = import_module("listing_generator")
        from pathlib import Path
        import json
        OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
        files = sorted(OUTPUT_DIR.glob("*_products.json"))
        if not files:
            print("[ERROR] product_matcher.py を先に実行してください")
        else:
            products = json.loads(files[-1].read_text(encoding="utf-8"))
            generator.generate_all(products)
    else:
        print("使い方:")
        print("  python run_trend_pipeline.py           # 全フロー")
        print("  python run_trend_pipeline.py detect    # トレンド検知のみ")
        print("  python run_trend_pipeline.py match     # 商品マッチのみ")
        print("  python run_trend_pipeline.py listing   # 販売ページのみ")
