#!/usr/bin/env python3
"""note記事のサムネを Wikimedia Commons（キー不要・無料・実写/CC）から自動取得して thumbnails/ に保存。

owner方針(2026-06-30)：自前AI画像(Pollinations)は荒い→使わない。**無料の実写を自動で**入れる。
- Wikimedia Commons API はキー不要・無料・レート制限が緩く、量産に向く（Openverse匿名は5req/時で不可）。
- 検索語は fetch_note_thumbnails.py の query_for()（日本語題材→英語写真検索語の対応表）を流用。
- 著作権キャラ(ドラえもん等)は query_for が場所/物/料理の語に寄せるため写り込まない。
- 取得画像は CC/パブリックドメイン等（Commons）。**クレジット表記が要る場合がある**点は運用で留意。
- 保存先: thumbnails/{stem}.jpg（.gitignore 済→ワークフローが git add -f）＋ _provenance.json に "wikimedia" 記録。
- provenance に good backend(openai/gemini/pollinations/wikimedia/pexels)で記録済みの記事はスキップ（自己修復・増分）。

使い方:
  python3 fetch_thumbnails_wikimedia.py                # 不足/素性不明のみ
  python3 fetch_thumbnails_wikimedia.py --force        # 全件取り直し
  python3 fetch_thumbnails_wikimedia.py --filter 2026-06-09
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from fetch_note_thumbnails import query_for, extract_title  # 検索語生成を流用

REPO = SCRIPT_DIR.parents[2]
ARTICLES_DIR = REPO / "CMO" / "outputs"
THUMB_DIR = SCRIPT_DIR / "thumbnails"
PROV_FILE = THUMB_DIR / "_provenance.json"
VERIFIED_FILE = THUMB_DIR / "_verified.txt"
NO_AUTO_FILE = THUMB_DIR / "_no_auto.txt"   # 意図的に無サムネ（誤サムネより無サムネが正）
GOOD_BACKENDS = {"openai", "gemini", "pollinations", "wikimedia", "pexels"}
MIN_IMAGE_BYTES = 8000
UA = "toyama-guide-thumbnailer/1.0 (https://github.com/tyutyutakokaina81-netizen/agent-team; free real photos)"
API = "https://commons.wikimedia.org/w/api.php"

# 2026-07-30 概念語(温泉/川/そうめん/鱒寿司 等)は英語検索だと Commons が別物(海外の地質/会社ビル/春の桜川)を
# 返しやすい。Commons は日本語タグの実写も多いので、これらは「日本語＋補助語」で先に検索し、
# JP該当stemは英語フォールバックしない（英語だと別物を拾うため）。値をリストにすると順に試す。
# 単語で検索する（Commons全文検索は複数語がAND寄りで0件になりやすい＝前回の失敗要因）。
JP_QUERY = [
    ("日帰り温泉", "露天風呂"), ("温泉", "露天風呂"),
    ("川遊び", "渓流"), ("川で遊", "渓流"),
    ("火を使わない", "そうめん"), ("そうめん", "そうめん"),
    ("鱒寿司", "ますのすし"), ("ますのすし", "ますのすし"),
    ("花火大会", "花火"), ("海水浴", "海水浴"),
    ("お盆", "夏祭り"), ("盆踊り", "夏祭り"),
    ("七夕", "七夕"), ("たなばた", "七夕"),
    ("線香花火", "線香花火"),
    ("金魚すくい", "金魚すくい"), ("金魚", "金魚"),
    ("朝顔", "アサガオ"), ("あさがお", "アサガオ"),
    ("灯籠流し", "灯籠流し"), ("精霊流し", "灯籠流し"),
    ("夏の魚", "刺身"), ("漬け丼", "海鮮丼"), ("南蛮漬け", "南蛮漬け"),
    ("うなぎ", "蒲焼"), ("土用の丑", "蒲焼"), ("鰻", "蒲焼"),
    ("みたらし団子", "みたらし団子"), ("みたらし", "みたらし団子"), ("焼き団子", "みたらし団子"),
    ("枝豆", "枝豆"), ("えだまめ", "枝豆"),
    ("スイカ", "スイカ"), ("すいか", "スイカ"), ("西瓜", "スイカ"),
    ("入道雲", "入道雲"), ("夕立", "入道雲"), ("積乱雲", "積乱雲"),
    ("クラフトコーラ", "クラフトコーラ"), ("コーラ", "コーラ"),
    ("鮎", "鮎"), ("あゆ", "鮎"), ("鮎の塩焼き", "鮎"),
    ("冷ややっこ", "冷奴"), ("冷奴", "冷奴"),
    ("扇風機", "扇風機"),
    ("桃", "桃"), ("もも", "桃"),
    ("ざるそば", "蕎麦"), ("そば", "蕎麦"),
    ("星空", "天の川"), ("天の川", "天の川"), ("夜空", "天の川"),
    ("蚊帳", "蚊帳"),
    ("昆布締め", "昆布締め"), ("牛の昆布締め", "昆布締め"),
    ("冷や汁", "冷や汁"), ("冷汁", "冷や汁"),
    ("ラムネ", "ラムネ"),
    ("カブトムシ", "カブトムシ"), ("かぶとむし", "カブトムシ"), ("兜虫", "カブトムシ"),
    ("ゴーヤチャンプルー", "ゴーヤチャンプルー"), ("ゴーヤ", "ゴーヤチャンプルー"),
    ("わらび餅", "わらび餅"), ("わらびもち", "わらび餅"),
    ("夕焼け", "夕焼け"), ("夕日", "夕焼け"), ("夕陽", "夕焼け"),
    ("天ぷら", "天ぷら"), ("天麩羅", "天ぷら"),
    # 新米は英語句(freshly cooked white rice bowl japan)だとCommonsが0件(実測 pages:12/img:0)。
    # Commonsは日本語タグの食写真が豊富なので日本語単語で引く。田んぼより前に置く(新米=米飯の写真)。
    # 2026-09-07 R2の未取得11本を「記事固有の語」で解消する（汎用フォールバックを廃止したため、
    # 対応表に無い題材は無サムネになる＝ここに記事ごとに違う語を足すのが唯一の増やし方）。
    # 同じ語を複数記事に割り当てると同一画像が配られてR2d(フォールバック汚染)になるので、必ず別語にする。
    ("彼岸花", "ヒガンバナ"), ("曼珠沙華", "ヒガンバナ"),
    # 2026-09-07 目視verifyで不合格だった語を差し替え（何がどう外れたかを残す）:
    #   中秋の名月→画面の大半が黒い満月／稲穂→シャーレの籾の標本／水道水→蛇口の水を飲む猫
    #   田んぼ→東南アジアの水田（少年と牛）／弥陀ヶ原→ホテルの外観／雨晴海岸→曇天の灰色の岩場
    # 十五夜: 中秋の名月→ほぼ黒い満月／月見団子→黒ごま団子（月見の絵にならない）と2回外した。
    # 3度目は日本の秋を一目で示す「ススキ」で引く。田んぼ: 田んぼ→東南アジア／稲刈り→海外らしき手刈りと
    # 2回外したので、日本固有の「はさ掛け」で引く。これで外れたら _no_auto に落とす。
    # 2026-09-10 の新規2本。いずれも日本固有の語で、海外の同名物に流れにくい。
    # 2026-09-11 の新規2本。なめこ=日本のきのこ／防災行政無線=日本固有の設備語で、海外の同名物に流れにくい。
    # 「なめこ」→パック入りの大きめの個体（本文「小さくて」と不一致）／「なめこ汁」→Commonsに0件、
    # と2回外した。カタカナ表記は別の候補（原木に生えた状態など）が上位に来る可能性があるので3度目はこれ。
    # これでも外れたら「なめこ」に戻し、本文の「小さくて」の方を実物に合わせて直す（写真に合わせて記事を直す）。
    # 2026-09-12 の新規2本。候補リスト方式（外れたら次の語）を最初から使う。
    # 1巡目の結果を反映して候補順を組み直した:
    #   焼き芋「焼き芋」→ 韓国の군고구마(ライセンスも kr)。日本語表記の候補を先に来させる。
    #   紅葉「ナナカマド」→ オーストリアの**緑の**ナナカマド＝紅葉していない。主題語(紅葉)を先頭へ。
    # 2026-09-13 の新規2本。最初から候補リストで。
    # 2026-09-14 の新規2本。おはぎ=日本語表記を先頭に（"botamochi"等のローマ字表記で海外の別菓子に
    # 流れないよう、かな表記→漢字表記の順）。仏壇/神棚は日本固有の語なので誤流出しにくいが、
    # 「仏壇」単体だと寺院の内陣写真が混ざりうるので「家庭 仏壇」を先に置く。
    # 1巡目「おはぎ」→ 和菓子店の作業場（人物が写り込み・「丹波おはぎ」の看板＝画面内に富山以外の
    # 地域名が出る・主題のおはぎは手前のトレイに小さく写るだけ）で不合格。食べもの単体の写真を狙って
    # 「おはぎ」を候補から外し、同義語から引き直す。
    # 2026-09-15 の新規2本。最初から候補リストで。
    # 里芋: 「里芋」だけだと調理済みの煮物が上位に来る可能性があるので、掘り出した状態を狙う。
    # 用水路: 「用水路」は日本固有語。ダム・河川の大型構造物に流れないよう住宅地側の語を後ろに置く。
    # 1巡目: 「サトイモ」→**里芋の葉**（海外撮影・記事は土の中の芋の話）／「用水路」→**Pont du Gard**
    # ＝フランスのローマ水道橋。いずれも _japan_score 0 の候補が「並べ替えられただけ」で採用された。
    # 0点足切りを入れたうえで、日本語の語彙に寄せた候補に組み替える。
    # 2巡目: 里芋は**0点足切りで全滅＝無サムネ**（設計どおり）。用水路は日本の用水路が取れたが
    # **水を抜いて浚渫中**の写真で、記事の主張「速い水が流れている」と逆だった。3巡目は語を替える。
    ("里芋", ["里芋", "サトイモ", "芋煮", "里芋 収穫"]),
    ("親芋", ["里芋", "サトイモ"]),
    ("用水路", ["用水路", "疏水", "用水路 日本", "農業用水路"]),
    ("速い水が流れている", ["用水路", "疏水"]),
    ("おはぎ", ["ぼたもち", "牡丹餅", "御萩", "あんころ餅"]), ("ぼたもち", ["ぼたもち", "牡丹餅"]),
    # 1巡目「仏壇」で取れた金仏壇は、脇掛が九字名号＝**宗派が読み取れる荘厳**だった（CQO中1）。
    # 本文は「うちの居間には仏壇がある」＝自宅の話なので、読者には筆者の家の宗派として読まれる。
    # A4（オーナーの属性を特定させない）の趣旨から、宗派の読み取れない神棚側へ振り替える。
    # ※神棚も神札に社名が出ると寺社名＝A4に触れるため、目視verifyで札の文字を必ず確認すること。
    ("仏壇", ["神棚", "神棚 家庭", "仏壇 扉"]), ("神棚", ["神棚", "神棚 家庭"]),
    ("二つの祈る場所", ["神棚", "神棚 家庭"]),
    ("秋刀魚", ["サンマの塩焼き", "秋刀魚", "サンマ"]), ("さんま", ["サンマの塩焼き", "秋刀魚"]),
    ("水力発電", ["水力発電所", "発電用ダム", "水力発電"]), ("冬の雪でできている", ["水力発電所", "発電用ダム"]),
    ("焼き芋", ["石焼き芋", "焼き芋", "サツマイモ"]), ("さつまいも", ["石焼き芋", "焼き芋", "サツマイモ"]),
    ("立山の紅葉", ["立山 紅葉", "草紅葉", "ナナカマド 紅葉", "高山 紅葉"]),
    ("日本でいちばん早い秋", ["立山 紅葉", "草紅葉", "高山 紅葉"]),
    ("なめこ", ["ナメコ", "なめこ"]), ("ナメコ", ["ナメコ", "なめこ"]),
    ("夕方のチャイム", "防災行政無線"), ("スピーカーが鳴る", "防災行政無線"), ("防災無線", "防災行政無線"),
    ("ぎんなん", "ぎんなん"), ("銀杏", "ぎんなん"),
    ("消雪パイプ", "消雪パイプ"), ("路面から水", "消雪パイプ"),
    ("十五夜", "ススキ"), ("お月見", "ススキ"), ("名月", "ススキ"),
    ("緑から金色", "はさ掛け"), ("収穫前", "はさ掛け"),
    # 2026-09-07 追加: 通信社透かし(FARS)と海外開催の日本祭りを拾っていた2本。名前ガードを入れたうえで再取得する。
    ("ラジオ体操", "ラジオ体操"),
    ("帰省と祭り", "盆踊り"), ("祭りのサイクル", "盆踊り"),
    ("干し柿", "干し柿"), ("ころ柿", "干し柿"), ("渋柿", "干し柿"),
    ("初冠雪", "立山連峰"), ("冠雪", "立山連峰"),
    ("標高で涼しさ", "室堂"),
    ("水道水", "黒部川"),
    ("完璧ガイド", "氷見線"), ("2日で巡る", "氷見線"),
    ("港町の朝", "氷見漁港"),
    ("港町と古都", "瑞龍寺"),
    ("江戸から昭和", "高岡大仏"),
    ("海と山を一日", "富山湾"),
    ("虫の声", "スズムシ"), ("鈴虫", "スズムシ"), ("秋の虫", "スズムシ"),
    ("栗ご飯", "栗ご飯"), ("栗", "栗"),
    ("新米", "白米"), ("白米", "白米"),
    ("田んぼ", "田んぼ"), ("稲", "田んぼ"), ("水田", "田んぼ"),
    ("たこ焼き", "たこ焼き"), ("たこ焼", "たこ焼き"),
    ("麦わら帽子", "麦わら帽子"), ("麦藁帽子", "麦わら帽子"),
    ("焼きそば", "焼きそば"), ("焼そば", "焼きそば"),
    ("うちわ", "うちわ"), ("団扇", "うちわ"),
    ("獅子舞", "獅子舞"), ("秋祭り", "獅子舞"),
    ("おにぎり", "おにぎり"), ("塩むすび", "おにぎり"), ("お握り", "おにぎり"),
    ("ビーチサンダル", "ビーチサンダル"), ("サンダル", "ビーチサンダル"),
    ("あんみつ", "あんみつ"), ("餡蜜", "あんみつ"),
    ("メロン", "メロン"),
    ("ひまわり", "ひまわり"), ("向日葵", "ひまわり"),
    ("名水", "湧水"), ("湧き水", "湧水"), ("湧水", "湧水"),
    # 2026-08-02 8/1の暮らし/食題材＝英語検索だとCommonsが別物/0件になりやすい→日本語単語で先に検索
    ("蚊取り線香", "蚊取り線香"), ("蚊遣り", "蚊遣り豚"),
    ("麦茶", "麦茶"),
    ("風鈴", "風鈴"),
    ("冷やし甘酒", "甘酒"), ("甘酒", "甘酒"),
    ("梅干し", "梅干し"), ("梅仕事", "梅干し"), ("土用干し", "梅干し"),
    ("打ち水", "打ち水"),
    ("ところてん", "ところてん"), ("心太", "ところてん"),
    ("冷やし中華", "冷やし中華"),
    ("とうもろこし", "とうもろこし"),
    ("みょうが", "ミョウガ"), ("茗荷", "ミョウガ"),
    ("お中元", "お中元"), ("中元", "お中元"),
    ("オクラ", "オクラ"), ("すだれ", "簾"), ("よしず", "葦簀"),
    # 2026-08-16 ストック2000字化に伴うサムネ拡充（owner「サムネもつくって」）。
    # 画像化できる題材のみ追加。人物/情感で誤取得しやすい題材（高校野球/昼寝/草むしり/日焼け/
    # 行水/水鉄砲/汗/寝苦しい夜/怪談/ひとり仕事）は無サムネ維持（誤サムネより無サムネ・code目視で最終判断）。
    ("氷見うどん", "うどん"), ("うどん", "うどん"),
    ("梅雨", "紫陽花"), ("あじさい", "紫陽花"), ("紫陽花", "紫陽花"),
    ("夏の終わり", "ススキ"), ("ススキ", "ススキ"),
    ("浴衣", "浴衣"),
    ("日傘", "日傘"),
    ("プール", "プール"),
    # 2026-08-16 8/14充足の新規3本
    ("岩牡蠣", "牡蠣"), ("牡蠣", "牡蠣"), ("岩がき", "牡蠣"),
    ("いちじく", "イチジク"), ("無花果", "イチジク"),
    ("網戸", "網戸"),
    # 2026-08-16 8/15充足の新規4本（夕涼み/花火の帰りは情感=無サムネ）
    ("冷やしトマト", "トマト"), ("トマト", "トマト"),
    ("冬瓜", "冬瓜"), ("とうがん", "冬瓜"),
    # 2026-08-16 owner単発題材
    ("バシャコーヒー", "コーヒー"), ("コーヒー", "コーヒー"), ("珈琲", "コーヒー"),
    # 2026-08-16 8/16充足の新規4本(帰省/夏バテは情感=無サムネ)
    ("流しそうめん", "そうめん"), ("そうめん", "そうめん"),
    ("お茶漬け", "お茶漬け"), ("茶漬け", "お茶漬け"),
]


def jp_query_for(title: str, stem: str):
    """対応する日本語検索語を返す。値はリストでもよく、その場合は**先頭から順に試す候補**になる。

    2026-09-11(CQO指摘・中10): 従来は1語しか試せず、実績のある語を未検証の語に置き換えた結果
    Commonsが0件を返し、Actionを3回回す羽目になった。code は A1 でクエリを事前検証できないので、
    **候補を複数持たせて外れたら次を試す**のが唯一の構造的な解。
    """
    hay = title + " " + stem
    for key, q in JP_QUERY:
        if key in hay:
            return q
    return None


def load_verified() -> set:
    """owner確認済みサムネのallowlist(_verified.txt)。ここに載るstemは自動取得で絶対に上書きしない(--forceでも)。"""
    try:
        return {ln.strip() for ln in VERIFIED_FILE.read_text(encoding="utf-8").splitlines()
                if ln.strip() and not ln.strip().startswith("#")}
    except Exception:
        return set()


def load_prov() -> dict:
    try:
        return json.loads(PROV_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_prov(p: dict) -> None:
    try:
        PROV_FILE.write_text(json.dumps(p, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
    except Exception:
        pass


# 2026-09-05 白黒/セピアの実写でない画像(銅版画・古書のハーフトーン印刷スキャン・
# 白黒写真)を bytes の段階で弾く。ファイル名フィルタだけでは
# 'PÊCHE INTERDITE(仏の白黒写真)' や '昭和の白黒スキャン' を取りこぼしたため（実測）。
# A3=サムネは写真風でカラー統一。Pillow が無い環境では検査をスキップ（安全側）。
MIN_SATURATION = 0.05


def _is_color_photo(data: bytes) -> bool:
    """カラー実写っぽいか。彩度がほぼ無い(=白黒/セピア)なら False。"""
    try:
        import io
        from PIL import Image, ImageStat
    except Exception:
        return True                      # Pillow 無し＝判定せず通す
    try:
        im = Image.open(io.BytesIO(data)).convert("RGB")
        im.thumbnail((200, 200))
        hsv = im.convert("HSV")
        sat = ImageStat.Stat(hsv).mean[1] / 255.0
        if sat < MIN_SATURATION:
            return False
        # 2026-09-06 CQO指摘: セピアの銅版画スキャンは彩度0.168で閾値を超え素通りした。
        # セピア/単色調は「色相がひとつに集中する」ので、色相の広がりでも判定する。
        hues = [h for h, s_, v_ in hsv.getdata() if s_ > 40 and v_ > 30]
        if len(hues) > 50:
            spread = len({h // 16 for h in hues})     # 色相を16分割した占有ビン数
            if spread <= 2:                            # ほぼ単一色相＝セピア/単色着色
                return False
        return True
    except Exception:
        return True                      # 解析できない時は通す（取り逃しを防ぐ）


def _get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


# 2026-09-05 実写以外(古書の挿絵/銅版画/地図/図版)を弾く。A3=サムネは写真風で統一、
# かつ「誤サムネより無サムネが正」。実測: 2語まで縮めた 'spacious japanese' が
# 19世紀の銅版画を拾ったため、語数下限と併せてこのフィルタを追加した。
NON_PHOTO_HINTS = (
    "engraving", "gravure", "illustration", "illustrated", "drawing", "sketch",
    "woodcut", "lithograph", "etching", "print of", "plate", "diagram", "map of",
    "map,", "plan of", "chart", "poster", "painting", "ukiyo", "manuscript",
    "le tour du monde", "page", "book", "album", "bub_", "internet archive",
    "scan", "atlas", "logo", "icon", "coat of arms", "seal of", "flag of",
    "18th century", "19th century", "1800", "1850", "1860", "1870", "1880", "1890",
)


# 古書スキャン(Internet Archive等)は題名に発行年が入りがち。'(1913)' 等を弾く。
# 実測: 'japanese suburban house' が1900年代の建築書の図版(セピア・西洋住宅)を拾った。
# 2026-09-06 実測: 日本語クエリ「獅子舞」でも Commons は **サンフランシスコの中国獅子舞(舞獅)**
# を返した。日本語で引けば日本の写真、とは限らない。題材が日本固有のとき、明らかに非日本を示す
# ファイル名は弾く（地理アンカーの日本語版）。CQO指摘D3の実害を受けての追加。
NON_JAPAN_HINTS = (
    "chinatown", "chinese", "china", "hong kong", "taiwan", "korea", "korean",
    "vietnam", "singapore", "malaysia", "thailand", "san francisco", "new york",
    "london", "paris", "sydney", "vancouver", "los angeles", "usa", "u.s.",
    "舞獅", "中国", "中華街", "唐人街",
    # 2026-09-07 実測で再発したもの。海外で行われる日本祭り／東南アジアの水田／欧州の海岸が
    # 「日本の写真」として配られていた（富山の8月＝米国の Matsuri Festival の舞台、
    #  田んぼ＝東南アジアの水牛と少年、入道雲＝バルト海らしき桟橋）。
    "washington", "seattle", "toronto", "melbourne", "hawaii", "brazil", "peru",
    "indonesia", "philippines", "cambodia", "laos", "myanmar", "india",
    "estonia", "latvia", "lithuania", "finland", "sweden", "poland", "germany",
    "festival in", "matsuri festival", "-us", " ohio", " texas", "california",
)

# 通信社の透かし入り写真は権利リスク（2026-08-02 と 2026-09-07 に FARS通信の写真を2回拾った）。
# Commons のファイル名に社名が入ることが多いので、名前で弾く。目視verifyの前段の機械ガード。
# ── code が目視verifyで落とした Commons ファイル。**同じ画像が戻ってこないようにする。**
# 2026-08〜09 に「獅子舞の誤サムネが8回戻ってきた」ことがあり、そのつど症状側（クエリ変更）で
# しのいでいた。落とした事実を残していないので、クエリが変わると同じ file を引き直していた。
# 判定は Commons のファイル名（"File:" は付けても付けなくてもよい／小文字化して部分一致）。
REJECTED_FILES = (
    # 2026-09-15
    "pont du gard",                      # 用水路の記事に**フランスのローマ水道橋**
    "taro leaf underside",               # 里芋の記事に**里芋の葉**（記事は土の中の芋の話・海外撮影）
    "倉敷市 用水路-03",                  # 日本の用水路だが**水を抜いて浚渫中**＝記事の主張「速い水が流れている」と逆
    # 2026-09-14
    "丹波おはぎ",                        # 和菓子店の作業場（人物写り込み・店名看板・富山以外の地域名が読める）
    "close-up butsudan at light on",     # 脇掛が九字名号＝**宗派が読み取れる**（本文が自宅の話のため筆者の宗派として読まれる）
    # 過去に採用してしまった誤サムネ（_provenance の実測で全て _japan_score 0 だった）。
    # 0点足切りで今後は入らないが、名前でも塞いでおく。
    "modern art museum, yerevan",        # 富山市ガラス美術館の記事にエレバンの美術館
    "utsunomiya daibutsu",               # 高岡大仏の記事に宇都宮大仏
    "ngari aka fermented fish",          # 北陸のへしこの記事にインド・マニプルの発酵魚
    "odisha crafts museum",              # 高岡銅器の記事にインド・オディシャの工芸博物館
    "kelp forest at taranga",            # とろろ昆布の記事にニュージーランドの昆布
    "squid ink pasta",                   # いかの黒造りの記事にイカスミパスタ
)


def _is_rejected_file(title: str) -> bool:
    """目視で落としたファイルか。名前で塞ぐ＝クエリを変えても同じ画像が戻ってこない。"""
    t = (title or "").lower().replace("file:", "").strip()
    return any(r in t for r in REJECTED_FILES)


AGENCY_HINTS = (
    "fars", "irna", "tasnim", "mehr news", "mehrnews", "isna", "yjc",
    "sputnik", "ria novosti", "xinhua", "kcna", "anadolu", "shutterstock",
    "getty", "alamy", "watermark",
)


def _looks_non_japan(title: str) -> bool:
    t = (title or "").lower()
    return any(h in t for h in NON_JAPAN_HINTS)


# 2026-09-12: 日本語クエリで引いたのに**日本の写真でない**候補が2件続けて通った。
#   焼き芋 → File:Gungoguma (roasted sweet potatoes) 2.jpg（韓国の군고구마・ライセンスも "CC BY-SA 2.0 kr"）
#   ナナカマド → File:Sorbus aucuparia Tauerntal（オーストリアのアルプス・しかも葉は緑＝紅葉していない）
# ファイル名の禁止語リストは「知っている地名」しか弾けず、この2件はどちらも未知の語だった。
# そこで**禁止でなく優先**に変える＝日本の痕跡がある候補を先に試す。痕跡が無い候補も最後には試すので
# （「Raw ginkgo nuts」「Pholiota microspora miso soup」のような良い写真を落とさない）取得率は下げない。
JAPAN_TOKENS = (
    "japan", "japanese", "nippon", "nihon", "honshu", "hokuriku",
    "toyama", "takaoka", "himi", "tateyama", "kurobe", "niigata", "ishikawa", "fukui",
    "kyoto", "osaka", "tokyo", "nagano", "gifu", "hokkaido", "tohoku", "kanazawa",
    "miso", "shrine", "temple", "tatami", "izakaya", "onsen", "sakura", "yakiimo",
)
# ライセンス名に付く国別ポート（kr/cn/tw 等）は、その国で撮られた写真である強い手がかり。
# 2026-09-12(CQO指摘・高9): 韓国ポート(kr)しか無く、欧州の写真は素通りしていた。CCの国別ポートを広く持つ。
NON_JP_LICENSE_PORTS = (
    " kr", " cn", " tw", " kor", " chn",
    " de", " fr", " it", " es", " pl", " nl", " at", " ch", " be", " cz", " se", " ee",
    " uk", " au", " ca", " br", " ru", " pt", " gr", " hu", " ro",
)
# ひらがな・カタカナは日本語に固有。**漢字は中国語と共通**なので、漢字だけでは最優先にしない
# （「紅葉」は中国語でも同じ字＝中国の紅葉写真が最優先で採られる経路があった）。
_KANA = re.compile(r"[\u3040-\u309F\u30A0-\u30FF]")
_KANJI = re.compile(r"[\u4E00-\u9FFF]")


def _japan_score(title: str, license_name: str = "") -> int:
    """日本の写真らしさ。3=かな / 2=漢字+日本語彙 / 1=日本を示す語 or 漢字のみ / 0=手がかりなし / -1=他国の痕跡。"""
    t = (title or "")
    low = t.lower()
    lic = (license_name or "").lower()
    if any(p in lic for p in NON_JP_LICENSE_PORTS):
        return -1
    has_token = any(k in low for k in JAPAN_TOKENS)
    if _KANA.search(t):
        return 3
    if _KANJI.search(t):
        return 2 if has_token else 1
    return 1 if has_token else 0


def _looks_agency(title: str) -> bool:
    """通信社/ストックの透かし入りが疑われるファイル名を弾く（権利リスク回避）。"""
    t = (title or "").lower()
    return any(h in t for h in AGENCY_HINTS)


_ARCHIVE_YEAR = re.compile(r"\b1[5-9]\d\d\b")


def _looks_non_photo(title: str) -> bool:
    """Commons のファイル名/ページ名から、実写でなさそうなもの(挿絵/図版/古書スキャン)を弾く。"""
    t = (title or "").lower()
    if any(h in t for h in NON_PHOTO_HINTS):
        return True
    if _looks_agency(t):
        return True
    return bool(_ARCHIVE_YEAR.search(t))   # 発行年入り=古書スキャンの可能性が高い


GEO_ANCHORS = ("japan", "japanese", "toyama", "takaoka", "himi", "hokuriku", "tateyama")


def _shorten(query: str):
    """Commons はキーワード検索＝長い説明的クエリ(『japanese nashi asian pear fruit sliced』)は0件に
    なりやすい。段階的に短くした候補を返す（重複除去・元→短の順）。

    重要: 短縮しても **地理アンカー(japan/toyama等)は必ず残す**。
    実測で 'canal fishing town japan' → 'canal fishing town' に縮めた結果、
    Commons が欧州の釣り風景を返した（日本の内川ではない）。末尾を落とすと
    アンカーが落ちて外国の写真を引くため、落ちた場合は付け直す。
    ※3語未満までは縮めない（'spacious japanese' 級の薄い2語は無関係画像を招く）。
    """
    words = query.split()
    anchor = next((w for w in words if w.lower() in GEO_ANCHORS), "")
    variants = [query]
    for n in (4, 3):
        if len(words) > n:
            v = words[:n]
            if anchor and anchor.lower() not in [w.lower() for w in v]:
                v = v + [anchor]             # アンカーは"付け足す"（置換すると主要名詞が落ちる）
            variants.append(" ".join(v))
    seen, out = set(), []
    for v in variants:
        if v and v not in seen:
            seen.add(v); out.append(v)
    return out


def _search_candidates(query: str):
    """1クエリで Commons を検索し、(候補url一覧, 診断dict) を返す。例外は上位へ。

    クエリ自体が日本語（かな/漢字を含む）なら、日本の題材を探しているということなので、
    日本の痕跡が一切ない候補（_japan_score==0）を採用しない。英語クエリには適用しない。"""
    _jp_query = bool(_KANA.search(query or "") or _KANJI.search(query or ""))
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": query, "gsrnamespace": "6", "gsrlimit": "12",
        # extmetadata も取る＝ライセンス/作者を保存するため（CC BY-SA は表示義務がある。
        # CQO指摘・中3: これまで出典を一切残しておらず、権利表示の可否を後から判断できなかった）。
        "prop": "imageinfo", "iiprop": "url|mime|size|extmetadata", "iiurlwidth": "1280",
        "origin": "*", "maxlag": "5",
    }
    data = json.loads(_get(API + "?" + urllib.parse.urlencode(params)).decode("utf-8"))
    diag = {"pages": 0, "img": 0}
    if data.get("error"):
        diag["error"] = str(data["error"])[:120]
    if data.get("warnings"):
        diag["warn"] = str(data["warnings"])[:120]
    pages = (data.get("query") or {}).get("pages") or {}
    diag["pages"] = len(pages)
    cands = []
    diag["nonphoto"] = 0
    for p in pages.values():
        ii = (p.get("imageinfo") or [{}])[0]
        if ii.get("mime") not in ("image/jpeg", "image/png"):
            continue
        diag["img"] += 1
        _title = p.get("title", "")
        if _looks_non_photo(_title):   # 古書の挿絵/銅版画/地図等は採用しない
            diag["nonphoto"] += 1
            continue
        if _looks_non_japan(_title):   # 中国/韓国/海外の同名行事は日本の記事に使わない
            diag["nonjp"] = diag.get("nonjp", 0) + 1
            continue
        w, h = ii.get("width", 0), ii.get("height", 0)
        if w < 900 or h < 560:           # アイコン/図版/小画像を除外
            continue
        if h > w * 1.2:                  # 縦長すぎは見出し向きでない
            continue
        turl = ii.get("thumburl") or ii.get("url")
        if turl:
            _em = ii.get("extmetadata") or {}
            _lic = (_em.get("LicenseShortName") or {}).get("value", "")
            _meta = {
                "file": _title,
                "license": _lic,
                "author": re.sub(r"<[^>]+>", "", (_em.get("Artist") or {}).get("value", ""))[:120],
                "descpage": ii.get("descriptionurl", ""),
            }
            if _is_rejected_file(_title):
                # 目視で落とした画像。クエリを変えても戻ってこないようにする。
                diag["rejected"] = diag.get("rejected", 0) + 1
                continue
            _sc = _japan_score(_title, _lic)
            if _sc < 0:
                # 他国のCCポート＝その国で撮られた写真である強い手がかり。順位を下げるだけだと
                # 「その語では-1しか返らない」場合にそのまま採用されてしまうので、ここで落とす。
                diag["nonjp_lic"] = diag.get("nonjp_lic", 0) + 1
                continue
            if _sc == 0 and _jp_query:
                # 2026-09-15: **日本語で引いたのに日本の痕跡が0の候補は落とす**。
                # 従来は順位を下げるだけで、候補が全部0点なら先頭がそのまま採用された。
                # 実害＝「用水路」で**フランスのローマ水道橋(Pont du Gard)**、「サトイモ」で
                # **里芋の葉**（海外撮影・記事は土の中の芋の話）。並べ替えるだけのガードは、
                # 全部が同点のときに何も守らない。
                # 過去の採用済み39件で実測すると0点は21件あり、その大半が既知の誤サムネだった
                # （エレバンの美術館／宇都宮大仏／インドの発酵魚／インドの工芸博物館／NZの昆布／
                #  イカスミパスタ）＝この足切りがあれば防げていた。
                # ただし**英語クエリ（仕事・抽象題材）には適用しない**。日本の痕跡を期待できないため。
                # 正しい日本の写真を取りこぼす場合はあるが、**誤サムネより無サムネが正**。
                diag["nojp_hint"] = diag.get("nojp_hint", 0) + 1
                continue
            cands.append((-_sc, p.get("index", 999), turl, _meta))
    # 日本の痕跡がある候補を先に、同点なら Commons の検索順。
    cands.sort(key=lambda c: (c[0], c[1]))
    diag["jp_first"] = sum(1 for c in cands if c[0] <= -2)   # score>=2 の候補数
    return [(t, m) for _, _, t, m in cands], diag


def fetch_from_wikimedia(query: str):
    """検索→実写候補(jpeg/png・横長・十分なサイズ)を順に試し、最初に取れた (bytes, 取得元URL) を返す。
    長い説明的クエリは Commons で0件になりやすいので、段階的に短縮した候補も試す。

    2026-09-07: 取得元URLも返すようにした。従来 _provenance.json には "wikimedia" としか
    残しておらず、**あとから「なぜこの写真になったのか」を追えなかった**（FARS通信の透かし写真を
    2回拾ったのに、どのファイルだったのか特定できなかった）。URLを残せば再発時に名前で弾ける。"""
    last_err: Exception | None = None
    last_diag = None
    for q in _shorten(query):
        for attempt in range(2):
            if attempt:
                time.sleep(attempt * 3)
            try:
                urls, diag = _search_candidates(q)
                last_diag = diag
                for turl, meta in urls[:6]:
                    try:
                        b = _get(turl)
                        if len(b) < MIN_IMAGE_BYTES:
                            continue
                        if not _is_color_photo(b):      # 白黒/セピア=実写サムネに使わない
                            diag["mono"] = diag.get("mono", 0) + 1
                            continue
                        return b, {"src": turl, **meta}
                    except Exception as e:
                        last_err = e
                # このクエリでは取れず → 次の（短い）クエリへ
                break
            except Exception as e:
                last_err = e
    # 全滅。診断（pages/img数 or error）を添えて上位で type 表示できるようにする
    detail = f" diag={last_diag}" if last_diag else ""
    raise last_err or RuntimeError(f"候補なし（query={query!r}）{detail}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--filter", default="")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--max", type=int, default=0)
    args = ap.parse_args()

    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    prov = load_prov()
    verified = load_verified()
    no_auto = {ln.strip() for ln in (NO_AUTO_FILE.read_text(encoding='utf-8').splitlines()
               if NO_AUTO_FILE.exists() else []) if ln.strip() and not ln.strip().startswith('#')}
    files = sorted(glob.glob(str(ARTICLES_DIR / "*note記事*.md")))
    files = [f for f in files if (not args.filter or args.filter in Path(f).name)]

    queue = []
    for f in files:
        p = Path(f)
        if "サムネ生成プロンプト" in p.name:
            continue
        if p.stem in verified:      # owner確認済み=絶対に上書きしない(--forceでもスキップ)
            continue
        if p.stem in no_auto:       # 自動取得を断念した題材=無サムネで確定（--forceでも取りに行かない）
            # 別runの競合等で既にjpgが在る場合は**消す**。残すとpublisher経路が拾って誤サムネ公開になる。
            stray = THUMB_DIR / f"{p.stem}.jpg"
            if stray.exists():
                try:
                    stray.unlink(); print(f"  removed stray thumbnail (no_auto): {p.stem}")
                except Exception:
                    pass
            continue
        out = THUMB_DIR / f"{p.stem}.jpg"
        # 2026-07-30 Pexels優先化に伴い、既存jpgは（provenance問わず）上書きしない＝
        # Wikimediaは「まだ画像が無い記事」だけ補完するフォールバックに徹する。
        # これにより Pexels が取った良質な実写を Wikimedia が塗り替える事故を防ぐ。
        if out.exists() and not args.force:
            continue
        text = p.read_text(encoding="utf-8")
        title = extract_title(text, p.stem)
        jp = jp_query_for(title, p.stem)                 # 概念語は日本語検索を優先
        en = query_for(title, p.stem)                    # 英語フォールバック
        queue.append((p.stem, jp, en, out))
    if args.max > 0:
        queue = queue[: args.max]

    print(f"backend: wikimedia（無料・実写）／対象: {len(queue)}本")
    ok = fail = 0
    for stem, jp, en, out in queue:
        # JP該当stem(温泉/川/そうめん等の概念題材)は英語だと別物を拾うので英語フォールバックしない
        # ＝JPで取れなければ無画像のまま（誤サムネより無サムネが正・publisherは_verifiedのみ採用）。
        # jp は文字列 or 候補リスト。JP該当stemは英語だと別物を拾うので英語へは落とさない
        # （誤サムネより無サムネが正・publisherは_verifiedのみ採用）。
        if isinstance(jp, (list, tuple)):
            tried = [q for q in jp if q]
        elif jp:
            tried = [jp]
        else:
            tried = [en] if en else []
        data = None
        used = None
        last = None
        src = {}
        for q in tried:
            try:
                data, src = fetch_from_wikimedia(q)
                used = q
                break
            except Exception as e:
                last = e
        if data:
            out.write_bytes(data)
            # backend だけでなく **クエリと取得元URL** を残す＝あとから誤サムネの原因を追える
            # 出典一式（Commonsのファイル名・ライセンス・作者・説明ページ）を残す。
            prov[stem] = {"backend": "wikimedia", "query": used, **src}
            save_prov(prov)
            print(f"  ✓ {out.name}  ← '{used}'  ({len(data)//1024} KB)  "
                  f"[{src.get('license') or 'license?'}] {src.get('file', '')}")
            ok += 1
        else:
            print(f"  ✗ {stem}  (tried {tried}): {type(last).__name__ if last else '?'} — {str(last)[:160] if last else ''}")
            fail += 1
        time.sleep(1.0)  # Commons への礼儀＝ペース調整
    print(f"\n成功: {ok} / 失敗: {fail}")


if __name__ == "__main__":
    main()
