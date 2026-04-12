"""
trend_detector.py — トレンド検知エンジン

Google Trends（RSS）+ 急上昇ワードを自動取得し、
売れるデジタル商品のネタを発見する。

依存: 標準ライブラリのみ（外部パッケージ不要）

使い方:
  python trend_detector.py              # 全ソース検索
  python trend_detector.py --source google  # Google Trendsのみ
"""

import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


# ─────────────────────────────────────────────
# HTML タグ除去ユーティリティ
# ─────────────────────────────────────────────

class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts = []

    def handle_data(self, data):
        self._parts.append(data)

    def get_text(self):
        return "".join(self._parts).strip()


def strip_html(html_text: str) -> str:
    s = _HTMLStripper()
    s.feed(html_text)
    return s.get_text()


# ─────────────────────────────────────────────
# Google Trends 急上昇ワード（日本）
# ─────────────────────────────────────────────

GOOGLE_TRENDS_RSS = "https://trends.google.co.jp/trending/rss?geo=JP"


def fetch_google_trends() -> list[dict]:
    """Google Trends 急上昇ワード（RSS）を取得"""
    trends = []
    try:
        req = urllib.request.Request(
            GOOGLE_TRENDS_RSS,
            headers={"User-Agent": "Mozilla/5.0 (compatible; TrendBot/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=15) as res:
            data = res.read().decode("utf-8")

        root = ET.fromstring(data)
        ns = {"ht": "https://trends.google.co.jp/trending/rss"}

        for item in root.findall(".//item"):
            title = item.findtext("title", "").strip()
            if not title:
                continue

            # トラフィック数を取得
            traffic_el = item.find("ht:approx_traffic", ns)
            traffic = traffic_el.text.strip() if traffic_el is not None else ""

            # ニュースタイトルを取得
            news_items = []
            for news in item.findall("ht:news_item", ns):
                news_title = news.findtext("ht:news_item_title", "", ns)
                news_url = news.findtext("ht:news_item_url", "", ns)
                if news_title:
                    news_items.append({
                        "title": strip_html(news_title),
                        "url": news_url,
                    })

            pub_date = item.findtext("pubDate", "")

            trends.append({
                "keyword": title,
                "traffic": traffic,
                "source": "google_trends",
                "news": news_items[:3],
                "pub_date": pub_date,
                "fetched_at": datetime.now().isoformat(),
            })
    except Exception as e:
        print(f"[Google Trends] エラー: {e}")

    return trends


# ─────────────────────────────────────────────
# Yahoo! リアルタイム検索トレンド
# ─────────────────────────────────────────────

def fetch_yahoo_realtime() -> list[dict]:
    """Yahoo! リアルタイム検索のトレンドワードを取得"""
    trends = []
    try:
        url = "https://search.yahoo.co.jp/realtime"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
        )
        with urllib.request.urlopen(req, timeout=15) as res:
            html = res.read().decode("utf-8")

        # トレンドワードを正規表現で抽出（簡易パーサ）
        # Yahoo!のトレンドセクションからキーワードを抽出
        pattern = r'<a[^>]*href="[^"]*realtime[^"]*search[^"]*p=([^&"]+)[^"]*"[^>]*>([^<]+)</a>'
        matches = re.findall(pattern, html)

        seen = set()
        for encoded_kw, display_text in matches:
            kw = urllib.request.unquote(encoded_kw)
            if kw in seen or len(kw) < 2:
                continue
            seen.add(kw)
            trends.append({
                "keyword": kw,
                "traffic": "",
                "source": "yahoo_realtime",
                "news": [],
                "fetched_at": datetime.now().isoformat(),
            })
            if len(trends) >= 20:
                break
    except Exception as e:
        print(f"[Yahoo! リアルタイム] エラー: {e}")

    return trends


# ─────────────────────────────────────────────
# トレンド統合 & スコアリング
# ─────────────────────────────────────────────

def score_trend(trend: dict) -> int:
    """トレンドの「商品化しやすさ」をスコアリング（0-100）"""
    score = 50  # ベーススコア
    kw = trend["keyword"]

    # トラフィック量ボーナス
    traffic = trend.get("traffic", "")
    if traffic:
        # "100,000+" 等の形式を数値化
        num = re.sub(r"[^\d]", "", traffic)
        if num:
            vol = int(num)
            if vol >= 500000:
                score += 20
            elif vol >= 100000:
                score += 15
            elif vol >= 50000:
                score += 10
            elif vol >= 10000:
                score += 5

    # デジタル商品化しやすいカテゴリのキーワード
    digital_friendly = [
        "テンプレ", "テンプレート", "やり方", "始め方", "方法",
        "使い方", "入門", "初心者", "副業", "AI", "ChatGPT", "Claude",
        "効率化", "自動化", "Excel", "スプレッドシート", "ノーコード",
        "プログラミング", "デザイン", "動画編集", "確定申告", "節約",
        "資格", "転職", "フリーランス", "リモートワーク", "投資",
        "ダイエット", "筋トレ", "レシピ", "収納", "整理",
        "SNS", "Instagram", "TikTok", "YouTube", "ブログ",
    ]
    if any(dk in kw for dk in digital_friendly):
        score += 20

    # 物販系（今回は無店舗なので微加点のみ）
    physical_keywords = [
        "ファッション", "コーデ", "新作", "限定", "コラボ",
        "アウトドア", "キャンプ", "ガジェット",
    ]
    if any(pk in kw for pk in physical_keywords):
        score += 5

    # ネガティブワード（商品化しにくい）
    negative = [
        "事故", "逮捕", "死亡", "事件", "地震", "災害",
        "訃報", "不倫", "炎上", "裁判", "戦争",
    ]
    if any(nw in kw for nw in negative):
        score -= 40

    # 政治・スポーツ結果（一過性で商品化困難）
    transient = ["選挙", "試合結果", "速報"]
    if any(tw in kw for tw in transient):
        score -= 15

    return max(0, min(100, score))


def detect_trends(sources: list[str] | None = None) -> list[dict]:
    """全ソースからトレンドを取得し、スコア順に並べる"""
    if sources is None:
        sources = ["google", "yahoo"]

    all_trends = []

    if "google" in sources:
        print("[検知] Google Trends 急上昇ワード取得中...")
        trends = fetch_google_trends()
        all_trends.extend(trends)
        print(f"  → {len(trends)}件")

    if "yahoo" in sources:
        print("[検知] Yahoo! リアルタイム検索トレンド取得中...")
        trends = fetch_yahoo_realtime()
        all_trends.extend(trends)
        print(f"  → {len(trends)}件")

    # スコアリング
    for t in all_trends:
        t["product_score"] = score_trend(t)

    # スコア順ソート
    all_trends.sort(key=lambda x: x["product_score"], reverse=True)

    # 重複除去
    seen = set()
    unique = []
    for t in all_trends:
        if t["keyword"] not in seen:
            seen.add(t["keyword"])
            unique.append(t)

    # 保存
    out = OUTPUT_DIR / f"{datetime.now().strftime('%Y-%m-%d_%H%M')}_trends.json"
    out.write_text(json.dumps(unique, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[完了] {len(unique)}件のトレンド検知 → {out}")

    # トップ10を表示
    print(f"\n{'─' * 60}")
    print(f"  🔥 トレンド Top 10（商品化スコア順）")
    print(f"{'─' * 60}")
    for i, t in enumerate(unique[:10], 1):
        score = t["product_score"]
        bar = "█" * (score // 10)
        source = t["source"].replace("google_trends", "Google").replace("yahoo_realtime", "Yahoo")
        traffic = f" ({t['traffic']})" if t.get("traffic") else ""
        print(f"  {i:2d}. [{score:3d}] {bar:<10} {t['keyword']}{traffic}  [{source}]")
    print(f"{'─' * 60}")

    return unique


# ─────────────────────────────────────────────
# メイン
# ─────────────────────────────────────────────

if __name__ == "__main__":
    sources = None
    if "--source" in sys.argv:
        idx = sys.argv.index("--source")
        if idx + 1 < len(sys.argv):
            sources = [sys.argv[idx + 1]]

    trends = detect_trends(sources)

    # 商品化推奨トレンド
    recommended = [t for t in trends if t["product_score"] >= 60]
    if recommended:
        print(f"\n✅ 商品化推奨: {len(recommended)}件")
        for t in recommended:
            print(f"  → {t['keyword']} (スコア {t['product_score']})")
    else:
        print("\n⚠️  商品化推奨トレンドなし。次の巡回を待ちます。")
