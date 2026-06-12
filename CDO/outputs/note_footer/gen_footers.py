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
    ],
    "場所": [
        "高岡・富山の歩ける場所の話を、住人目線で書き続けています。フォローすると毎日届きます。",
        "観光ガイドに載らない町の景色を、これからも書いていきます。よければフォローを。",
        "この町の別の場所の話も書いています。プロフィールからどうぞ。",
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
    return (
        "\n---\n\n"
        f"{FOOTER_MARK}\n"
        f"・{a['title']}\n{NOTE_BASE}{a['note_id']}\n"
        f"・{b['title']}\n{NOTE_BASE}{b['note_id']}\n\n"
        f"{cta}"
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--embed-from", help="この日付以降（ファイル名）の記事に直接埋め込む")
    ap.add_argument("--paste-until", help="この日付以前の記事のフッターを footers/ に出力")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    for p in article_files():
        date = p.name[:10]
        if args.embed_from and date >= args.embed_from:
            print(f"{p.name}: {embed(p, args.dry_run)}")
        elif args.paste_until and date <= args.paste_until:
            print(f"{p.name}: {paste_file(p, HERE / 'footers', args.dry_run)}")


if __name__ == "__main__":
    main()
