#!/usr/bin/env python3
"""地名の正本。**ファイル名に、記事に出てこない地名が入っていないか**を判定する。

なぜ1か所にまとめるか（2026-11-19）:
  同じ判定が**2か所**にあった。
  - `ops/check_requirements.py` の **R30**＝**採用したあと**に「記事に出てこない地名が
    ファイル名にあるか」を数える（＝事後）。
  - `fetch_thumbnails_wikimedia.py` の `_place_mismatch()`＝**クエリ**が土地を名乗るかしか見ず、
    **取れてきたファイル名は見ない**。
  その結果、**取得は通って、採用の直前に人が目で落とす**ことを繰り返していた。
  却下台帳 351件のうち、**ファイル名の町名・駅名・施設名が理由のものが約30件**ある
  （名掛丁／大字田吉947番地／Akasaka／八尾町西神通／生麦駅／三井野原駅／白沙荘／
   高尾山／船橋競馬場／道後温泉／金閣寺／銀閣寺／春日部／郡山宿…）。
  **R30 が後ろでやっている判定を、取得の時点でやれば、人が見る前に落ちる。**

  ★R30 の地名リストは 2026-09-21 に一度「手で書いた31語しかなく、新潟・福井・福島・千葉が
    抜けていた」という失敗をしている。**思いついた地名を並べる作りは、思いつかなかった地名を
    永久に見逃す**ので、47都道府県を漏れなく、ローマ字と対で持つ。
  ※**富山は地元なので入れない**（富山の記事に富山の地名が入るのは当然）。
"""
from __future__ import annotations

# (漢字, ローマ字) の対。対で持つのは、**ファイル名は英語、本文は漢字**で書かれるため。
# 2026-11-13 の失敗＝対の相手が分からず、`"nagano" in 本文` が永久に偽になっていた
# （おやき＝File:Nozawana-Oyaki-Nagano.JPG／本文に「長野」が14回あるのに BROKEN になった）。
PREF_PAIRS = [
    ("北海道", "hokkaido"), ("青森", "aomori"), ("岩手", "iwate"), ("宮城", "miyagi"),
    ("秋田", "akita"), ("山形", "yamagata"), ("福島", "fukushima"), ("茨城", "ibaraki"),
    ("栃木", "tochigi"), ("群馬", "gunma"), ("埼玉", "saitama"), ("千葉", "chiba"),
    ("東京", "tokyo"), ("神奈川", "kanagawa"), ("新潟", "niigata"), ("石川", "ishikawa"),
    ("福井", "fukui"), ("山梨", "yamanashi"), ("長野", "nagano"), ("岐阜", "gifu"),
    ("静岡", "shizuoka"), ("愛知", "aichi"), ("三重", "mie"), ("滋賀", "shiga"),
    ("京都", "kyoto"), ("大阪", "osaka"), ("兵庫", "hyogo"), ("奈良", "nara"),
    ("和歌山", "wakayama"), ("鳥取", "tottori"), ("島根", "shimane"), ("岡山", "okayama"),
    ("広島", "hiroshima"), ("山口", "yamaguchi"), ("徳島", "tokushima"), ("香川", "kagawa"),
    ("愛媛", "ehime"), ("高知", "kochi"), ("福岡", "fukuoka"), ("佐賀", "saga"),
    ("長崎", "nagasaki"), ("熊本", "kumamoto"), ("大分", "oita"), ("宮崎", "miyazaki"),
    ("鹿児島", "kagoshima"), ("沖縄", "okinawa"),
]   # ※富山は地元なので入れない

# 都道府県名を名乗らない有名地・施設名（見つけ次第足す）
EXTRA_PLACES = [
    "kobe", "kanazawa", "nagoya", "kamakura", "sendai", "yokohama", "nikko", "hakone",
    "meiji-mura", "harajuku", "yuzawa", "katori", "echizen", "yokosuka",
    "神戸", "金沢", "名古屋", "鎌倉", "横浜", "日光", "箱根", "原宿", "湯沢", "香取", "越前",
    "江戸東京", "横須賀", "大山千枚田", "鳴門", "naruto",
    # 2026-09-24: 川の名前も土地を名乗る。朝霧に「只見川の川霧」（福島/新潟）を採用した。
    "只見", "tadami",
    # ★2026-11-19 追加: 却下台帳から、実際に落とした固有名を拾って足した。
    #   「見つけ次第足す」運用なので、**落としたら必ずここに書く**。
    "春日部", "府中", "くらやみ祭", "郡山宿", "沼津", "高尾山", "船橋競馬場",
    "道後温泉", "生麦", "三井野原", "木次線", "名掛丁", "八尾町", "白沙荘",
    "akasaka", "赤坂", "eccleshall", "guildford", "dülmen", "dulmen", "apia",
]

ALL_PLACES = [x for pair in PREF_PAIRS for x in pair] + EXTRA_PLACES

# 漢字 ⇔ ローマ字 の相互参照
PAIR = {}
for _k, _r in PREF_PAIRS:
    PAIR.setdefault(_k, set()).add(_r)
    PAIR.setdefault(_r, set()).add(_k)


def places_in(filename: str) -> list:
    """ファイル名に含まれる地名を返す（小文字化して照合）。"""
    f = (filename or "").lower()
    if not f:
        return []
    return [x for x in ALL_PLACES if x in f]


def is_disclosed(found, stem: str = "", body: str = "") -> bool:
    """その地名が**記事の側で開示されているか**。

    開示のされ方は2通りある。
      ① 地名をそのまま書く（記事名か本文に出てくる）
      ② **「※撮影地は県外」のように地名を出さずに断る**
    ②を見ないと、**ちゃんと開示している記事まで落としてしまう**
    （消雪パイプ＝「※撮影地は新潟」／さつまいも＝「※撮影地は県外」）。
    """
    if not found:
        return True
    st = stem or ""
    bd = body or ""
    lb = bd.lower()
    if any(x in st for x in found):
        return True
    if any(x in bd or x in lb for x in found):
        return True
    # 漢字⇔ローマ字の対でも照合する（ファイル名は英語、本文は漢字）
    for x in found:
        for q in PAIR.get(x, ()):
            if q in bd or q.lower() in lb:
                return True
    return "撮影地" in bd


def mismatched_place(filename: str, stem: str = "", body: str = ""):
    """**記事に出てこない地名**がファイル名にあれば、その最初の1つを返す。無ければ None。"""
    found = places_in(filename)
    if not found or is_disclosed(found, stem, body):
        return None
    return found[0]
