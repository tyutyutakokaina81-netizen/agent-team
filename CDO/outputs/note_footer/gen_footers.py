#!/usr/bin/env python3
"""
記事フッター導線ジェネレータ（CDO・2026-06-12）

各 note 記事の末尾に付ける2部構成フッターを生成する：
  1. ▼あわせて読む：公開済み記事（published_registry.tsv）から関連2本（タイトル＋URL）
  2. CTA一文：カテゴリ別に複数パターンをローテーション（テンプレ感の回避）

使い方:
    python3 gen_footers.py --embed-from 2026-06-12   # 指定日以降の記事mdの本文ブロック末尾に直接埋め込む（未公開ストック向け）
    python3 gen_footers.py --paste-until 2026-06-11  # 指定日以前の記事のフッターを footers/ に書き出す（公開済み記事にcoworkが貼る用）
    python3 gen_footers.py --dry-run ...             # 書き込まずに対象と内容を表示

ルール:
  - 自分自身へはリンクしない
  - 既に「▼ あわせて読む」を含む記事はスキップ（二重付与防止）
  - 関連選定: 同カテゴリ優先 → 高岡/旅 → 全体。記事タイトルのハッシュでローテーションし、
    全記事が同じ2本にならないようにする
"""
import argparse
import csv
import hashlib
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ARTICLES = REPO / "CMO" / "outputs"
FOOTER_MARK = "▼ あわせて読む"
NOTE_BASE = "https://note.com/safe_canna441/n/"
# 英語ガイドへの導線（North Star＝海外読者。note読者→英語ガイドへ流す・全記事フッター共通）
GUIDE_URL = "https://tyutyutakokaina81-netizen.github.io/agent-team/toyama/en.html"
GUIDE_CTA = ("🌍 For overseas readers (海外の方・海外の友人へ): a local's free English guide to "
             "Toyama, Takaoka & Himi → " + GUIDE_URL)

# 有料note（2026-08-19 公開・各¥300）。無料記事から"題材が近い1本だけ"を案内する。
# 収益の実態＝無料279本に対し有料への導線が4本しか無かった＝作った商品が発見されない状態。
# 全記事に同じ広告を貼るのでなく、記事の題材に噛み合う1本を出す（外れた案内は読者の信用を削る）。
PAID_NOTES = {
    "魚": ("富山湾の魚、地元民の選び方・旬・食べ方【保存版】",
           NOTE_BASE + "n589f9a38d45f",
           "旬・鮮度の見分け方・買い方まで、保存版にまとめました"),
    "工芸": ("高岡の手しごと、地元民の選び方と楽しみ方【保存版】",
             NOTE_BASE + "n6fae4ac8e59a",
             "銅器・錫・漆・ガラスの選び方と手入れを、保存版にまとめました"),
    "酒": ("富山の地酒、地元民の選び方と楽しみ方【保存版】",
           NOTE_BASE + "n9d31ee9d3b0a",
           "料理と温度で選ぶ考え方を、保存版にまとめました"),
}
# 題材の近さで選ぶ（上から順に判定）。どれにも当たらなければ有料案内は出さない＝無理に売らない。
PAID_MATCH = [
    ("酒",   ["酒", "地酒", "日本酒", "ビール", "甘酒", "晩酌", "焼酎", "ワイン"]),
    ("魚",   ["魚", "刺身", "寿司", "鮨", "ブリ", "フクラギ", "ノドグロ", "白えび", "ホタルイカ",
              "バイ貝", "かに", "ずわい", "干物", "昆布じめ", "昆布締め", "牡蠣", "いか", "イカ",
              "海鮮", "漁", "富山湾", "鱒", "へしこ", "たら汁", "アラ", "キス", "メゴチ", "鮎", "マグロ"]),
    ("工芸", ["銅器", "鋳物", "錫", "漆", "ガラス", "工芸", "職人", "手しごと", "金屋町", "高岡大仏"]),
]
# 字面だけ一致して題材が違うものを弾く（実測した誤爆）。
# 例：「金魚すくい」「魚津の蜃気楼（地名）」に魚の買い方ガイドを出すのは読者の信用を削る。
PAID_EXCLUDE = ["金魚", "魚津", "不器用"]


def pick_paid(title: str, category: str):
    """記事の題材に噛み合う有料note を1本返す。当たらなければ None（＝案内しない）。"""
    if any(x in title for x in PAID_EXCLUDE):
        return None
    for key, words in PAID_MATCH:
        if any(w in title for w in words):
            return PAID_NOTES[key]
    # 題材語で当たらない食記事は、いちばん広く効く「魚」を出す（富山の食＝富山湾が土台のため）。
    if category == "食":
        return PAID_NOTES["魚"]
    return None

