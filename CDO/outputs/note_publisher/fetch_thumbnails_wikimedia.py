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
# 外したら英語(query_for)にフォールバックする。キー不要のまま精度を上げる狙い。
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
        sat = ImageStat.Stat(im.convert("HSV")).mean[1] / 255.0
        return sat >= MIN_SATURATION
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
)


def _looks_non_japan(title: str) -> bool:
    t = (title or "").lower()
    return any(h in t for h in NON_JAPAN_HINTS)


_ARCHIVE_YEAR = re.compile(r"\b1[5-9]\d\d\b")


def _looks_non_photo(title: str) -> bool:
    """Commons のファイル名/ページ名から、実写でなさそうなもの(挿絵/図版/古書スキャン)を弾く。"""
    t = (title or "").lower()
    if any(h in t for h in NON_PHOTO_HINTS):
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
    """1クエリで Commons を検索し、(候補url一覧, 診断dict) を返す。例外は上位へ。"""
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": query, "gsrnamespace": "6", "gsrlimit": "12",
        "prop": "imageinfo", "iiprop": "url|mime|size", "iiurlwidth": "1280",
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
            cands.append((p.get("index", 999), turl))
    cands.sort()
    return [t for _, t in cands], diag


def fetch_from_wikimedia(query: str) -> bytes:
    """検索→実写候補(jpeg/png・横長・十分なサイズ)を順に試し、最初に取れた画像bytesを返す。
    長い説明的クエリは Commons で0件になりやすいので、段階的に短縮した候補も試す。"""
    last_err: Exception | None = None
    last_diag = None
    for q in _shorten(query):
        for attempt in range(2):
            if attempt:
                time.sleep(attempt * 3)
            try:
                urls, diag = _search_candidates(q)
                last_diag = diag
                for turl in urls[:6]:
                    try:
                        b = _get(turl)
                        if len(b) < MIN_IMAGE_BYTES:
                            continue
                        if not _is_color_photo(b):      # 白黒/セピア=実写サムネに使わない
                            diag["mono"] = diag.get("mono", 0) + 1
                            continue
                        return b
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
        tried = [jp] if jp else ([en] if en else [])
        data = None
        used = None
        last = None
        for q in tried:
            try:
                data = fetch_from_wikimedia(q)
                used = q
                break
            except Exception as e:
                last = e
        if data:
            out.write_bytes(data)
            prov[stem] = "wikimedia"
            save_prov(prov)
            print(f"  ✓ {out.name}  ← '{used}'  ({len(data)//1024} KB)")
            ok += 1
        else:
            print(f"  ✗ {stem}  (tried {tried}): {type(last).__name__ if last else '?'} — {str(last)[:160] if last else ''}")
            fail += 1
        time.sleep(1.0)  # Commons への礼儀＝ペース調整
    print(f"\n成功: {ok} / 失敗: {fail}")


if __name__ == "__main__":
    main()
