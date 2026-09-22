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
    # 2026-09-15: 高岡大仏に JP_QUERY が無く EN_QUERY「great buddha statue japan」へ落ちて
    # 奈良の大仏を拾った。土地名入りのクエリを明示的に持たせる。
    ("高岡大仏", ["高岡大仏", "高岡 大仏"]), ("銅の大仏", ["高岡大仏", "高岡 大仏"]),
    # 3巡目: 里芋は「芋煮」で**芋煮会の会場パノラマ**（芋が写っていない）。用水路は塞いだ -03 の
    # **連番 -04**が来た（同じ浚渫中の連作）。名前で連作ごと塞いだうえで未使用の語に絞る。
    # 2026-09-16 の新規2本。0点足切りが効くので、日本語名の付いた写真が来る語を並べる。
    # 蕎麦は「新蕎麦」だとCommonsに写真が乏しいと見て、料理としての盛り付け語を先に置く。
    # 2026-09-17 の新規2本。
    # 運動会は**児童生徒の顔が写った写真を絶対に採らない**（A4/肖像）。無人の校庭で構わないので、
    # 人が写りにくい語（校庭・グラウンドのライン）を先に置く。取れなければ無サムネで確定させる。
    # 1巡目は全滅（0点足切り＝日本の痕跡のない候補しか無かった）。日本語名の付いた写真を狙って語を替える。
    # 2026-09-18 の新規2本。どちらも日本語名の写真がCommonsに多い題材を選んである
    # （09-17は2本とも無サムネ確定になったので、題材選定の段階でサムネ可用性を見た）。
    # 1巡目「マツタケ」「松茸」「マツタケ 収穫」は全滅（学名ファイル名が0点足切りに掛かった）。
    # 学名をJAPAN_TOKENSに足したうえで、学名そのものも候補に入れる。
    # 2026-09-19 の新規2本。どちらも日本語名の写真がCommonsに多い題材。
    # いくらは**器に盛った醤油漬け**を狙う（生筋子の塊だと[写真①]と合わない）。
    # 金木犀は**花の接写**。木全体の遠景だと「小さい花が密集」という本文の主張が見えない。
    # 1巡目「いくら 醤油漬け」は0件、2巡目「イクラ 丼」は**ウニ丼**（外食の定食）で不合格。
    # Commons は片仮名表記が多いので片仮名を先に置き、丼ものを候補から外す。
    # 2026-09-24 の新規2本。
    # ひやおろし＝**日本酒の瓶が並んだ売り場／蔵の貯蔵タンク**。
    #   **銘柄ラベルが大きく読めるもの・人物が写るものは不可**（宣伝と肖像を避ける）。
    # 衣替え＝**畳んだ衣類・押し入れ**。**人物が写るものは不可**（A4／肖像）。
    ("ひやおろし", ["日本酒 瓶", "清酒 貯蔵タンク", "酒蔵 タンク", "日本酒 売り場"]),
    ("夏を越させる", ["日本酒 瓶", "酒蔵 タンク"]),
    # 「衣装ケース」は外した＝**相模湾の護岸に捨てられた黒いケース**を拾った（2026-09-19・REJECTED登録済）。
    # 「ケース」は容器一般を指すので、衣類と無関係な写真に届いてしまう。衣類の語が入る形に寄せる。
    # 2026-09-25 実測: 「衣類 整理」は pages:1 / nonphoto:1（図版で落ちた）。
    #   filetype:bitmap で PDF は消えたが、**複合語で候補が1件しか返らない**のが残りの原因。単語に寄せる。
    ("衣替え", ["箪笥", "タンス", "押入れ", "衣装箱", "衣類 収納"]),

    # ── 2026-09-21: **検索語が1本も無かった富山圏の記事**に題材語を足す。
    #   毎runの空振り62本のうち20本がこれで、いずれも North Star そのものの記事だった
    #   （高岡・氷見・富山の題材なのにサムネを取りに行けていない）。
    #   ※地名を名乗る記事は**地名入りのクエリ**が要る（_place_mismatch のガード）。
    ("ガラス美術館", ["富山市ガラス美術館", "富山 ガラス美術館", "富山 キラリ"]),
    ("高岡銅器", ["高岡銅器", "高岡 鋳物", "高岡 銅器"]),
    ("かぶら寿司", ["かぶら寿司", "蕪寿司", "北陸 かぶら寿司"]),
    ("氷見の干物", ["氷見 干物", "氷見 漁港", "氷見 魚"]),
    ("みりん干し", ["みりん干し", "干物 天日", "氷見 干物"]),
    ("氷見潮風ギャラリー", ["氷見 潮風ギャラリー", "氷見 まんが", "氷見市"]),
    ("氷見線", ["氷見線", "氷見線 列車", "雨晴海岸 列車"]),
    ("寒ブリ", ["氷見 寒ブリ", "鰤 氷見", "ブリ 水揚げ"]),
    ("二上山", ["二上山 高岡", "高岡 二上", "高岡 里山"]),
    ("御旅屋通り", ["高岡 商店街", "高岡 アーケード", "御旅屋"]),
    ("新湊内川", ["新湊 内川", "射水 内川", "新湊 漁船"]),
    ("千保川", ["千保川", "高岡 川", "高岡 千保川"]),
    ("魚のアラ", ["魚のアラ", "鮮魚 売り場", "アラ汁"]),
    ("富山弁", ["富山 方言", "富山県", "富山 まちなみ"]),
    ("富山の宿", ["富山 旅館", "富山 ホテル", "富山県 宿"]),
    ("レンタカー", ["富山 道路", "富山 車窓", "富山県 国道"]),
    ("夏至前の北陸", ["北陸 夕焼け", "富山 夕方", "富山湾 夕景"]),
    ("バタバタ茶", ["バタバタ茶", "朝日町 バタバタ茶", "茶筅 茶"]),
    ("日付で服を入れ替える", ["衣類 収納", "たたんだ衣類"]),
    # 2026-09-23 の新規2本。
    # ぶどう＝**房になった実**。皿に盛った粒・ジュース・ワインは本文とずれる（種と皮の話なので実物）。
    # 日の入り＝**夕焼け／日没の空**。ただし「夕焼け」は既に別記事で使っているので同一画像を配らないよう
    #   「日没」「入日」を先に置く（R2d フォールバック汚染の回避）。
    # 2026-09-21: 4クエリとも空振り。診断は nojp_hint:7 ＝候補は12枚あったが
    # **日本の痕跡が無いので0点足切りで全滅**（ブドウの写真は欧州産が多い）。ガードは正しい。
    # 日本の品種名は Commons のファイル名にそのまま入るので、そちらで引く。
    ("ぶどう", ["巨峰", "デラウェア ブドウ", "ブドウ 山梨", "ブドウ狩り", "ブドウ 房"]),
    ("種を出す手間", ["ブドウ 房", "ぶどう 果実"]),
    ("日の入り", ["日没 海", "入日", "日の入り", "夕空"]),
    ("暗くなる時刻", ["日没 海", "入日"]),
    # 2026-09-22 の新規2本。
    # れんこん＝**輪切りにして穴が見えている状態**。畑・泥つきの塊でも可。料理の完成皿は避ける。
    # 墓参り＝**供えられた花や墓地の風景**。ただし A4/肖像のため、
    #   **人物・墓石の文字・寺院名が写るものは不可**。条件に合わなければ無サムネで確定させる。
    # 2026-09-21: 最後の「ハス 地下茎」は pages:0＝検索が1件も返さない語だった。
    # 料理名・加工品名のほうが Commons のファイル名に実在する。
    ("れんこん", ["レンコン 輪切り", "蓮根", "レンコン", "れんこん 煮物", "蓮根 収穫"]),
    ("穴が空いているから", ["レンコン 輪切り", "蓮根"]),
    # 2026-09-21: 「お供え 花」は pages:3 / img:0。**人物・墓石の文字・寺院名が写るものは不可**(A4)
    # なので、墓地の遠景か彼岸花に寄せる。
    ("墓参り", ["彼岸花 墓地", "供花", "墓地 日本", "彼岸花 田んぼ", "卒塔婆"]),
    ("年に何度行くか", ["供花", "お供え 花"]),
    # 2026-09-21 の新規2本。R27（登録漏れの検知）が書いた直後に BROKEN を出したので、その場で登録した。
    # ざくろ＝**割れて粒が見えている実**。ジュース・加工品・料理の皿は本文とずれる。
    # かかし＝**刈り終わった田に立つかかし**。人物が大きく写るもの、かかしコンテストの群れは不可（A4／肖像）。
    # 1巡目「pomegranate japan」で**まな板の上の切ったザクロ**を拾った＝本文（誰も採らない／木に残る）
    # と正反対。英語クエリに japan を付けても足切りが効いていなかったのが原因（_jp_query を直した）。
    # 狙いは**木に生っている／自然に裂けた実**なので、木・枝を含む語を先に置き、切った実は避ける。
    ("ざくろ", ["ザクロ 木", "ザクロ 実 枝", "ザクロ 果実", "柘榴"]),
    ("誰も採らない木", ["ザクロ 木", "ザクロ 実 枝"]),
    ("かかし", ["かかし 田", "案山子", "かかし 稲刈り後", "scarecrow japan"]),
    ("顔が描いてある", ["かかし 田", "案山子"]),
    # 2026-09-20 の新規2本。**登録を忘れて1巡目が丸ごと空振りした**（成功0/失敗59）。
    # そのときのログは「土地名を含むクエリが無い」と出ていたが、実際は**クエリ自体が未登録**で、
    # メッセージの「」も空だった＝原因を取り違えさせる出方をしていたので下で直した。
    # 秋茄子＝**切る前の実**。料理の完成皿（麻婆茄子・焼き茄子）は本文とずれる。
    # 置き傘＝**傘立て**を先に置く。雨の街の写真は人物が大きく写りやすく A4／肖像のリスクがある。
    #   和傘・番傘は不可（本文はビニール傘と置き傘の話で、伝統工芸の話ではない）。
    # 2巡目:「茄子」で**重慶の茄子溪駅**を拾った（中国の地名に同じ漢字が入る）。
    # 単独の「茄子」を外し、野菜だと分かる語だけにする。CN_MARKERS でも弾くようにした。
    # 3巡目も全滅。diag は pages:12 / img:12 / **nojp_hint:8** ＝候補は在るのに0点足切りで8枚落ちていた。
    # あけび・松茸・いくらと同じ型だが、**ナスは世界中で作られる野菜**なので学名(Solanum melongena)を
    # JAPAN_TOKENS に足すのは筋が悪い（イタリアの丸ナスまで通ってしまう）。
    # 代わりに**クエリ自体が日本を名乗る語**を足す＝ファイル名に japan が入るものだけが通る。
    ("秋茄子", ["japanese eggplant", "ナス 収穫", "eggplant japan", "ナス 畑", "茄子 収穫"]),
    ("正反対の説明", ["japanese eggplant", "ナス 収穫"]),
    ("置き傘", ["傘立て", "ビニール傘", "傘立て 玄関", "傘 日本"]),
    ("誰のものでもなくなる", ["傘立て", "ビニール傘"]),
    ("いくら", ["イクラ 醤油漬け", "イクラ", "筋子", "サケ 卵"]),
    ("生の筋子", ["イクラ 醤油漬け", "筋子"]),
    ("金木犀", ["キンモクセイ 花", "金木犀", "キンモクセイ"]),
    ("においが先", ["キンモクセイ 花", "金木犀"]),
    ("松茸", ["松茸", "マツタケ 収穫", "松茸 かご", "マツタケ 料理"]),
    ("名前だけ知っている", ["松茸", "マツタケ 収穫"]),
    ("稲刈り", ["稲刈り", "コンバイン 稲刈り", "稲刈り後の田", "刈り取り 水田"]),
    ("うるさい日", ["稲刈り", "コンバイン 稲刈り"]),
    ("あけび", ["アケビ 果実", "Akebia quinata fruit", "アケビ 裂", "アケビ 実"]),
    ("中身だけ食べる実", ["アケビ 果実", "Akebia quinata fruit"]),
    # 1巡目「小学校 校庭」→ 桜満開の春の校庭（無人なのは良いが季節が逆・白線なし・学校名がクレジットに入る）。
    # **「運動会」を候補から外した**＝児童生徒の顔が写った写真を引く可能性が高く、A4／肖像のリスクが取れない。
    # 人が写りにくい語だけに絞り、届かなければ _no_auto（無サムネ確定）にする。
    ("運動会", ["グラウンド ライン", "陸上競技場 トラック", "校庭 ライン"]),
    ("場所取りの朝", ["グラウンド ライン", "校庭 ライン"]),
    ("赤とんぼ", ["アキアカネ", "赤とんぼ", "アカトンボ", "トンボ 秋"]),
    ("山で夏を過ごして", ["アキアカネ", "赤とんぼ"]),
    # 1巡目「ざるそば」→ **将棋の駒の形の器**（天童の名物）。蕎麦自体は良いが器が主役になる。
    ("新蕎麦", ["もりそば", "蕎麦 盛り", "そば 料理", "新蕎麦"]),
    ("秋になると幟が立つ", ["もりそば", "蕎麦 盛り"]),
    ("里芋", ["里芋 収穫", "里芋 畑", "サトイモ 栽培"]),
    ("親芋", ["里芋 収穫", "里芋 畑"]),
    ("用水路", ["疏水", "用水路 日本", "農業用水路"]),
    ("速い水が流れている", ["疏水", "用水路 日本"]),
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
    # 2026-09-25分。**「田んぼ」より前に置く**＝後ろに置くと二番穂の記事が
    # 汎用の「田んぼ」に吸われて、刈る前の緑の水田が来てしまう（主題は刈った後の再生）。
    # 2026-09-25 実測: 「ヤマノイモ 珠芽」は pages:0。**2語の日本語複合語は Commons にほぼ当たらない**
    #   （ファイル名は単語で付いているため）。実際に当たったのは 蓮根 / 巨峰 / 彼岸花 のような**単語**。
    # 2026-09-26分。今日の教訓＝**2語の複合語は候補が出ず、曖昧な単語は別物に当たる**
    #   （「稲孫」が人名 錢稻孫 に、「タンス」が競馬の写真に当たった）。
    #   題材が一意に決まる語だけを並べる。
    ("豚汁", ["豚汁", "味噌汁 具だくさん", "けんちん汁"]),
    # 2026-09-22: 「石油ストーブ」で **外部タンク付きの据置型ファンヒーター**が来た（別の器具）。
    #   本文は物置から出す携帯型の話なので、**反射式**を先に試す。
    ("石油ストーブ", ["反射式ストーブ", "石油ストーブ 反射", "ストーブ やかん", "石油ストーブ"]),
    ("柿", ["柿 果実", "柿 木", "甘柿", "渋柿"]),
    ("渡り鳥", ["田んぼ 鳥", "水田 鳥", "刈田 鳥", "渡り鳥"]),
    ("鮭", ["塩鮭", "焼き鮭", "鮭 切り身", "サケ 切り身"]),
    ("落ち葉", ["落ち葉", "落ち葉 道", "枯れ葉", "落葉 歩道"]),
    ("むかご", ["むかご", "零余子", "Mukago", "Dioscorea japonica"]),
    # 2026-09-25 実測: 「稲 再生」は pages:1 / too_small:1。同じく単語に寄せる。
    ("二番穂", ["ひこばえ", "二番穂", "稲孫", "ratoon rice"]),
    ("ひこばえ", ["ひこばえ", "二番穂", "稲孫"]),
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
    # 2026-09-19: **私が画像そのものを見て落とした最初の1件**（これまでは名前と出典しか見ていなかった）。
    # 「衣替え」のクエリ 衣装ケース が **相模湾の護岸に捨てられた黒いケース** に一致していた。
    # 波消しブロックと堤防の写真で、衣類は1枚も写っていない。画面隅に「相模湾」の文字入り。
    "相模湾",
    # 2026-09-19: 出典の埋め戻しが進んで、**採用していない側のプールにも誤サムネが溜まっていた**
    # ことが判明。いずれも _verified に入っていないので公開には使われていない（allowlist が効いた）。
    # それでも名前で塞いでおく＝将来うっかり採用しないため。
    "edgar degas", "google art project", "portugal-lisboa", "port arthur",
    "modern art museum, yerevan", "odisha crafts museum",

    # 2026-09-22: **英語の一般語で引いた採用サムネ9件を総点検**し、4件が主題と合っていなかった。
    # 高岡万葉線の京都市電と同じ型で、「日本の写真ではあるが別の土地／別の物」を拾っている。
    "道滿green park",        # 埼玉・道満グリーンパーク → 高岡のおとぎの森公園ではない（2記事で使用）
    "ramen bowl 2",          # スープが澄んでいる → 富山ブラック（黒い醤油）の記事に不可（2記事で使用）
    "cod soup-01",           # トマトとセロリの洋風スープ → 朝日町のたら汁（味噌仕立て）ではない
    "rock'n'roll craft beer",# 英国 Marshall の缶 → 「富山の地ビール」の見出しに他社ブランドは不可

    # 2026-09-22: **高岡万葉線の記事に京都市電（明治村の保存車両）が使われていた**。
    # 出典の埋め戻しが進んで初めて判明。英語クエリ "tram streetcar japan city" で引いたため、
    # 日本の路面電車ではあるが**別の都市の、しかも博物館の展示車両**だった。
    "heritage kyoto city tram",

    # 2026-09-15
    "倉敷市 用水路",                     # -03を塞いだら**同じ連番の-04**が来た。水を抜いて浚渫中の連作なのでシリーズごと塞ぐ
    "農業用水路跡",                      # 用水路の**遺構**（水なし・林の中・文化財の解説板つき）。記事は「速い水が流れている」話
    "uni-ikura-don",                     # **半分がウニ**の丼。しかも味噌汁・割り箸・漬物つきの**外食の定食**で、
                                        # 本稿の「家で筋子をほぐして漬ける」という主題と正反対
    "akebia quinata 02",                 # あけびの**花**（春）。記事は秋の**裂けた実**の話
    "tricholoma matsutake (15415279801)", # 松茸だが**トナカイゴケと花崗岩の北方林の林床**＝北欧らしい。
                                         # 傘も開ききっていて「秋の高級品」の見え方でもない
    "takebishi stadium",                 # 運動会の記事に**夜の陸上競技場**。学校でも九月の校庭でもなく、
                                        # **観客の顔が手前に大きく写っている**（A4／肖像）
    "奈佐小学校の校庭",                  # 無人なのは良いが**桜が満開＝春**（記事は九月の運動会）／白線もトラックも無い／
                                        # CC BY-SA の表示義務で**特定の小学校名**がクレジットに入る（読者に筆者の地元校と読まれうる）
    "将棋ざるそば",                      # 蕎麦は良いが器が**将棋の駒（銀将）の形**＝天童の名物。普通の蕎麦の見え方ではないうえ、
                                        # CC BY の表示義務で店名と市名がクレジットに入る。記事は「季節と自分の味覚」の話
    "日本一の芋煮会",                    # 里芋の記事に**芋煮会の会場を写した超横長パノラマ**（芋は写っていない）
    "tōdai-ji",                          # 高岡大仏の記事に**奈良の大仏**。EN_QUERY「great buddha statue japan」が引いた
    "todai-ji", "todaiji",
    "kamakura daibutsu", "kotoku-in",    # 同じ理由で鎌倉大仏も塞ぐ（高岡大仏の記事に来る）
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
    # 2026-09-18 追加: **日本の題材である動植物の学名**。
    # 0点足切り（日本語クエリで引いたのに日本の痕跡が無い候補を落とす）を入れて以降、
    # **あけび・松茸が2本続けて無サムネになった**。原因は、Commons では動植物のファイル名が
    # 学名（Akebia quinata / Tricholoma matsutake）になりやすく、日本語も地名も入らないこと。
    # 種そのものが記事の主題である場合、学名の一致は「題材が正しい」という**より強い**手がかりなので、
    # 日本の痕跡として扱う。撮影地が国外の個体を拾う可能性は残るが、
    # 松茸の記事は輸入品にも触れており、別の題材を拾う誤りとは性質が違う。
    # 2026-09-19 追加: **日本語の食べもの名のローマ字表記**。あけび・松茸のときと同じ型で、
    # 「イクラ」「筋子」「イクラ 醤油漬け」「サケ 卵」の4語すべてが0件になった。
    # Commons では日本の食べものが "Ikura"/"Sujiko" のローマ字だけで命名されることがあり、
    # 日本語も地名も入らないため 0点足切りに掛かる。これらの語自体が日本の食べものを指すので
    # 日本の痕跡として扱う（"salmon roe" のような一般語は入れない＝どの国のものか分からないため）。
    "ikura", "sujiko", "matsutake", "wasabi", "mochi", "natto", "umeboshi",
    "tricholoma matsutake", "akebia quinata", "sympetrum frequens",
    "colocasia esculenta", "diospyros kaki", "ginkgo biloba", "pholiota microspora",
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


