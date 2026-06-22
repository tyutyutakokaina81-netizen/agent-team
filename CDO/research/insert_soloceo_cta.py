#!/usr/bin/env python3
"""note記事末尾に Solo CEO OS の送客CTAを差し込む（テーマ別振り分け・冪等）。
- 対象: CMO/outputs/*note記事*.md（サムネ/生成プロンプト系は除外）
- 既に <!-- SOLOCEO_CTA --> を含むファイルはスキップ（二重挿入防止）
- URL差し替えはマーカー行ごと一括置換で可能
"""
import glob
import os

URL = "https://gumroad.com/l/olkujo"
MARKER = "<!-- SOLOCEO_CTA -->"

CTA = {
    "A": (
        "毎回ゼロからAIに指示するのをやめて、「役員チーム」として役割を固定する方法を"
        "一式にまとめました。6人のAI役員（CDO/CFO/CMO/CPO/CSO/CAO）のプロンプトと、"
        "記憶・自動実行の仕組みつき。\n→ Solo CEO OS：" + URL
    ),
    "C": (
        "企画も数字も営業も全部自分、という状態を「会社のように」分けるための運営OSを"
        "作りました。ひとりでも、役員チームがいる前提で回せます。\n"
        "→ Solo CEO OS：" + URL
    ),
    "D": (
        "この「仕組みで回す」考え方を、6役員ぶんのプロンプトと運営ルールにまとめたのが"
        " Solo CEO OS です。今日から各役員に仕事を振れます。\n→ " + URL
    ),
    "E": (
        "▶ ひとりで会社のように回す運営キット「Solo CEO OS」：" + URL
    ),
}

A_KW = ["AI", "ChatGPT", "Claude", "プロンプト", "役職", "役割"]
C_KW = ["ひとり", "個人", "会社", "フリーランス", "起業", "孤独", "月30万", "挑戦"]
D_KW = ["仕組み", "営業", "顧客", "有料", "発信", "マーケ", "SNS", "ログ", "時給",
        "サブスク", "予習", "ディープワーク", "メール", "ファイル名", "週次", "振り返り",
        "失敗", "テンプレ", "月10万", "月1万", "整え方", "辞める", "やらない",
        "最初に開く", "昼休み", "気力切れ", "本ベスト", "稼ぐ", "棚卸し"]

SKIP_KW = ["サムネ", "生成プロンプト"]


def classify(name: str) -> str:
    if any(k in name for k in A_KW):
        return "A"
    if any(k in name for k in C_KW):
        return "C"
    if any(k in name for k in D_KW):
        return "D"
    return "E"


def main():
    files = sorted(glob.glob("CMO/outputs/*note記事*.md"))
    counts = {"A": 0, "C": 0, "D": 0, "E": 0}
    skipped_marker = 0
    skipped_kind = 0
    touched = []
    for path in files:
        name = os.path.basename(path)
        if any(k in name for k in SKIP_KW):
            skipped_kind += 1
            continue
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        if MARKER in text:
            skipped_marker += 1
            continue
        cat = classify(name)
        block = "\n\n---\n\n" + MARKER + "\n" + CTA[cat] + "\n"
        if not text.endswith("\n"):
            text += "\n"
        text = text.rstrip("\n") + "\n" + block
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        counts[cat] += 1
        touched.append((name, cat))

    total = sum(counts.values())
    print(f"対象note記事: {len(files)}本")
    print(f"挿入: {total}本  内訳 A(AI)={counts['A']} C(ひとり)={counts['C']} "
          f"D(仕組み)={counts['D']} E(汎用)={counts['E']}")
    print(f"スキップ: マーカー既存={skipped_marker}  サムネ等除外={skipped_kind}")


if __name__ == "__main__":
    main()