FOOD = ["食", "丼", "寿司", "うどん", "そば", "そうめん", "ラーメン", "おでん", "大根", "昆布", "かまぼこ",
        "ブリ", "フクラギ", "ノドグロ", "白えび", "ホタルイカ", "バイ貝", "鮎", "かに", "ずわい", "干物",
        "へしこ", "黒造り", "豆腐", "薄氷", "柿", "煮", "汁", "コロッケ", "せんべい", "和菓子", "地酒",
        "ビール", "鱒", "たら汁", "よごし", "唐揚", "定食", "ミルク", "おやつ", "酒"]
PLACE = ["公園", "駅", "町", "川", "峡", "滝", "海岸", "大仏", "瑞龍寺", "万葉線", "city", "市場",
         "金屋町", "山町", "古城", "雨晴", "内川", "蜃気楼", "ギャラリー", "運河", "環水", "遊覧",
         "氷見", "新湊", "庄川", "魚津", "立山", "二上", "散歩", "歩く"]
BIZ = ["フリーランス", "ひとり", "AI", "仕事", "起業", "会社", "発信", "有料", "テンプレ", "収支",
       "請求書", "時給", "メール", "ファイル", "振り返り", "失敗", "月30万", "営業", "顧客",
       "孤独", "整え", "リセット", "やらない", "ルーティン", "専門家", "ChatGPT", "Claude", "役職", "週"]


def classify(title: str) -> str:
    def hit(words):
        return any(w in title for w in words)
    if hit(FOOD):
        return "食"
    if hit(PLACE):
        return "場所"
    if hit(BIZ):
        return "仕事"
    return "場所"  # 高岡/富山ネタが大半のため


