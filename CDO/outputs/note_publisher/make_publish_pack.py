#!/usr/bin/env python3
"""手動公開パックを生成する。

各note記事から〈タイトル／本文（貼るだけ）／タグ／note無料ギャラリー検索ワード〉を抽出し、
1ファイルにまとめる。オーナーは note で「タイトル貼る→本文貼る→見出し画像は
『記事にあう画像を選ぶ』で検索ワードを入れて選ぶ→公開」するだけ。サンプル画像不要・無料。

使い方:
  python3 make_publish_pack.py --filter 2026-06-09
  python3 make_publish_pack.py            # 全note記事
出力: CMO/outputs/<日付>_手動公開パック.md（filter指定時はその日付名）
"""
from __future__ import annotations
import re, sys, glob
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parents[2]
ARTICLES = REPO / "CMO" / "outputs"

# タイトル/本文の語 → noteギャラリー検索ワード（日本語・関連写真を引く・キャラ語は使わない）
KW = [
    ("かぶら寿司", "和食 発酵"), ("ます寿司", "寿司 駅弁"), ("ホタルイカ", "海 富山"),
    ("寒ぶり", "魚 刺身"), ("ぶり", "魚 刺身"), ("げんげ", "和食 魚"),
    ("昆布", "昆布 出汁"), ("塩蔵わかめ", "わかめ 海藻"), ("わかめ", "海藻"),
    ("高岡コロッケ", "コロッケ 揚げ物"), ("コロッケ", "コロッケ"), ("地酒", "日本酒"),
    ("べっこう", "和食 小鉢"), ("駅そば", "そば 蕎麦"), ("そば", "蕎麦"),
    ("かきもち", "和菓子 餅"), ("ばい貝", "貝 海鮮"), ("おでん", "おでん 鍋"),
    ("氷見牛", "牛肉 和牛"), ("白えび", "海老 海鮮"), ("寿司", "寿司"),
    ("ぶりしゃぶ", "鍋 料理"), ("山菜", "山菜 春"), ("かまぼこ", "かまぼこ"),
    ("瑞龍寺", "寺 日本"), ("勝興寺", "寺 日本"), ("御車山", "祭り 山車"),
    ("銅器", "金属 工芸"), ("漆器", "漆器 工芸"), ("大仏", "大仏"),
    ("富山城", "城 日本"), ("古城公園", "城 公園"), ("岩瀬", "古い町並み"),
    ("町並み", "古い町並み"), ("海王丸", "港 船"), ("新湊大橋", "橋 港"),
    ("合掌造り", "合掌造り 集落"), ("五箇山", "合掌造り 集落"),
    ("雨晴", "海 山 朝"), ("立山", "雪山 山脈"), ("雪の大谷", "雪 壁"),
    ("アルペンルート", "雪山"), ("連峰", "山脈 雪"), ("チューリップ", "チューリップ 花"),
    ("黒部峡谷", "渓谷 鉄道"), ("トロッコ", "渓谷 鉄道"), ("称名滝", "滝"),
    ("宇奈月温泉", "温泉"), ("温泉", "温泉"), ("北陸新幹線", "新幹線"),
    ("新幹線", "新幹線"), ("持ち家", "家 リビング"), ("薬売り", "和 古い"),
    ("雪国", "雪 町"), ("冬支度", "雪 家"), ("立山連峰", "雪山 山脈"),
    # 実務/暮らし系は写真風のデスク/落ち着いた風景
    ("時給", "デスク ノート"), ("値上げ", "デスク パソコン"), ("値段", "ノート ペン"),
    ("見積", "書類 デスク"), ("断る", "コーヒー デスク"), ("クレーム", "デスク 静か"),
    ("休み方", "休息 窓"), ("支出", "電卓 ノート"), ("実績", "デスク ノート"),
    ("口約束", "パソコン デスク"), ("ディープワーク", "集中 デスク"),
    ("メール", "パソコン デスク"), ("ディープ", "デスク"), ("本", "読書 本"),
    ("AI", "パソコン デスク"), ("会社", "デスク オフィス"), ("失敗", "ノート デスク"),
]


def kw_for(title: str, stem: str) -> str:
    hay = title + " " + stem
    for k, q in KW:
        if k in hay:
            return q
    return "富山 風景"


def extract(text: str, stem: str):
    mt = re.search(r"##\s*タイトル\s*\n```\s*\n(.+?)\n```", text, re.S)
    title = mt.group(1).strip().splitlines()[0] if mt else stem
    mb = re.search(r"##\s*本文\s*\n```\s*\n(.+?)\n```", text, re.S)
    body = mb.group(1).strip() if mb else ""
    mh = re.search(r"##\s*ハッシュタグ\s*\n```\s*\n(.+?)\n```", text, re.S)
    tags = " ".join(re.findall(r"#\S+", mh.group(1))) if mh else ""
    return title, body, tags


def main():
    flt = ""
    if "--filter" in sys.argv:
        flt = sys.argv[sys.argv.index("--filter") + 1]
    files = sorted(glob.glob(str(ARTICLES / "*note記事*.md")))
    files = [f for f in files if (not flt or flt in Path(f).name)]
    if not files:
        sys.exit("対象記事なし")
    out_name = f"{flt}_手動公開パック.md" if flt else "手動公開パック_全記事.md"
    out = ARTICLES / out_name
    L = [f"# 手動公開パック（{flt or '全記事'}）\n",
         "noteでの手順（1記事ずつ・無料）：",
         "1. 新規記事 → **タイトル**を貼る → **本文**を貼る",
         "2. 見出し画像＝「画像を追加」→**記事にあう画像を選ぶ**（みんなのフォトギャラリー・無料）",
         "   → 下の【サムネ検索ワード】で検索して好きな写真を選ぶ",
         "3. ハッシュタグを入れて **公開**\n", "---\n"]
    for i, f in enumerate(sorted(files), 1):
        stem = Path(f).stem
        title, body, tags = extract(Path(f).read_text(encoding="utf-8"), stem)
        kw = kw_for(title, stem)
        L.append(f"## {i}. {title}")
        L.append(f"- 🔎 **サムネ検索ワード**：`{kw}`")
        L.append(f"- 🏷 タグ：`{tags}`")
        L.append("**▼タイトル（コピペ）**")
        L.append("```\n" + title + "\n```")
        L.append("**▼本文（コピペ）**")
        L.append("```\n" + body + "\n```\n")
        L.append("---\n")
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"✅ 生成: {out}  （{len(files)}本）")


if __name__ == "__main__":
    main()