# 2026-09-20 実測: 「茄子」で引いたら **中国・重慶の「茄子溪」駅**（File:茄子溪4.jpg）を拾った。
# _japan_score は「漢字が入っていれば 1点」なので、**日本語と同じ漢字を含む中国の地名は素通りする**。
# 0点足切りの網はこの型に効かない。そこで「日本語では使わない字」が入っていたら他国の痕跡として扱う。
# ・簡体字（日本語では別の字体になるもの）… 车铁线轨广华汉龙马鸟长东时门关亚讯业风飞习币
# ・中国語圏の語（日本語のファイル名にはまず出ない）… 站 / 捷運 / 地鐵 / 溪
# 誤爆を避けるため、日本語にも普通にある字（区・国・湾 等）は入れない。
CN_MARKERS = ("车", "铁", "线", "轨", "广", "华", "汉", "龙", "马", "鸟", "长", "东", "时",
              "门", "关", "亚", "讯", "业", "风", "飞", "习", "币", "站", "捷運", "地鐵", "溪")


def _looks_chinese(title: str) -> bool:
    """中国語圏の地名・施設名らしさ。日本語では使わない字が入っていれば True。"""
    return any(c in (title or "") for c in CN_MARKERS)


# 2026-09-22 実測: 「レンコン」で **Loin steak, chrysanthemum chimichurri, lotus root purée…**
# （西洋料理の皿）を拾った。原因は JAPAN_TOKENS の "himi"(氷見) が
# **chi(himi)churri の中に部分一致**していたこと。4文字のローマ字は英単語の内側に普通に現れる。
# → ASCII のトークンは**単語境界**で照合する（日本語トークンは境界が無いので従来どおり部分一致）。
_ASCII_TOK = [k for k in JAPAN_TOKENS if all(ord(c) < 128 for c in k)]
_JP_TOK = [k for k in JAPAN_TOKENS if any(ord(c) >= 128 for c in k)]
_ASCII_RE = re.compile(r"(?<![a-z0-9])(?:" +
                       "|".join(re.escape(k) for k in sorted(_ASCII_TOK, key=len, reverse=True)) +
                       r")(?![a-z0-9])") if _ASCII_TOK else None


