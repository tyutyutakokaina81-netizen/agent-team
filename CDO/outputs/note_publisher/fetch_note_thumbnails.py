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

# 日本語タイトル/ファイル名の部分一致 → Pexels/Wikimedia検索語（具体的なものを先に置く＝先勝ち）
RULES = [
    # 2026-07 新分野・リサーチ記事の追加（default「富山の山写真」への誤落ちを防ぐ＝A5/誤サムネ根治）
    ("七輪", "shichirin charcoal grill japan"),
    ("炭火", "shichirin charcoal grill japan"),
    ("高岡で食べる", "sushi japan"),
    ("散居村", "satoyama rice field farmhouse japan"),
    ("砺波平野", "satoyama rice field farmhouse japan"),
    ("屋敷林", "farmhouse trees rural japan"),
    ("北アルプス", "Tateyama mountain range snow japan"),
    ("富山の水", "clear mountain stream water japan"),
    ("名水", "clear mountain stream water japan"),
    ("富山湾", "Toyama bay sea coast japan"),
    ("魚の宝庫", "fish market seafood japan"),
    # 無人販売所/直売所は「夏野菜」より先に置く（本記事タイトルに両方含む→棚の固有画像を優先取得・2026-07-30追加）
    ("無人販売所", "roadside farm vegetable stand japan"),
    ("無人販売", "roadside farm vegetable stand japan"),
    ("直売所", "roadside farm vegetable stand japan"),
    ("庭の畑", "summer vegetables harvest basket"),
    ("家庭菜園", "summer vegetables harvest basket"),
    ("夏野菜", "summer vegetables harvest basket"),
    ("採れたて", "summer vegetables harvest basket"),
    ("本物と静けさ", "Zuiryuji temple Takaoka japan"),
    ("高岡に何を", "Takaoka Daibutsu great buddha japan"),
    ("求めて", "Takaoka Daibutsu great buddha japan"),
    ("砂糖", "japanese home cooking kitchen"),
    # 家庭料理の野菜（夏野菜/常備野菜シリーズ・default「山写真」への誤落ち防止＝A5/誤サムネ根治・2026-07-29追加）
    ("焼きなす", "grilled eggplant japanese food"), ("なす", "eggplant dish japanese food"),
    ("しそ", "shiso perilla green leaves"), ("大葉", "shiso perilla green leaves"),
    ("もろきゅう", "cucumber miso japanese food"), ("たたききゅうり", "smashed cucumber dish"),
    ("きゅうり", "cucumber fresh vegetable food"),
    ("肉じゃが", "nikujaga potato stew japanese"), ("ポテトサラダ", "potato salad food"),
    ("じゃがバター", "baked potato butter"), ("新じゃが", "boiled small potatoes food"),
    ("じゃがいも", "potato dish japanese food"),
    ("とうもろこし", "grilled corn on the cob food"), ("とうきび", "grilled corn on the cob food"), ("コーン", "corn on the cob food"),
    ("みょうが", "myoga ginger bud"), ("茗荷", "myoga ginger bud"),
    ("お中元", "japanese gift box noshi"), ("中元", "japanese gift box noshi"),
    ("トマト", "fresh tomato food"), ("ピーマン", "green bell pepper vegetable"),
    ("かぼちゃ", "kabocha squash japanese"), ("枝豆", "edamame soybeans"),
    ("梅干し", "umeboshi pickled plum"), ("梅仕事", "umeboshi pickled plum drying"), ("土用干し", "umeboshi drying sun basket"),
    ("打ち水", "water sprinkling wet stone street japan"), ("うちみず", "water sprinkling wet stone street japan"),
    ("ところてん", "tokoroten jelly noodles bowl"), ("心太", "tokoroten jelly noodles bowl"),
    ("ラジオ体操", "morning exercise park people"), ("体操", "morning exercise group"),
    ("冷やし中華", "hiyashi chuka cold noodles"), ("冷し中華", "hiyashi chuka cold noodles"),
    ("麦茶", "barley tea glass pitcher"), ("むぎ茶", "barley tea glass pitcher"),
    ("甘酒", "amazake rice drink glass"), ("冷やし甘酒", "amazake rice drink glass"),
    ("セミ", "cicada tree summer"), ("蝉", "cicada tree summer"),
    ("蚊取り線香", "mosquito coil incense smoke"), ("蚊遣り", "mosquito coil incense"), ("蚊取", "mosquito coil incense"),
    ("味噌汁", "miso soup japanese"), ("漬物", "japanese pickles tsukemono"),
    ("浅漬け", "japanese pickles tsukemono"),
    # 過去記事QCで判明した誤サムネ(山夕景/無関係)の穴埋め・2026-07-29②追加（具体名を先に＝黒部ダムは黒部峡谷より前）
    ("黒部ダム", "kurobe dam concrete water reservoir japan"), ("ダム", "concrete dam reservoir water"),
    ("西瓜", "watermelon fruit"), ("スイカ", "watermelon fruit"), ("すいか", "watermelon fruit"),
    ("カレー", "curry rice japanese food"),
    ("栃餅", "mochi rice cake japanese"), ("とち餅", "mochi rice cake japanese"),
    ("県美術館", "modern art museum architecture"), ("美術館", "modern art museum architecture"),
    ("TAD", "modern art museum architecture"),
    ("風鈴", "japanese wind chime hanging"), ("ホタル", "firefly night glow"), ("蛍", "firefly night glow"),
    ("おわら", "japanese folk dance festival evening"), ("風の盆", "japanese folk dance festival evening"),
    ("木彫り", "wood carving craft chisel"), ("井波", "wood carving craft workshop"),
    # 食（実写ヒット率を上げる追加分・具体的なものを先に）
    ("紅ずわい", "red snow crab"), ("ずわい", "snow crab"), ("かに", "snow crab seafood"),
    ("バイ貝", "whelk shellfish"), ("フクラギ", "yellowtail fish"), ("フクラギ", "yellowtail fish"),
    ("たら汁", "cod fish soup"), ("鮎", "ayu sweetfish grilled"), ("よごし", "japanese vegetable side dish"),
    ("ノドグロ", "blackthroat seaperch fish"), ("ほたるいか", "firefly squid"),
    # 場所（追加分）
    ("蜃気楼", "sea horizon calm bay"), ("内川", "canal fishing town japan"),
    ("金屋町", "japanese old townscape"), ("万葉線", "tram streetcar japan city"),
    ("路面電車", "tram streetcar japan city"), ("庄川峡", "river gorge mountains japan"),
    ("遊覧船", "sightseeing boat river gorge"), ("環水", "canal park waterfront japan"),
    ("富岩運河", "canal park waterfront japan"), ("伏木", "japanese old port town"),
    ("市場散歩", "fish market japan morning"), ("早朝散歩", "coast sea mountains japan"),
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
    # 車（※「路面電車/トロッコ/御車山/車窓」等の"電車/祭"系と衝突しないよう固有トークンで限定）
    ("車内", "car interior dashboard"), ("第二の部屋", "car parked outdoor"),
    ("車社会", "cars parked lot"), ("一人一台", "cars parked lot"),
    # 海・夏（海水浴＝砂浜/海の実写へ。魚介記事の"富山湾"より前に置くと魚に寄るので固有トークン限定）
    ("海水浴", "japan beach sea summer"), ("海で泳ぐ", "japan beach sea summer"),
    ("花火大会", "japanese fireworks festival night"), ("花火", "japanese fireworks festival night"),
    ("川遊び", "mountain stream rocks clear water green"), ("川で遊", "mountain stream rocks clear water green"),
    ("火を使わない", "somen noodles cold bowl japanese"), ("そうめん", "somen noodles cold bowl japanese"),
    ("鱒寿司", "salmon sushi rice japanese"), ("ますのすし", "salmon sushi rice japanese"),
    ("かき氷", "kakigori shaved ice dessert"),
    ("お盆", "bon odori festival lanterns night"), ("盆踊り", "bon odori festival lanterns night"),
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
    # ★catch-all（RULES最終・料理/レシピ系は山写真でなく家庭料理写真へ寄せる＝A5誤サムネ防止・2026-07-29）
    ("料理", "japanese home cooking dish"), ("レシピ", "japanese home cooking dish"),
    ("食べ切る", "japanese home cooking dish"), ("食べ方", "japanese home cooking dish"),
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


def load_verified() -> set:
    """owner確認済みサムネのallowlist(_verified.txt)。ここに載るstemは自動取得で絶対に上書きしない。"""
    f = THUMB_DIR / "_verified.txt"
    try:
        return {ln.strip() for ln in f.read_text(encoding="utf-8").splitlines()
                if ln.strip() and not ln.strip().startswith("#")}
    except Exception:
        return set()


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
    verified = load_verified()
    files = sorted(glob.glob(str(ARTICLES_DIR / "*note記事*.md")))
    ok = skip = miss = 0
    for f in files:
        p = Path(f)
        stem = p.stem
        if flt and flt not in p.name:
            continue
        if stem in verified:      # owner確認済み=絶対に上書きしない
            skip += 1
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
