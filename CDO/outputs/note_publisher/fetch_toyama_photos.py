#!/usr/bin/env python3
"""
富山ガイド各記事に「内容に応じたフリー写真(Pexels)」を入れる。
- code はネット遮断(A1)のため、これは GitHub Actions(ネット可)で動かす想定。
- 各記事の stem に対応する検索ワードで Pexels を引き、landscape写真を1枚取得。
  apps/toyama-guide/photos/<stem>.jpg に保存し、
  (a) og:image / JSON-LD image を その写真に差し替え
  (b) 最初の </h1> 直後に hero <img> を挿入（記事本体にも写真）
- 冪等：既に photos/<stem>.jpg を参照済みのページはスキップ。
- 写真が取れない記事は、既存の文字OG画像のまま据え置き（壊さない）。

ローカル検証モード:
  python3 fetch_toyama_photos.py --selftest
    → Pexelsを呼ばず、既存 og/<stem>.png を photos/<stem>.jpg にコピーして
      HTML書き換えを実行し、妥当性だけ確認する（ネット不要）。
本番(Actions):
  PEXELS_API_KEY=xxxx python3 fetch_toyama_photos.py
"""
import os, re, sys, json, shutil, html, urllib.request, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GUIDE = ROOT / "apps" / "toyama-guide"
PHOTOS = GUIDE / "photos"
BASE = "https://tyutyutakokaina81-netizen.github.io/agent-team/toyama"

# 記事 stem → Pexels検索ワード（内容に応じた・無難で被写体が確実に取れる語に）
QUERY = {
    # --- 食(日本語) ---
    "benizuwai":"snow crab seafood", "kanburi":"yellowtail fish sashimi",
    "kamaboko":"japanese fish cake", "genge":"dried fish", "baigai":"sea snail shellfish",
    "kombu":"kombu seaweed", "kombujime":"sashimi", "jibeer":"craft beer glass",
    "jizake":"japanese sake", "masuzushi":"trout sushi", "hotaruika":"squid sea japan",
    "shiroebi":"shrimp sashimi", "toyama-black":"ramen bowl", "himi-fish":"fish market japan",
    "himono":"dried fish grilled", "omiyage":"japanese souvenir gift", "sweets":"japanese sweets",
    "rice":"rice field japan", "ochugen-gift":"japanese gift box", "furusato-nozei":"japanese seafood",
    "takaoka-craft":"bronze metal craft",
    # --- 旅・景観 ---
    "en-himi":"sea of japan mountains", "himi-hattori":"japan fishing town sea",
    "en-takaoka":"japan old town temple", "en-amaharashi":"japan coast mountains sunrise",
    "en-alpine":"japan alps snow mountains", "en-gokayama":"thatched village japan snow",
    "en-toyama-city":"japan city tram", "en-daytrip":"sea of japan coast",
    "en-itinerary":"japan travel train", "en-access":"shinkansen train japan",
    "en-when-to-go":"japan four seasons mountains", "en-vs-kanazawa":"japanese garden city",
    "en-things-to-do":"toyama japan landscape", "en":"sea of japan coast mountains",
    "en-food":"japanese seafood", "en-shiroebi":"shrimp sashimi",
    "en-hattori":"japan fishing port", "en-doraemon":"japan city tram",
    "en-manga-pilgrimage":"japan retro town", "novel":"ocean view kitchen window",
    # --- 旅・計画（2026-06-26 追加：未登録ページのサムネ修正） ---
    "en-where-to-stay":"japanese ryokan room", "en-worth-visiting":"japan sea mountains landscape",
    "en-getting-around":"japan tram station", "en-rail-pass":"shinkansen train japan",
    "en-car-rental":"countryside road japan", "en-faq":"toyama japan landscape",
    "en-shirakawa-go":"thatched village japan", "en-alpine-cost":"japan snow corridor mountains",
    # --- 季節 ---
    "en-autumn":"japan autumn foliage mountains", "en-spring":"japan cherry blossom mountains",
    "en-summer":"japan green mountains river", "en-winter":"japan snow mountains sea",
    # --- 景観・名所 ---
    "en-kurobe-gorge":"mountain gorge river autumn", "en-shomyo-falls":"tall waterfall japan",
    "en-zuiryuji":"japanese zen temple", "en-off-beaten-path":"japan rural countryside",
    "en-onsen":"japanese onsen hot spring", "en-glass-art":"glass art museum",
    "en-days-2-3":"japan travel train", "en-how-many-days":"japan travel train",
    # --- 食（英語） ---
    "en-crab":"snow crab seafood", "en-sake":"japanese sake", "en-masuzushi":"trout sushi",
    "en-firefly-squid":"squid sea japan", "en-toyama-black":"black ramen bowl",
    "en-onigiri-kelp":"rice ball onigiri",
    # --- 食（日本語・漏れ） ---
    "ikagurozukuri":"squid seafood", "tororo-gohan":"rice bowl japanese",
    # --- 多言語Toyama概要・漫画聖地（著作権キャラ回避＝町並み写真） ---
    "de-toyama":"sea of japan coast mountains", "fr-toyama":"sea of japan coast mountains",
    "es-toyama":"sea of japan coast mountains", "about":"toyama japan landscape",
    "zh-toyama":"sea of japan coast mountains", "zh-tw-toyama":"sea of japan coast mountains",
    "ko-toyama":"sea of japan coast mountains",
    "ko-manga":"japan retro town tram", "zh-manga":"japan retro town tram",
    "zh-tw-manga":"japan retro town tram",
}

