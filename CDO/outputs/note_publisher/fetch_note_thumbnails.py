#!/usr/bin/env python3
"""note記事のサムネ画像を Pexels API（無料）から自動取得して thumbnails/ に保存する。

私(code)のコンテナはネット遮断だが **GitHub Actions はネット可** なのでそこで実行する。
→ 「フリー画像の手配」をクラウドで自動化し、note公開時に自動でサムネが付くようにする。

- 写真は Pexels（商用利用可・帰属任意・写真風＝オーナー方針に合致）。
- ドラえもん等の著作権キャラは検索語に含めない（場所/物/料理で写真風を引く）。
- 保存先: CDO/outputs/note_publisher/thumbnails/{記事stem}.jpg
  （.gitignore 済みフォルダだが、ワークフロー側で `git add -f` してコミットする）

必要: 環境変数 PEXELS_API_KEY（無料・https://www.pexels.com/api/ → リポジトリ Secrets に登録）

使い方:
  PEXELS_API_KEY=xxxx python3 CDO/outputs/note_publisher/fetch_note_thumbnails.py
  PEXELS_API_KEY=xxxx python3 CDO/outputs/note_publisher/fetch_note_thumbnails.py --force
  PEXELS_API_KEY=xxxx python3 CDO/outputs/note_publisher/fetch_note_thumbnails.py --filter 2026-06-09
"""
from __future__ import annotations

import os
import sys
import time
import json
import glob
import urllib.parse
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parents[2]
ARTICLES_DIR = REPO / "CMO" / "outputs"
THUMB_DIR = SCRIPT_DIR / "thumbnails"
KEY = os.environ.get("PEXELS_API_KEY")

# 日本語タイトル/ファイル名の部分一致 → Pexels検索語（具体的なものを先に置く）
RULES = [
    # 食
    ("かぶら寿司", "kabura sushi japanese food"), ("ます寿司", "japanese pressed sushi"),
    ("ホタルイカ", "squid seafood japan"), ("寒ぶり", "yellowtail fish sashimi"),
    ("ぶり大根", "simmered fish radish"), ("ぶり", "yellowtail fish"),
    ("とろろ昆布", "kelp seaweed"), ("昆布じめ", "sashimi kelp"), ("昆布", "kelp seaweed"),
    ("高岡コロッケ", "croquette food"), ("コロッケ", "croquette food"),
    ("白えび", "white shrimp sashimi"), ("げんげ", "japanese fish dish"),
    ("塩蔵わかめ", "wakame seaweed"), ("わかめ", "wakame seaweed"),
    ("べっこう", "japanese egg jelly food"), ("駅そば", "soba noodles bowl"),
    ("そば", "soba noodles"), ("かきもち", "rice crackers"), ("ばい貝", "whelk shellfish"),
    ("おでん", "oden hotpot"), ("氷見牛", "wagyu beef"), ("牛", "wagyu beef"),
    ("白えびの天かきあげ", "shrimp tempura"), ("唐揚", "fried chicken japanese"),
    ("大門素麺", "somen noodles"), ("山菜", "mountain vegetables wild"),
    ("かまぼこ", "japanese fish cake"), ("へしこ", "fermented fish"),
    ("五箇山豆腐", "tofu"), ("豆腐", "tofu"), ("薄氷", "japanese sweets wagashi"),
    ("和菓子", "japanese sweets wagashi"), ("黒造り", "squid dish"), ("いか", "squid"),
    ("うどん", "udon noodles"), ("地ビール", "craft beer glass"),
    ("地酒", "japanese sake"), ("酒", "japanese sake"), ("市場", "fish market japan"),
    ("ラーメン", "ramen bowl"), ("富山ブラック", "black soy ramen"),
    ("寿司", "japanese sushi"), ("冬大根", "daikon radish"), ("大根", "daikon radish"),
    # 文化・観光
    ("瑞龍寺", "japanese zen temple"), ("勝興寺", "japanese temple"), ("寺", "japanese temple"),
    ("御車山", "japanese festival float"), ("祭", "japanese festival"),
    ("高岡銅器", "bronze metal craft"), ("銅器", "bronze metal craft"),
    ("漆器", "japanese lacquerware"), ("大仏", "great buddha statue japan"),
    ("古城公園", "japanese castle park"), ("富山城", "japanese castle"), ("城", "japanese castle"),
    ("岩瀬", "japanese old merchant town"), ("山町筋", "japanese old townscape"),
    ("町並み", "japanese old townscape"), ("海王丸", "tall ship harbor"),
    ("新湊大橋", "harbor bridge"), ("合掌造り", "gassho thatched village japan"),
    ("五箇山", "gassho thatched village japan"), ("おとぎの森", "japanese park green"),
    ("ギャラリー", "art museum interior"), ("潮風", "seaside town japan"),
    # 自然・観光
    ("雨晴", "coast sea mountains japan"), ("立山", "snow mountains japan"),
    ("雪の大谷", "snow wall mountains"), ("アルペンルート", "snow mountains japan"),
    ("連峰", "mountain range snow japan"), ("チューリップ", "tulip field"),
    ("黒部峡谷", "mountain gorge railway"), ("トロッコ", "mountain railway gorge"),
    ("称名滝", "waterfall japan"), ("滝", "waterfall"),
    ("宇奈月温泉", "japanese hot spring onsen"), ("温泉", "japanese onsen hot spring"),
    ("古城", "japanese castle"),
    # 暮らし・文化史
    ("北陸新幹線", "shinkansen bullet train japan"), ("新幹線", "shinkansen bullet train"),
    ("持ち家", "japanese house living room"), ("広い家", "spacious house interior"),
    ("薬売り", "traditional medicine wooden box"), ("雪国", "snow town japan winter"),
    ("冬支度", "snow house winter japan"), ("置き薬", "wooden medicine box"),
    ("観光地に住", "japanese town daily life"),
    # 仕事・実務（フリーランス系は写真風のデスク/作業で統一）
    ("メール", "laptop email desk"), ("時給", "minimal desk laptop calculator"),
    ("値上げ", "laptop email writing desk"), ("値段", "notebook pen desk pricing"),
    ("見積", "documents desk laptop"), ("断る", "calm desk coffee notebook"),
    ("クレーム", "calm laptop desk tea"), ("休み方", "hammock rest window"),
    ("お金の分け方", "envelopes money calculator desk"), ("支出", "wallet calculator desk"),
    ("実績", "portfolio desk laptop"), ("口約束", "laptop email contract desk"),
    ("ディープワーク", "focused work desk laptop"), ("昼休み", "lunch break desk coffee"),
    ("予習", "planner notebook desk"), ("サブスク", "laptop subscriptions desk"),
    ("辞める基準", "calm desk window thinking"), ("孤独", "person working alone desk"),
    ("本", "books reading desk"), ("AIと働く", "laptop technology desk"),
    ("AIに5つ", "laptop technology desk"), ("請求書", "invoice laptop desk"),
    ("失敗", "notebook pen desk reflection"), ("営業しないで", "laptop desk calm work"),
    ("テンプレ", "spreadsheet laptop desk"), ("カレンダー", "calendar planner desk"),
    ("顧客の声", "notebook coffee desk"), ("会社を持てる", "laptop minimal workspace"),
    ("途中経過", "notebook charts desk"), ("個人発信", "laptop writing desk"),
    ("気力切れ", "calm desk window coffee"), ("月10万", "laptop desk work growth"),
]

