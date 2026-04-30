#!/usr/bin/env python3
"""
agent_cro.py — CRO（トレンド調査部隊）自動実行

外部アクセス制限があるため、以下の方針でトレンド分析を実施:
1. 内部コンテンツパフォーマンス分析（自社キューデータ）
2. 季節・曜日トレンドの知識ベース推定
3. 手動インプット欄（MacでXを見た後に貼り付けるセクション）
4. CMO/CSO/CPOへの推奨アクション生成
"""

import json
from datetime import datetime, date
from pathlib import Path

REPO = Path(__file__).parent
SESSIONS = REPO / ".sessions"
OUTPUT_DIR = REPO / "CRO" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TODAY = date.today().isoformat()
MANUAL_TRENDS_FILE = SESSIONS / "manual_trends.json"


def _internet_available() -> bool:
    """外部接続できるか確認（繋がったら自動でリアルデータ取得に切替）"""
    try:
        import urllib.request
        urllib.request.urlopen("https://www.google.com", timeout=5)
        return True
    except Exception:
        return False


# ── 手動トレンド入力（MacでXを見た後に貼り付ける） ───────────
def load_manual_trends() -> dict:
    """ユーザーが手動で入力したトレンドを読み込む"""
    if MANUAL_TRENDS_FILE.exists():
        return json.loads(MANUAL_TRENDS_FILE.read_text())
    # デフォルト（空のテンプレート）
    return {
        "updated": "",
        "x_trending": [],          # Xトレンドワード
        "youtube_trending": [],    # YouTube急上昇タイトル
        "cw_hot_categories": [],   # CW/Lancersで多い案件
        "notes": "",               # 自由メモ
    }


# ── 内部コンテンツ分析 ─────────────────────────────────────
def analyze_internal_content() -> dict:
    """自社コンテンツキューを分析してパフォーマンス傾向を把握"""
    x_queue_file = SESSIONS / "x_post_queue.json"
    x_extra_file = SESSIONS / "x_extra_posts.json"

    themes = {}
    if x_queue_file.exists():
        q = json.loads(x_queue_file.read_text())
        for v in q.values():
            text = v.get("text", "")
            for kw in ["高岡大仏", "瑞龍寺", "金屋町", "能作", "コロッケ",
                       "フリーランス", "副業", "AI", "Excel", "スプレッドシート",
                       "HiddenJapan", "旅行", "観光"]:
                if kw in text:
                    themes[kw] = themes.get(kw, 0) + 1

    top_themes = sorted(themes.items(), key=lambda x: x[1], reverse=True)[:5]
    return {"top_themes": top_themes, "total_posts": sum(themes.values())}


# ── 季節・カレンダートレンド推定 ───────────────────────────
def estimate_seasonal_trends() -> list[dict]:
    """日付・月から旬のトレンドを推定（知識ベース）"""
    month = datetime.now().month
    weekday = datetime.now().weekday()  # 0=月

    trends = []

    # 4-5月: GW・新生活・旅行シーズン
    if month in [4, 5]:
        trends += [
            {"type": "季節", "keyword": "GW旅行", "reason": "ゴールデンウィーク需要"},
            {"type": "季節", "keyword": "新生活 副業", "reason": "4月新生活スタート"},
            {"type": "季節", "keyword": "日帰り旅行 穴場", "reason": "GW混雑回避需要"},
        ]

    # 月曜: 副業・キャリア系が伸びやすい
    if weekday == 0:
        trends.append({"type": "曜日", "keyword": "副業 始め方", "reason": "月曜の仕事モチベ"})

    # 金曜: 旅行・週末外出系
    if weekday == 4:
        trends.append({"type": "曜日", "keyword": "週末旅行 近場", "reason": "金曜の旅行計画"})

    # 常時有効
    trends += [
        {"type": "定常", "keyword": "高岡市 穴場", "reason": "検索ボリューム安定"},
        {"type": "定常", "keyword": "フリーランス 確定申告", "reason": "年間需要あり"},
        {"type": "定常", "keyword": "HiddenJapan", "reason": "インバウンド増加中"},
    ]

    return trends


