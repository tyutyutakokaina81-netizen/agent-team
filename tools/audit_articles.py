#!/usr/bin/env python3
"""記事の海外導線・品質カバレッジを監査する依存ゼロCLI。

CMO/outputs/ の各 note 記事をスキャンし、以下を点検する：
- 英語セクション（travel writing / 英語要約）の有無
- じゃらん PR表記の有無（食記事で必須）
- 事実検証ノートの有無
- 日付ヘッダの有無
- 本文の概算文字数（短すぎ警告）

使い方:
  python3 tools/audit_articles.py            # サマリ
  python3 tools/audit_articles.py --gaps     # 不足のある記事だけ一覧
  python3 tools/audit_articles.py --overseas # 高岡/氷見/富山の食・観光記事に絞る
"""
from __future__ import annotations
import argparse, glob, os, re

OUTDIR = "CMO/outputs"
OVERSEAS = re.compile(r"高岡|氷見|富山|越中|砺波|五箇山|庄川|雨晴|新湊|二上山|倶利伽羅|井波|八尾|瑞龍寺|大仏|古城|おとぎの森|潮風|白えび|ホタルイカ|ぶり|フクラギ|ノドグロ|鱒寿司|ます寿司|昆布|かぶら|コロッケ|ブラック|うどん|素麺|そば|御清水|豆腐|地酒|地ビール|薄氷|かまぼこ|へしこ|黒造り|わかめ|山菜|大根|おでん|バイ貝|鮎|岩がき|氷見牛|漆器|和紙|彫刻|称名滝|万葉線|唐揚|市場|大門|青貝|沖漬")
FOOD = re.compile(r"白えび|ホタルイカ|ぶり|フクラギ|ノドグロ|鱒寿司|ます寿司|昆布|かぶら|コロッケ|ブラック|うどん|素麺|そば|御清水|豆腐|地酒|地ビール|薄氷|かまぼこ|へしこ|黒造り|わかめ|山菜|大根|おでん|バイ貝|鮎|岩がき|氷見牛|唐揚|沖漬|きっとき")

def audit(path: str) -> dict:
    name = os.path.basename(path)
    body = open(path, encoding="utf-8").read()
    return {
        "name": name,
        "overseas": bool(OVERSEAS.search(name)),
        "food": bool(FOOD.search(name)),
        "en": bool(re.search(r"from Kanazawa|## English|英語", body)),
        "pr": "アフィリエイト広告（じゃらん" in body,
        "factcheck": "事実検証ノート" in body,
        "date": bool(re.search(r"日付.*2026-", body)),
        "chars": len(re.sub(r"\s", "", body)),
    }

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gaps", action="store_true", help="不足のある記事だけ")
    ap.add_argument("--overseas", action="store_true", help="海外向け(食・観光)記事だけ")
    a = ap.parse_args()
    rows = [audit(p) for p in sorted(glob.glob(f"{OUTDIR}/2026-*note記事*.md"))]
    if a.overseas:
        rows = [r for r in rows if r["overseas"]]
    tot = len(rows)
    en = sum(r["en"] for r in rows)
    pr_need = [r for r in rows if r["food"]]
    pr_ok = sum(r["pr"] for r in pr_need)
    fc = sum(r["factcheck"] for r in rows)
    print(f"対象 {tot}本 | 英語 {en} | 事実検証ノート {fc} | 食記事 {len(pr_need)}中 PR表記 {pr_ok}")
    if a.gaps:
        print("--- 不足 ---")
        for r in rows:
            miss = []
            if r["overseas"] and not r["en"]:
                miss.append("英語")
            if r["food"] and not r["pr"]:
                miss.append("PR")
            if not r["factcheck"]:
                miss.append("検証ノート")
            if r["chars"] < 600:
                miss.append(f"短い({r['chars']}字)")
            if miss:
                print(f"  [{'+'.join(miss)}] {r['name']}")

if __name__ == "__main__":
    main()
