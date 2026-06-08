#!/usr/bin/env python3
"""note記事の品質監査ツール（依存ゼロ）。

CMO/outputs/*_note記事_*.md を走査し、各記事について
  - 英語セクションの有無（「## English」「For English readers」等 複数書式を検出）
  - 事実検証ノートの有無
  - じゃらんPR表記＋アフィリリンクの有無
  - 地元/旅行/食・文化 か 国内向け（実務/エッセイ）か の分類
を判定する。North Star（海外読者）直結なのは「地元系で英語/PRが欠落」の記事だけ。

背景: 2026-06-08、素朴な grep が「For English readers」形式を拾えず英語欠落を
49本と誤検知（実際の地元系欠落はほぼ0）。同種の誤検知を防ぐための正本ツール。

使い方:
  python3 ops/audit_articles.py            # サマリ＋真のギャップのみ表示
  python3 ops/audit_articles.py --verbose  # 全記事の判定を表示
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "CMO" / "outputs"

# 地元/旅行/食・文化を示すキーワード（含まれれば海外読者向け＝英語/PRが要る）
LOCAL_KW = [
    "高岡", "富山", "氷見", "五箇山", "雨晴", "新湊", "砺波", "井波", "八尾", "庄川", "二上",
    "ドラえもん", "藤子", "笑ゥせぇるすまん", "万葉線", "瑞龍寺", "勝興寺", "高岡大仏", "古城公園",
    "白えび", "ホタルイカ", "ぶり", "寒ブリ", "ノドグロ", "昆布", "かまぼこ", "富山ブラック",
    "氷見うどん", "氷見牛", "コロッケ", "鱒寿司", "ます寿司", "かぶら", "へしこ", "バイ貝", "ゲンゲ",
    "岩がき", "大門素麺", "白川郷", "合掌", "立山", "銅器", "漆器", "和紙", "彫刻", "そば", "鮎",
    "市場", "海岸", "灯台", "倶利伽羅", "称名滝", "Takaoka", "Toyama", "Himi", "Gokayama",
    "Doraemon", "Kanazawa", "Shirakawa",
]

EN_PATTERNS = [
    r"##\s*english", r"for\s+english\s+readers", r"english\s+(summary|version|readers)",
    r"🌏", r"primary\s*[—-]\s*travel", r"travel\s+writing",
]


def has_english(text: str) -> bool:
    low = text.lower()
    if any(re.search(p, low) for p in EN_PATTERNS):
        return True
    if "english" in low:
        return True
    # コードブロック内に英文の長い連なりがあれば英語ありとみなす
    for blk in re.findall(r"```(.*?)```", text, re.S):
        latin = sum(1 for c in blk if ("a" <= c.lower() <= "z"))
        if latin > 200:  # 英単語が相当数＝英語本文
            return True
    return False


def is_local(text: str) -> bool:
    return any(kw in text for kw in LOCAL_KW)


def audit_one(p: pathlib.Path) -> dict:
    text = p.read_text(encoding="utf-8")
    return {
        "name": p.name,
        "local": is_local(text),
        "english": has_english(text),
        "factcheck": "事実検証" in text,
        "jalan_pr": ("px.a8.net" in text or "a8mat=" in text) and "アフィリエイト広告" in text,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="note記事 品質監査")
    ap.add_argument("--verbose", action="store_true", help="全記事の判定を表示")
    args = ap.parse_args()

    files = sorted(SRC.glob("*_note記事_*.md"))
    if not files:
        sys.exit(f"記事が見つかりません: {SRC}")

    rows = [audit_one(p) for p in files]
    total = len(rows)
    local = [r for r in rows if r["local"]]

    # 真のギャップ＝地元系なのに欠落しているもの
    gap_en = [r["name"] for r in local if not r["english"]]
    gap_fc = [r["name"] for r in local if not r["factcheck"]]
    gap_pr = [r["name"] for r in local if not r["jalan_pr"]]

    print(f"総記事数: {total}（うち地元/旅行系: {len(local)} / 国内向け: {total - len(local)}）")
    print(f"地元系の英語欠落:       {len(gap_en)}")
    print(f"地元系の事実検証欠落:   {len(gap_fc)}")
    print(f"地元系のじゃらんPR欠落: {len(gap_pr)}  （※食・観光記事のみ要・エッセイ系は任意）")

    def dump(title, names):
        if names:
            print(f"\n[{title}]")
            for n in names:
                print(f"  - {n}")

    dump("英語欠落（地元系・要対応）", gap_en)
    dump("事実検証欠落（地元系）", gap_fc)
    dump("じゃらんPR欠落（地元系・食観光は要対応）", gap_pr)

    if args.verbose:
        print("\n=== 全記事判定 ===")
        for r in rows:
            flags = "".join([
                "L" if r["local"] else "-",
                "E" if r["english"] else "-",
                "F" if r["factcheck"] else "-",
                "P" if r["jalan_pr"] else "-",
            ])
            print(f"  {flags}  {r['name']}")
        print("  凡例: L=地元系 E=英語 F=事実検証 P=じゃらんPR")


if __name__ == "__main__":
    main()