def _has_japan_token(low: str) -> bool:
    """日本を示す語が入っているか。ASCII の語は単語境界で見る（部分一致の誤爆を防ぐ）。"""
    if any(k in low for k in _JP_TOK):
        return True
    return bool(_ASCII_RE and _ASCII_RE.search(low))


def _japan_score(title: str, license_name: str = "") -> int:
    """日本の写真らしさ。3=かな / 2=漢字+日本語彙 / 1=日本を示す語 or 漢字のみ / 0=手がかりなし / -1=他国の痕跡。"""
    t = (title or "")
    low = t.lower()
    lic = (license_name or "").lower()
    if any(p in lic for p in NON_JP_LICENSE_PORTS):
        return -1
    if _looks_chinese(t):
        return -1
    has_token = _has_japan_token(low)
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


# 記事タイトルが固有の土地を名乗っているなら、クエリもその土地を名乗っていなければならない。
# 2026-09-15 の実害: 「高岡大仏」の記事に JP_QUERY が無く EN_QUERY「great buddha statue japan」へ
# 落ちた結果、**奈良の大仏**を拾った。前にも同じ型で**宇都宮大仏**を拾っている。
# 一般語で引けば、その題材の全国的な代表例（奈良/鎌倉）が必ず上位に来る＝構造的に外す。
PLACE_TOKENS = ("高岡", "氷見", "富山", "立山", "黒部", "砺波", "南砺", "射水", "滑川", "魚津", "小矢部")
_PLACE_ROMAJI = {"高岡": "takaoka", "氷見": "himi", "富山": "toyama", "立山": "tateyama",
                 "黒部": "kurobe", "砺波": "tonami", "南砺": "nanto", "射水": "imizu",
                 "滑川": "namerikawa", "魚津": "uozu", "小矢部": "oyabe"}