def load_registry():
    rows = []
    with open(HERE / "published_registry.tsv", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            rows.append(row)
    return rows


# カテゴリ別CTA（ローテーション・テンプレ感回避のため複数パターン）
CTAS = {
    "食": [
        "富山・高岡の食の話は、ほかにも書いています。フォローすると毎日届きます。",
        "住んでいる町の食べ物の話を、毎日すこしずつ書いています。気に入ったらフォローどうぞ。",
        "次はどの富山の味の話にするか考え中です。フォローして待っていてもらえたら。",
        "選び方や旬をもっと詳しく知りたい方向けに、保存版の有料記事も書いています。プロフィールからどうぞ。",
    ],
    "場所": [
        "高岡・富山の歩ける場所の話を、住人目線で書き続けています。フォローすると毎日届きます。",
        "観光ガイドに載らない町の景色を、これからも書いていきます。よければフォローを。",
        "この町の別の場所の話も書いています。プロフィールからどうぞ。",
        "旅行前にもっと詳しく知りたい方向けに、保存版の有料ガイドも書いています。プロフィールからどうぞ。",
    ],
    "仕事": [
        "ひとり仕事×AIの実践記を毎日書いています。収支管理テンプレも note で販売中です（プロフィールから）。",
        "フリーランスの実務で使っているテンプレートを note で販売しています。詳しくはプロフィールへ。",
        "AIと一緒に働く日々の記録を毎日更新中。フォローすると朝に届きます。",
    ],
}


def pick_related(category: str, self_title: str, registry):
    pool = [r for r in registry if r["category"] == category and r["title"] != self_title]
    if len(pool) < 2:
        extra = [r for r in registry if r["category"] in ("旅", "場所") and r["title"] != self_title
                 and r not in pool]
        pool += extra
    if len(pool) < 2:
        pool += [r for r in registry if r["title"] != self_title and r not in pool]
    h = int(hashlib.md5(self_title.encode()).hexdigest(), 16)
    i = h % len(pool)
    j = (h // 7 + 1 + i) % len(pool)
    if j == i:
        j = (i + 1) % len(pool)
    return pool[i], pool[j]


def build_footer(title: str) -> str:
    registry = load_registry()
    cat = classify(title)
    a, b = pick_related(cat, title, registry)
    h = int(hashlib.md5(title.encode()).hexdigest(), 16)
    cta = CTAS[cat][h % len(CTAS[cat])]
    paid = pick_paid(title, cat)
    paid_block = ""
    if paid:
        p_title, p_url, p_desc = paid
        paid_block = f"\n📘 {p_desc}。\n・{p_title}\n{p_url}\n"
    return (
        "\n---\n\n"
        f"{FOOTER_MARK}\n"
        f"・{a['title']}\n{NOTE_BASE}{a['note_id']}\n"
        f"・{b['title']}\n{NOTE_BASE}{b['note_id']}\n"
        f"{paid_block}\n"
        f"{cta}\n\n"
        f"{GUIDE_CTA}"
    )


def article_files():
    return sorted(p for p in ARTICLES.glob("*_note記事_*.md")
                  if p.is_file() and "サムネ" not in p.name)


def get_title(text: str, path: Path) -> str:
    m = re.search(r"##\s*タイトル.*?\n```\n(.+?)\n```", text, re.S)
    if m:
        return m.group(1).strip().splitlines()[0]
    m = re.search(r"^#\s*note記事[：:](.+)$", text, re.M)
    if m:
        return m.group(1).strip()
    return path.stem.split("_note記事_", 1)[-1]


def embed(path: Path, dry: bool) -> str:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"(##\s*本文.*?\n```\n)(.+?)(\n```)", text, re.S)
    if not m:
        return "no-body"
    if FOOTER_MARK in m.group(2):
        return "skip(already)"
    title = get_title(text, path)
    footer = build_footer(title)
    new_body = m.group(1) + m.group(2) + "\n" + footer + m.group(3)
    if not dry:
        path.write_text(text[:m.start()] + new_body + text[m.end():], encoding="utf-8")
    return "embedded"


def paste_file(path: Path, outdir: Path, dry: bool) -> str:
    text = path.read_text(encoding="utf-8")
    title = get_title(text, path)
    footer = build_footer(title)
    out = outdir / (path.stem + ".footer.txt")
    if not dry:
        outdir.mkdir(exist_ok=True)
        out.write_text(f"# 貼り付け先: {title}\n# note編集画面で本文の最後に以下を貼る\n{footer}\n", encoding="utf-8")
    return f"paste -> {out.name}"


def build_paid_footer(title: str):
    """公開済み記事に後から貼る用の、有料note案内だけの短いブロック。

    「▼あわせて読む」を外す理由：published_registry.tsv がまだ14件しかなく、
    数百本に貼ると同じ14本が延々と並んで逆効果になる。ここでの目的は
    無料→有料の導線を通すことなので、噛み合う1本と英語ガイドだけに絞る。
    """
    paid = pick_paid(title, classify(title))
    if not paid:
        return None
    p_title, p_url, p_desc = paid
    return (
        "\n---\n\n"
        f"📘 {p_desc}。\n"
        f"・{p_title}\n{p_url}\n\n"
        f"{GUIDE_CTA}"
    )


def paste_paid(path: Path, outdir: Path, dry: bool) -> str:
    text = path.read_text(encoding="utf-8")
    title = get_title(text, path)
    footer = build_paid_footer(title)
    if not footer:
        return "skip(噛み合う有料noteなし)"
    out = outdir / (path.stem + ".paid.txt")
    if not dry:
        outdir.mkdir(parents=True, exist_ok=True)
        out.write_text(f"# 貼り付け先: {title}\n# note編集画面で本文の最後に以下を貼る\n{footer}\n",
                       encoding="utf-8")
    return f"paid -> {out.name}"


def _norm(s: str) -> str:
    return re.sub(r"[\s—\-–、。「」『』【】…!！?？]", "", s)


def write_manifest(dry: bool) -> int:
    """append_paid_footer.py が読む manifest を書き出す。

    published_registry.json（公開時に note_id が記録される）とタイトルで突合し、
    「どの記事に・どの文面を貼るか」を機械可読にする。突合できない記事は載せない
    （note_id が無いと編集画面を開けないため）。
    """
    import json
    reg_path = REPO / "CDO" / "outputs" / "note_publisher" / "published_registry.json"
    reg = json.loads(reg_path.read_text(encoding="utf-8")) if reg_path.exists() else []
    indexed = [(_norm(r["title"]), r) for r in reg if r.get("url")]

    items = []
    for p in article_files():
        title = get_title(p.read_text(encoding="utf-8"), p)
        footer = build_paid_footer(title)
        if not footer:
            continue
        nt = _norm(title)
        hit = next((r for k, r in indexed
                    if k == nt or (len(nt) > 10 and (nt in k or k in nt))), None)
        if not hit:
            continue
        note_id = hit["url"].rstrip("/").split("/")[-1]
        items.append({"note_id": note_id, "title": title, "stem": p.stem, "footer": footer})
    if not dry:
        (HERE / "paid_footer_manifest.json").write_text(
            json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    return len(items)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--embed-from", help="この日付以降（ファイル名）の記事に直接埋め込む")
    ap.add_argument("--paste-until", help="この日付以前の記事のフッターを footers/ に出力")
    ap.add_argument("--paid-only", action="store_true",
                    help="公開済み記事に貼る「有料note案内だけ」のブロックを paid_footers/ に出力")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.paid_only:
        made = 0
        for p in article_files():
            r = paste_paid(p, HERE / "paid_footers", args.dry_run)
            if r.startswith("paid"):
                made += 1
        print(f"有料導線ブロックを {made} 本ぶん出力しました → {HERE / 'paid_footers'}")
        n = write_manifest(args.dry_run)
        print(f"追記スクリプト用マニフェストを出力しました（{n}本・公開URL判明分）→ "
              f"{HERE / 'paid_footer_manifest.json'}")
        print("  次: python3 CDO/outputs/note_footer/append_paid_footer.py --apply --limit 2")
        return

    for p in article_files():
        date = p.name[:10]
        if args.embed_from and date >= args.embed_from:
            print(f"{p.name}: {embed(p, args.dry_run)}")
        elif args.paste_until and date <= args.paste_until:
            print(f"{p.name}: {paste_file(p, HERE / 'footers', args.dry_run)}")


if __name__ == "__main__":
    main()
