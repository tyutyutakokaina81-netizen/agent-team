#!/usr/bin/env python3
"""
add_thumbnail_prompts.py — 記事ごとに実写風サムネ生成プロンプトを末尾に追記する。

ルール:
- 既に "Photorealistic" / "サムネ用プロンプト" / "実写生成プロンプト" を含む記事はスキップ
- カテゴリ判定（食/富山地理/AI実用/思想暮らし/文化場所）→ テンプレ選択
- タイトルから主題を抽出して埋め込む
- 末尾に "## サムネ用プロンプト" セクションを追記
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ARTICLES_DIR = REPO / "CMO" / "outputs"

ALREADY_PATTERNS = (
    "Photorealistic", "photorealistic",
    "## サムネ用プロンプト",
    "## サムネ", "実写生成プロンプト", "実写プロンプト",
)

# ---- カテゴリ判定キーワード ----
FOOD_KW = (
    "ラーメン", "うどん", "そば", "寿司", "刺身", "丼", "かまぼこ", "豆腐",
    "魚", "ブリ", "フクラギ", "ノドグロ", "ホタルイカ", "白えび", "鱒", "鯛",
    "せんべい", "和菓子", "薄氷", "コロッケ", "ビール", "地酒", "出汁", "昆布",
    "干物", "わかめ", "黒造り", "へしこ", "おでん", "大根", "山菜", "ぶり大根",
    "とろろ", "椀", "市場", "唐揚", "そうめん", "素麺", "かぶら寿司", "弁当", "朝食",
)
TOYAMA_PLACE_KW = (
    "高岡", "富山", "氷見", "雨晴", "新湊", "北陸", "五箇山", "瑞龍寺", "古城公園",
    "万葉", "称名", "おとぎの森", "潮風ギャラリー", "御清水庵", "ほりい",
)
TECH_KW = (
    "AI", "Claude", "ChatGPT", "プロンプト", "請求書", "サブスク", "ツール",
    "コード", "5つの役職", "AIと働く",
)
SOLO_KW = (
    "フリーランス", "ひとり起業", "ひとり会社", "個人事業", "営業", "顧客の声",
    "月10万", "月30万", "失敗", "辞める基準", "テンプレ", "Vol",
    "有料記事", "発信", "海外", "個人が会社", "メンバーシップ",
)
LIFE_KW = (
    "月曜", "火曜", "水曜", "木曜", "金曜", "土曜", "日曜",
    "朝", "夜", "週末", "昼休み", "ルーティン", "メール整理", "週次振り返り",
    "孤独", "気力", "整え方", "ディープワーク", "やらない", "予習", "棚卸し",
    "時給", "本ベスト", "観光地に住んで",
)
CULTURE_KW = (
    "藤子", "笑ゥせぇるすまん", "ドラえもん", "銅器", "工房", "万葉線", "路面電車",
    "結婚式", "引き出物", "祭", "風習", "婚礼", "職人", "国宝",
)

def detect_category(title: str, body: str) -> str:
    text = title + " " + body[:600]
    if any(k in text for k in FOOD_KW):
        return "food"
    if any(k in text for k in CULTURE_KW):
        return "culture"
    if any(k in text for k in TOYAMA_PLACE_KW):
        return "place"
    if any(k in text for k in TECH_KW):
        return "tech"
    if any(k in text for k in SOLO_KW):
        return "solo"
    if any(k in text for k in LIFE_KW):
        return "life"
    return "essay"

def extract_title(md_text: str) -> str:
    m = re.search(r"^## タイトル\s*\n```\s*\n(.+?)\n```", md_text, re.MULTILINE | re.DOTALL)
    if m:
        return m.group(1).strip().splitlines()[0]
    m = re.search(r"^#\s+note記事[:：]\s*(.+)$", md_text, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return ""

def extract_body_head(md_text: str) -> str:
    m = re.search(r"^## 本文\s*\n```\s*\n(.+?)\n```", md_text, re.MULTILINE | re.DOTALL)
    return m.group(1).strip()[:800] if m else ""

# ---- カテゴリ別 写真プロンプト テンプレ ----
TEMPLATES = {
    "food": (
        'Photorealistic close-up of {subject_en}, served on a simple ceramic '
        'or wooden plate in a humble Japanese home kitchen setting. Natural '
        'window light from the side, soft shadows, slight steam if the dish '
        'is hot. Authentic everyday Japanese food photography style — not '
        'styled restaurant glamour, more like a careful family meal documented '
        'with care. Shallow depth of field, top-down 3/4 angle. No people, '
        'no text, no logos. 16:9 aspect ratio.'
    ),
    "place": (
        'Photorealistic landscape photograph of {subject_en} in Toyama '
        'Prefecture, Japan. Capture a quiet, lived-in atmosphere — locals '
        'going about ordinary life rather than tourist crowds. Natural '
        'daylight, slight overcast or golden-hour warmth. Documentary travel '
        'photography style, balanced composition, sense of place. No '
        'recognizable individual faces, no text, no logos. 16:9 aspect ratio.'
    ),
    "culture": (
        'Photorealistic image evoking {subject_en} — a traditional Japanese '
        'cultural element from Toyama / Hokuriku region. Focus on craft, '
        'texture, and material — wood, metal, paper, fabric, food, or stone '
        'as appropriate. Warm directional lighting that emphasizes surface '
        'detail. Documentary craft photography style. No people in focus, '
        'no readable text, no logos. 16:9 aspect ratio.'
    ),
    "tech": (
        'Photorealistic overhead workspace photo: a modern minimalist desk '
        'with a laptop showing a generic chat-style interface (no readable '
        'text), a notebook, a coffee mug, and warm directional natural light '
        'from one side. Suggests calm focused solo work involving AI tools. '
        'Slight aspirational but grounded mood. No people visible (hands at '
        'most), no logos, no readable text. 16:9 aspect ratio.'
    ),
    "solo": (
        'Photorealistic close-up of a solo worker\'s desk in a small home '
        'office: laptop slightly open, notebook with handwritten lines, a '
        'mug of coffee or tea, a window letting in soft natural light. Theme: '
        '{subject_en}. Calm, candid, lived-in atmosphere — not a stock photo '
        'staged scene. Shallow depth of field. No readable text, no logos, '
        'no faces visible. 16:9 aspect ratio.'
    ),
    "life": (
        'Photorealistic candid lifestyle photo capturing a quiet domestic '
        'moment in a Japanese home: soft natural light through a window, a '
        'simple wooden table, a paper notebook, a ceramic mug. Mood: {subject_en}. '
        'Calm, slightly contemplative, documentary feel rather than staged. '
        'No people in focus (hands at most). No text, no logos. 16:9 aspect ratio.'
    ),
    "essay": (
        'Photorealistic minimal still life evoking the essay\'s theme: '
        '{subject_en}. Natural window light, simple wooden or paper surface, '
        'one or two carefully placed everyday objects (notebook, pen, mug, '
        'plant). Slight cinematic mood. Documentary photography style, not '
        'commercial. No people, no readable text, no logos. 16:9 aspect ratio.'
    ),
}

# ---- 主題（英訳）テーブル ----
SUBJECT_HINTS = {
    "ラーメン": "a bowl of dark soy-broth Japanese ramen with chashu and green onions",
    "うどん": "a bowl of thin handmade udon noodles in light kombu broth",
    "そば": "a wooden tray of cold soba noodles with grated daikon and dipping sauce",
    "鱒寿司": "a circular wooden frame of pink trout pressed sushi wrapped in bamboo leaves",
    "寿司": "carefully arranged pieces of nigiri sushi on a wooden block",
    "刺身": "a plate of fresh sliced sashimi with shiso leaf and grated wasabi",
    "白えび丼": "a bowl of Toyama white shrimp sashimi rice bowl, translucent shrimp piled on rice",
    "白えびせんべい": "Toyama white shrimp rice crackers in a small ceramic dish",
    "白えび": "small translucent Toyama bay white shrimp on a dark plate",
    "ノドグロ": "a salt-grilled blackthroat seaperch with crisp skin on a ceramic plate",
    "ブリ大根": "a clay pot of slow-simmered yellowtail and daikon in dark broth",
    "ぶり大根": "a clay pot of slow-simmered yellowtail and daikon in dark broth",
    "フクラギ": "salt-grilled young yellowtail slice on a small ceramic plate",
    "ホタルイカ": "firefly squid glowing faintly blue on a dark Toyama beach at night",
    "かまぼこ": "a large pink-and-red ceremonial sea bream made of kamaboko fish cake on gold paper",
    "細工かまぼこ": "a large pink-and-red ceremonial sea bream made of kamaboko on gold paper",
    "薄氷": "delicate translucent Toyama wagashi sweets called Usugori, like thin ice flakes",
    "豆腐": "a thick block of firm Gokayama tofu tied with straw rope on a wooden board",
    "五箇山豆腐": "a thick block of firm Gokayama tofu tied with straw rope, mountain village setting",
    "コロッケ": "a freshly fried golden croquette on a piece of brown paper, hometown butcher shop style",
    "高岡コロッケ": "freshly fried golden croquettes on brown paper at a small Takaoka butcher shop",
    "干物": "salted dried fish on a bamboo rack catching morning sun by the sea",
    "氷見": "the calm fishing port of Himi on Toyama Bay at dawn with boats",
    "わかめ": "dark green dried Toyama seaweed in a wooden bowl",
    "黒造り": "jet-black squid ink fermented squid paste in a small ceramic dish",
    "へしこ": "salted rice-bran-fermented mackerel on a wooden cutting board, traditional Hokuriku preserve",
    "おでん": "a steaming pot of Toyama-style oden with daikon, egg, kamaboko in pale broth",
    "大根": "a thick slice of slow-simmered daikon radish in clear kombu broth",
    "山菜": "freshly foraged Japanese mountain vegetables (sansai) on a bamboo basket",
    "とろろ": "shaved tororo kombu seaweed in a small ceramic bowl with hot rice",
    "とろろ昆布": "shaved tororo kombu seaweed in a small ceramic bowl beside a rice bowl",
    "昆布じめ": "translucent kombu-cured sashimi slices on a wooden board, kombu sheets nearby",
    "昆布": "dried Hokkaido-style kombu sheets stacked on a wooden board",
    "ます寿司": "a circular wooden frame of pink trout pressed sushi wrapped in bamboo leaves",
    "鯛": "a large ceremonial sea bream displayed on gold paper, Toyama wedding gift style",
    "かぶら寿司": "fermented turnip and yellowtail kabura-zushi on a ceramic plate, winter preserve",
    "そうめん": "delicate hand-pulled white somen noodles coiled in a glass bowl with ice water",
    "素麺": "delicate hand-pulled white somen noodles coiled in a glass bowl with ice water",
    "大門素麺": "tightly coiled topknot-shaped Daimon somen noodles in their traditional package",
    "唐揚定食": "a generous Japanese karaage fried chicken set meal with rice and miso soup",
    "ビール": "a glass of locally brewed Toyama craft beer with condensation, dim pub setting",
    "地酒": "a small ceramic sake cup beside a sake bottle, dim tatami room",
    "市場": "early morning at a Toyama fishing harbor market with boxes of fresh fish",
    "新湊": "early morning at Shinminato Kitto market in Toyama with fresh fish on ice",
    "雨晴": "the Amaharashi coast of Toyama at dawn with snow-capped Tateyama mountains across the bay",
    "雨晴海岸": "Amaharashi coast at sunrise, calm sea reflecting distant Tateyama mountain range",
    "瑞龍寺": "the wide stone-paved courtyard of Zuiryuji Zen temple in Takaoka, quiet morning",
    "古城公園": "the moats and old stone walls of Takaoka Castle Park covered in cherry blossoms",
    "高岡古城公園": "the moats and stone walls of Takaoka Castle Park with cherry blossoms",
    "万葉線": "a small green-and-cream local tram of the Manyo Line running through central Takaoka",
    "高岡銅器": "a craftsman's worn hands working a Takaoka bronze casting in a dim workshop",
    "高岡大仏": "the towering green-bronze Great Buddha of Takaoka against a cloudy sky",
    "おとぎの森": "the open green lawn of Otogi-no-Mori park in Takaoka with playful Doraemon statues in soft sunlight",
    "潮風ギャラリー": "a quiet small-town museum interior in Himi devoted to manga artist Fujiko Fujio A",
    "笑ゥせぇるすまん": "a small mid-century Showa-era Japanese parlor scene evoking the world of Warau Salesman manga",
    "藤子": "a quiet small-town museum corner devoted to Fujiko Fujio in Hokuriku Japan",
    "ドラえもん": "playful Doraemon-themed bronze statues in a green park in Takaoka, sunny afternoon",
    "万葉集": "a small wooden plaque with classical Japanese calligraphy beside the Manyo Line tram",
    "称名": "the towering Shomyo waterfall in Toyama Tateyama range, mist rising at the base",
    "高岡": "a quiet street in central Takaoka with old wooden buildings and a passing tram",
    "御清水庵": "a rustic Fukui soba restaurant interior with a wooden tray of cold zaru soba",
    "ほりい": "a small family-run Hokuriku diner table with a generous fried chicken set meal",
    "個人が会社": "a single laptop and notebook on a worn wooden desk in a small home office",
    "AIに5つの役職": "a single laptop displaying a multi-panel chat interface evoking team-of-AI workflow, warm desk light",
    "AIと働く": "a calm home office desk with a laptop, notebook, and morning coffee, soft natural light",
    "ChatGPT": "two laptops side by side at a desk, one with warm screen glow one with cool, hands typing",
    "Claude": "a calm minimal desk with a single laptop showing a generic chat interface, soft side light",
    "プロンプト": "an open notebook with three handwritten lines and a laptop in the background, morning light",
    "請求書": "a printed Japanese invoice on a wooden desk with a calculator and pen, neat composition",
    "サブスク": "a phone screen displaying a list of subscription apps (no readable text), beside a notebook and coffee",
    "時給": "a notebook with handwritten hourly calculations beside a calculator and a coffee mug",
    "テンプレ": "a small office desk with printed worksheet templates spread out, notebook and pen",
    "Vol": "a small desk with printed product mockup sheets and a coffee mug, indie-creator atmosphere",
    "失敗": "an open notebook with crossed-out lines and a fresh new page beside it, soft afternoon light",
    "辞める基準": "an open notebook with a clear handwritten list on a quiet desk, morning light through window",
    "観光地に住んで": "a quiet residential street in central Takaoka with locals walking, low light",
    "月曜": "Monday morning home office desk with a leather notebook open, coffee, soft window light",
    "火曜": "a focused weekday morning at a clean desk with laptop and notebook, deep work mood",
    "水曜": "a midweek lunch break in a small Japanese park with a homemade bento on a bench",
    "木曜": "a Thursday afternoon home office desk with an inbox-sorted screen and a tea cup, golden light",
    "金曜": "a Friday evening dim home interior with a closed laptop and a cup of tea, end-of-week calm",
    "土曜": "Saturday morning notebook with handwritten weekly review notes, sunny breakfast table",
    "日曜": "Sunday morning at a quiet home with an open notebook and slow coffee, soft warm light",
    "メール整理": "an inbox folder list on a laptop screen (no readable text) beside a notebook and pen",
    "週次振り返り": "an open notebook with weekly review jottings beside a coffee mug, calm Saturday light",
    "ディープワーク": "a single laptop on an otherwise empty desk with morning light, intense focus atmosphere",
    "孤独": "a single chair and desk by a large window in an empty room, late afternoon light, quiet mood",
    "気力": "a half-drunk cup of coffee on a desk with a closed notebook, late afternoon weariness",
    "整え方": "a tidy small Japanese home with neat shelves, plant, and morning light through curtains",
    "予習": "a small open notebook with next-week plan items handwritten, Friday evening soft light",
    "やらない": "an empty Friday evening desk with closed laptop, single small plant, calm tone",
    "棚卸し": "a notebook with a list of canceled subscription names crossed out, beside a phone",
    "本ベスト": "a small stack of five books on a wooden desk beside a coffee mug, warm reading lamp",
    "営業しないで": "a small home office desk with a notification on laptop screen (no text), warm light",
    "顧客の声": "an open notebook with bullet-point customer feedback, beside a phone showing a chat (no text)",
    "月10万": "a home office desk with a laptop showing a generic dashboard (no readable text) and a notebook",
    "月30万": "a small home office desk with a laptop, notebook, and calculator, morning planning mood",
    "海外で読まれる": "a world map on a wall behind a writer's desk with a laptop and notebook, evening lamp",
    "個人発信": "a calm home office desk with a laptop displaying a generic blog editor (no readable text)",
    "ひとり会社最初30日": "a flat-lay of noise-canceling earbuds, A4 notebook, and a smartphone on a wooden desk",
    "買ってよかった": "a flat-lay of carefully chosen everyday tools (earbuds, notebook, phone) on a wooden desk",
    "30日": "a wall calendar marked through 30 days beside a laptop and notebook on a small desk",
    "メンバーシップ": "a laptop screen showing a generic subscription page (no readable text) on a calm desk",
    "Vol1": "a printed sample template page on a wooden desk beside a coffee mug, indie-publishing mood",
    "Vol2": "a printed sample template page on a wooden desk beside a coffee mug, indie-publishing mood",
    "Vol.1": "a printed sample template page on a wooden desk beside a coffee mug, indie-publishing mood",
    "Vol.2": "a printed sample template page on a wooden desk beside a coffee mug, indie-publishing mood",
    "失敗ログ": "an open notebook with bullet-point failure notes crossed and revised, soft evening light",
    "1ヶ月で失敗": "an open notebook with handwritten retrospective notes on a small home office desk",
    "ファイル": "a laptop screen showing a single open file (no readable text) with a notebook beside, morning light",
    "専門家3人": "three small business cards on a clean desk beside a notebook and a pen, soft daylight",
    "有料記事": "a writer's quiet desk with a laptop showing a generic editor (no readable text), morning coffee",
    "観光": "a quiet morning street in a small Toyama town with a local resident walking with a shopping bag",
    "工房": "an old Takaoka copperware workshop with worn tools and warm directional light on a craftsman's hands",
    "結婚式": "a Toyama wedding reception table corner with a large pink kamaboko sea bream gift",
    "鯛切り": "a family cutting board with a large pink kamaboko sea bream being sliced ceremonially",
    "高岡銅器の工房": "a traditional Takaoka copperware workshop interior with anvils, tools, and warm tungsten light",
    "高岡銅器": "close-up of a craftsman's hands shaping a Takaoka copper bowl in a dim workshop",
}

DEFAULT_SUBJECT = {
    "food": "a humble Japanese home-cooked dish on a simple ceramic plate",
    "place": "a quiet street or natural landscape in Toyama Prefecture, Japan",
    "culture": "a traditional Japanese cultural artifact or craft from Toyama",
    "tech": "a clean minimal home office desk with a laptop and notebook",
    "solo": "a solo worker's modest desk with notebook and laptop",
    "life": "a calm domestic moment of a quiet life",
    "essay": "a quiet still life of an open notebook and a coffee mug",
}

def find_subject(title: str, body: str) -> str | None:
    # SUBJECT_HINTS の キー が title/body に含まれているかを優先度で探す
    haystack = title + " " + body[:400]
    # 長いキーから順に
    for key in sorted(SUBJECT_HINTS.keys(), key=lambda k: -len(k)):
        if key in haystack:
            return SUBJECT_HINTS[key]
    return None

def build_prompt(title: str, body: str, category: str) -> str:
    subject = find_subject(title, body) or DEFAULT_SUBJECT[category]
    return TEMPLATES[category].format(subject_en=subject)

def already_has_prompt(text: str) -> bool:
    return any(pat in text for pat in ALREADY_PATTERNS)

def process_file(path: Path, dry_run: bool) -> bool:
    text = path.read_text(encoding="utf-8")
    if already_has_prompt(text):
        return False
    title = extract_title(text)
    body = extract_body_head(text)
    category = detect_category(title, body)
    prompt = build_prompt(title, body, category)

    block = (
        f"\n## サムネ用プロンプト（実写風・画像AIに貼る）\n\n"
        f"```\n{prompt}\n```\n"
        f"\n_カテゴリ判定: `{category}` ／ 自動生成。"
        f"必要なら手動で被写体・光・背景を調整してください。_\n"
    )
    new_text = text.rstrip() + "\n" + block
    if not dry_run:
        path.write_text(new_text, encoding="utf-8")
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--pattern", default="2026-*_note記事_*.md")
    args = ap.parse_args()

    files = sorted(ARTICLES_DIR.glob(args.pattern))
    changed = 0
    skipped = 0
    for f in files:
        if process_file(f, args.dry_run):
            changed += 1
            print(f"+ {f.name}")
        else:
            skipped += 1
    mode = "(dry-run)" if args.dry_run else ""
    print(f"\n{mode} 追記: {changed} / スキップ（既存）: {skipped}")

if __name__ == "__main__":
    main()