# 土地名の直後が助詞・区切りなら「その土地の一般的な題材」（例:「富山の田んぼ」「立山の紅葉」）＝
# 全国どこの写真でも成立するのでクエリに土地名は要らない。
# 直後が続く語なら固有名詞（例:「高岡大仏」「富山市ガラス美術館」「氷見うどん」「富山ブラック」）＝
# 一般語で引くと必ず全国の代表例（奈良の大仏／ただのラーメン／ただのうどん）を拾うので土地名を要求する。
_PLACE_LOOSE = "のはがをにへともや、。_ 　：:・"


def _place_mismatch(stem: str, query: str) -> str:
    """記事が**固有名詞として**土地を名乗り、クエリがその土地を名乗っていなければ土地名を返す。"""
    st = stem or ""
    q = (query or "").lower()
    for jp in PLACE_TOKENS:
        i = st.find(jp)
        if i < 0:
            continue
        nxt = st[i + len(jp): i + len(jp) + 1]
        if nxt == "" or nxt in _PLACE_LOOSE:
            continue                      # 「富山の〜」＝一般的な題材。土地名を要求しない
        if jp in query or _PLACE_ROMAJI[jp] in q:
            return ""
        return jp
    return ""


def _search_candidates(query: str):
    """1クエリで Commons を検索し、(候補url一覧, 診断dict) を返す。例外は上位へ。

    クエリ自体が日本語（かな/漢字を含む）なら、日本の題材を探しているということなので、
    日本の痕跡が一切ない候補（_japan_score==0）を採用しない。英語クエリには適用しない。"""
    # 2026-09-21 実測: 「pomegranate japan」で **File:Pomegranate cut in half.jpg**（まな板の上の
    # 切ったザクロ）を拾った。0点足切りは「クエリが日本語のときだけ」効く作りだったので、
    # **英語のクエリを足した瞬間に日本判定が丸ごと無効になっていた**。
    # 日本を名乗るクエリ（"... japan"）は日本の写真を探しているのだから、同じ足切りを掛ける。
    _jp_query = bool(_KANA.search(query or "") or _KANJI.search(query or "")
                     or "japan" in (query or "").lower())
    # ★2026-09-21: **検索の時点で画像に限定する**。
    #   File名前空間には PDF も入っているので、日本語の語では PDF ばかり返ることがある。
    #   実測（Actionのログ）: 「衣類 整理」→ **12件すべて application/pdf**、
    #   「蓮根 収穫」→ 2件とも PDF。取得側で mime を弾いていたため
    #   「pages:12 / img:0」＝**候補枠を全部 PDF に使い潰して0件**になっていた。
    #   filetype:bitmap は Commons の検索構文で、jpeg/png 等のビットマップ画像だけに絞る。
    _q = f"{query} filetype:bitmap"
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": _q, "gsrnamespace": "6", "gsrlimit": "12",
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
    # filetype:bitmap が効かない／絞りすぎて0件になった場合は、**元のクエリで引き直す**。
    # 新しい絞り込みを入れるときに、それ自体が全滅の原因になっては本末転倒なので退避路を持つ。
    if not pages:
        params["gsrsearch"] = query
        data2 = json.loads(_get(API + "?" + urllib.parse.urlencode(params)).decode("utf-8"))
        pages2 = (data2.get("query") or {}).get("pages") or {}
        if pages2:
            diag["bitmap_filter_empty"] = True   # 絞り込みが0件→素のクエリで拾い直した
            data, pages = data2, pages2
    diag["pages"] = len(pages)
    cands = []
    diag["nonphoto"] = 0
    # ★2026-09-21: 診断に**落ちた理由**を残す。これまでは pages と img しか数えておらず、
    #   「pages:12 / img:0」という**何も分からない報告**が出ていた（衣替え・墓参り）。
    #   mime で落ちたのか、imageinfo が無かったのか、サイズや縦横比で落ちたのかを区別する。
    #   数えていない足切りは、あとから原因を追えない＝直せない。
    for p in pages.values():
        _iis = p.get("imageinfo") or []
        if not _iis:
            diag["no_imageinfo"] = diag.get("no_imageinfo", 0) + 1
            continue
        ii = _iis[0]
        _mime = ii.get("mime")
        if _mime not in ("image/jpeg", "image/png"):
            diag.setdefault("mimes", {})
            diag["mimes"][_mime or "none"] = diag["mimes"].get(_mime or "none", 0) + 1
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
            diag["too_small"] = diag.get("too_small", 0) + 1
            continue
        if h > w * 1.2:                  # 縦長すぎは見出し向きでない
            diag["too_tall"] = diag.get("too_tall", 0) + 1
            continue
        turl = ii.get("thumburl") or ii.get("url")
        if not turl:
            diag["no_url"] = diag.get("no_url", 0) + 1
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
        # 記事が土地を名乗っているのに、そのクエリが土地を名乗っていなければ使わない。
        # 一般語（"great buddha statue japan"）で引くと、その題材の全国的な代表例（奈良/鎌倉）が
        # 必ず上位に来るので構造的に外す。2026-09-15 に奈良の大仏を、以前に宇都宮大仏を拾っている。
        _dropped = [q for q in tried if _place_mismatch(stem, q)]
        if _dropped:
            _pl = _place_mismatch(stem, _dropped[0])
            tried = [q for q in tried if not _place_mismatch(stem, q)]
            print(f"  skip(place): {stem[:30]}… は「{_pl}」を名乗る記事。"
                  f"土地名を含まないクエリ {_dropped} は使わない")
        if not tried:
            # 2026-09-20: ここは「土地名が足りない」と「そもそもクエリが1本も無い」の
            # **2つの別々の原因**が同じ文言で出ていた。後者のとき「」が空で表示されるため、
            # 土地名の問題だと読み違える。原因ごとに違う文言を出す。
            _pl_need = _place_mismatch(stem, "")
            if _dropped and _pl_need:
                print(f"  ✗ {stem}  (「{_pl_need}」を名乗る記事なのに土地名入りのクエリが無い "
                      f"→ JP_QUERY に「{_pl_need}」入りの語を足すこと)")
            else:
                print(f"  ✗ {stem}  (**JP_QUERY にも EN_QUERY にも登録が無い**＝検索語が1本も無い。"
                      f"新しい記事を書いたら JP_QUERY に題材語を登録すること)")
            fail += 1
            continue
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