def pexels_photo(query, key):
    url = "https://api.pexels.com/v1/search?" + urllib.parse.urlencode(
        {"query":query, "per_page":1, "orientation":"landscape", "size":"medium"})
    req = urllib.request.Request(url, headers={"Authorization":key})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    photos = data.get("photos") or []
    if not photos: return None, None
    src = photos[0]["src"]
    img_url = src.get("large") or src.get("landscape") or src.get("original")
    credit = photos[0].get("photographer","Pexels")
    return img_url, credit

def download(img_url, dest):
    req = urllib.request.Request(img_url, headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r, open(dest,"wb") as f:
        shutil.copyfileobj(r, f)

def rewrite_html(path: Path, stem: str, alt: str) -> bool:
    s = path.read_text(encoding="utf-8"); o = s
    photo_rel = f"photos/{stem}.jpg"
    photo_url = f"{BASE}/{photo_rel}"
    if photo_rel in s:   # 冪等
        return False
    # (a) og:image / JSON-LD image を 文字OG(og/<stem>.png) から 写真(photos/<stem>.jpg) へ
    s = s.replace(f"{BASE}/og/{stem}.png", photo_url)
    # (b) 最初の </h1> 直後に hero画像を挿入
    hero = (f'\n<img src="{photo_rel}" alt="{html.escape(alt)}" loading="lazy" '
            f'style="width:100%;height:auto;border-radius:12px;margin:12px 0;display:block">')
    if "</h1>" in s:
        s = s.replace("</h1>", "</h1>"+hero, 1)
    if s != o:
        path.write_text(s, encoding="utf-8"); return True
    return False

def main():
    selftest = "--selftest" in sys.argv
    key = os.environ.get("PEXELS_API_KEY","")
    if not selftest and not key:
        sys.exit("PEXELS_API_KEY が未設定です（Actionsのsecretsに登録してください）。")
    PHOTOS.mkdir(exist_ok=True)
    done=skip=fail=0
    for f in sorted(GUIDE.glob("*.html")):
        stem=f.stem
        if stem=="index": continue   # 日本語ハブは別管理（カード型）なので対象外
        # 自動連携：QUERYに無い新規ページも必ずサムネが付くよう、安全な既定値でフォールバック
        # （以後ページを追加してもサムネ登録漏れで穴があかない＝手作業の保険）
        q=QUERY.get(stem) or "toyama japan landscape"
        dest=PHOTOS/f"{stem}.jpg"
        tm=re.search(r"<title>(.*?)</title>", f.read_text(encoding='utf-8'), re.S)
        alt=re.split(r"[｜|]", html.unescape(tm.group(1)))[0].strip() if tm else stem
        if not dest.exists():
            try:
                if selftest:
                    src=GUIDE/"og"/f"{stem}.png"
                    if src.exists(): shutil.copyfile(src,dest)
                    else: skip+=1; continue
                else:
                    img_url,_=pexels_photo(q,key)
                    if not img_url: fail+=1; continue
                    download(img_url,dest)
            except Exception as e:
                print("取得失敗:",stem,e); fail+=1; continue
        if rewrite_html(f, stem, alt): done+=1
        else: skip+=1
    print(f"写真挿入: {done} / スキップ: {skip} / 失敗: {fail}")

if __name__=="__main__":
    main()