# ── 推奨アクション生成 ──────────────────────────────────────
def generate_recommendations(internal: dict, seasonal: list, manual: dict) -> dict:
    top_themes = [t[0] for t in internal["top_themes"]]
    manual_x = manual.get("x_trending", [])
    manual_yt = manual.get("youtube_trending", [])

    # CMO推奨（コンテンツ化）
    cmo = []
    for s in seasonal[:3]:
        cmo.append(f"「{s['keyword']}」をテーマに高岡コンテンツを作成（{s['reason']}）")
    if manual_yt:
        cmo.append(f"YouTube急上昇「{manual_yt[0]}」の高岡版Shortsを制作")

    # CSO推奨（案件応募）
    cso = [
        "データ入力・Excel作業案件を週5件応募（単価¥3,000〜¥15,000）",
        "ライティング案件（観光・副業ジャンル）に特化して応募",
    ]
    manual_cw = manual.get("cw_hot_categories", [])
    if manual_cw:
        cso.insert(0, f"今週の急募: 「{manual_cw[0]}」案件を優先応募")

    # CPO推奨（商品化）
    cpo = [
        "「高岡市日帰りモデルコース」PDFガイド（¥980）の制作",
        "「GW穴場旅行スポット10選」noteマガジン（¥500）",
    ]

    return {"CMOへ": cmo, "CSOへ": cso, "CPOへ": cpo}


# ── レポート生成 ───────────────────────────────────────────
def generate_report(internal: dict, seasonal: list, manual: dict, recs: dict) -> str:
    manual_updated = manual.get("updated", "未入力")
    lines = [
        f"# CRO トレンドレポート {TODAY}",
        f"生成: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "---",
        "",
        "## 自社コンテンツ傾向分析",
        f"総投稿数分析: {internal['total_posts']}件",
        "",
        "| テーマ | 投稿数 |",
        "|--------|--------|",
    ]
    for theme, count in internal["top_themes"]:
        lines.append(f"| {theme} | {count}本 |")

    lines += [
        "",
        "## 季節・カレンダートレンド推定",
        "",
        "| 種別 | キーワード | 根拠 |",
        "|------|-----------|------|",
    ]
    for t in seasonal:
        lines.append(f"| {t['type']} | {t['keyword']} | {t['reason']} |")

    lines += [
        "",
        f"## 手動入力トレンド（最終更新: {manual_updated}）",
        "",
        "> Macで実際のXトレンドを確認後、.sessions/manual_trends.json に入力してください",
        "",
    ]
    if manual.get("x_trending"):
        lines.append("**Xトレンド:**")
        for t in manual["x_trending"]:
            lines.append(f"- {t}")
    else:
        lines.append("*（未入力 — Mac側でXを確認して追加してください）*")

    lines += ["", "## 推奨アクション", ""]
    for role, actions in recs.items():
        lines.append(f"### {role}")
        for a in actions:
            lines.append(f"- {a}")
        lines.append("")

    lines += [
        "---",
        "",
        "## 手動トレンド入力方法",
        "",
        "Macで `zsh now` 実行後、以下を編集:",
        "```",
        "nano ~/agent-team/.sessions/manual_trends.json",
        "```",
        "",
        "```json",
        "{",
        '  "updated": "2026-04-30",',
        '  "x_trending": ["#トレンドワード1", "#トレンドワード2"],',
        '  "youtube_trending": ["急上昇動画タイトル1"],',
        '  "cw_hot_categories": ["データ入力", "SNS運用"],',
        '  "notes": "気づいたことを自由に"',
        "}",
        "```",
    ]
    return "\n".join(lines)


def run() -> dict:
    print("━" * 45)
    print("  CRO — トレンド調査")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("━" * 45)

    online = _internet_available()
    print(f"\n  接続状態: {'✅ オンライン（リアルデータ取得）' if online else '⚡ オフライン（内部分析モード）'}")

    print("\n  [1] 内部コンテンツ分析...")
    internal = analyze_internal_content()
    print(f"  トップテーマ: {[t[0] for t in internal['top_themes'][:3]]}")

    print("\n  [2] 季節トレンド推定...")
    seasonal = estimate_seasonal_trends()
    print(f"  推定トレンド: {len(seasonal)}件")

    print("\n  [3] 手動インプット確認...")
    manual = load_manual_trends()
    updated = manual.get("updated", "未入力")
    print(f"  最終更新: {updated}")

    print("\n  [4] 推奨アクション生成...")
    recs = generate_recommendations(internal, seasonal, manual)

    report = generate_report(internal, seasonal, manual, recs)
    out = OUTPUT_DIR / f"{TODAY}_trend_report.md"
    out.write_text(report, encoding="utf-8")

    json_out = OUTPUT_DIR / f"{TODAY}_trend_data.json"
    json_out.write_text(json.dumps({
        "date": TODAY,
        "top_themes": internal["top_themes"],
        "seasonal_trends": seasonal,
        "manual_trends": manual,
        "recommendations": recs,
    }, ensure_ascii=False, indent=2))

    print(f"\n  ✅ レポート保存: {out.name}")
    print("\n  【今週の推奨アクション】")
    for role, actions in recs.items():
        print(f"\n  {role}:")
        for a in actions[:2]:
            print(f"    • {a}")

    print("━" * 45)
    return recs


if __name__ == "__main__":
    run()
