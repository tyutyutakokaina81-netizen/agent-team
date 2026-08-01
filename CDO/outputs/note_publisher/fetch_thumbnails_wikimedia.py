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


def _get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_from_wikimedia(query: str) -> bytes:
    """検索→実写候補(jpeg/png・横長・十分なサイズ)を順に試し、最初に取れた画像bytesを返す。"""
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": query, "gsrnamespace": "6", "gsrlimit": "20",
        "prop": "imageinfo", "iiprop": "url|mime|size", "iiurlwidth": "1280",
    }
    last_err: Exception | None = None
    for attempt in range(3):
        if attempt:
            time.sleep(attempt * 3)
        try:
            data = json.loads(_get(API + "?" + urllib.parse.urlencode(params)).decode("utf-8"))
            pages = (data.get("query") or {}).get("pages") or {}
            cands = []
            for p in pages.values():
                ii = (p.get("imageinfo") or [{}])[0]
                if ii.get("mime") not in ("image/jpeg", "image/png"):
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
            for _, turl in cands[:6]:
                try:
                    b = _get(turl)
                    if len(b) >= MIN_IMAGE_BYTES:
                        return b
                except Exception as e:
                    last_err = e
            last_err = RuntimeError(f"候補なし（query={query!r}）")
        except Exception as e:
            last_err = e
    raise last_err or RuntimeError("wikimedia 取得失敗")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--filter", default="")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--max", type=int, default=0)
    args = ap.parse_args()

    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    prov = load_prov()
    verified = load_verified()
    files = sorted(glob.glob(str(ARTICLES_DIR / "*note記事*.md")))
    files = [f for f in files if (not args.filter or args.filter in Path(f).name)]

    queue = []
    for f in files:
        p = Path(f)
        if "サムネ生成プロンプト" in p.name:
            continue
        if p.stem in verified:      # owner確認済み=絶対に上書きしない(--forceでもスキップ)
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
            print(f"  ✗ {stem}  (tried {tried}): {type(last).__name__ if last else '?'}")
            fail += 1
        time.sleep(1.0)  # Commons への礼儀＝ペース調整
    print(f"\n成功: {ok} / 失敗: {fail}")


if __name__ == "__main__":
    main()