FOOD_HINT = ("寿司", "ぶり", "コロッケ", "えび", "昆布", "そば", "おでん", "牛", "豆腐",
             "和菓子", "いか", "うどん", "ビール", "酒", "ラーメン", "大根", "わかめ",
             "べっこう", "かきもち", "貝", "へしこ", "かまぼこ", "山菜", "げんげ", "ホタルイカ")


def query_for(title: str, stem: str) -> str:
    hay = title + " " + stem
    for key, q in RULES:
        if key in hay:
            return q
    if any(h in hay for h in FOOD_HINT):
        return "japanese cuisine toyama"
    return "toyama japan landscape mountains"


def has_thumb(stem: str) -> bool:
    return any((THUMB_DIR / f"{stem}{e}").exists() for e in (".jpg", ".jpeg", ".png", ".webp"))


def extract_title(text: str, stem: str) -> str:
    import re
    # 注釈付き見出し「## タイトル案」等も拾えるよう .*? を許容（厳格形だと112/124止まりでサムネ精度が落ちる）
    m = re.search(r"##\s*タイトル.*?\n```\s*\n(.+?)\n```", text, re.S)
    if m:
        return m.group(1).strip().splitlines()[0]
    m2 = re.search(r"^\*\*タイトル[:：]\*\*\s*(.+)$", text, re.M)
    if m2:
        return m2.group(1).strip()
    return stem


def fetch_url(query: str):
    url = "https://api.pexels.com/v1/search?" + urllib.parse.urlencode(
        {"query": query, "orientation": "landscape", "per_page": 1, "size": "medium"})
    req = urllib.request.Request(url, headers={"Authorization": KEY})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    photos = data.get("photos") or []
    if not photos:
        return None
    src = photos[0]["src"]
    return src.get("large") or src.get("landscape") or src.get("original")


def main() -> None:
    if not KEY:
        sys.exit("PEXELS_API_KEY が未設定です。リポジトリ Secrets に登録してください（無料）。")
    force = "--force" in sys.argv
    flt = ""
    if "--filter" in sys.argv:
        flt = sys.argv[sys.argv.index("--filter") + 1]

    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(glob.glob(str(ARTICLES_DIR / "*note記事*.md")))
    ok = skip = miss = 0
    for f in files:
        p = Path(f)
        stem = p.stem
        if flt and flt not in p.name:
            continue
        if not force and has_thumb(stem):
            skip += 1
            continue
        title = extract_title(p.read_text(encoding="utf-8"), stem)
        q = query_for(title, stem)
        try:
            img = fetch_url(q)
            if not img:
                print(f"  no result: {stem} ({q})")
                miss += 1
                continue
            urllib.request.urlretrieve(img, THUMB_DIR / f"{stem}.jpg")
            print(f"  {stem}.jpg  <-  {q}")
            ok += 1
            time.sleep(0.4)  # APIに優しく
        except Exception as e:
            print(f"  skip {stem}: {e}")
            miss += 1
    print(f"\nfetched {ok} / skipped(existing) {skip} / missed {miss}  → {THUMB_DIR}")


if __name__ == "__main__":
    main()
