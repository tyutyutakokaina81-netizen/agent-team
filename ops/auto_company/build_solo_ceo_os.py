#!/usr/bin/env python3
"""
build_solo_ceo_os.py — 商品「Solo CEO OS」の単一配布ファイルを自動生成

2本のプロンプト集を、操作ガイド（operating model / playbook）付きの1ファイルに結合。
アップロードを1回で済ませるため。LLM不使用・課金ゼロ。

出力: ops/outbox/gumroad/Solo_CEO_OS_完全版.md
"""
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(REPO, "ops", "outbox", "gumroad")
PACK1 = os.path.join(SRC, "2026-06-22_AIプロンプト集_ひとり会社の実務_先行版.md")
PACK2 = os.path.join(SRC, "2026-06-22_AIプロンプト集_飲食店と小さな食ビジネス_先行版.md")
OUT = os.path.join(SRC, "Solo_CEO_OS_完全版.md")

HEADER = """# Solo CEO OS — Run your business like a company, with AI executives

ひとりビジネスを「会社」みたいに回すためのOS＋実務プロンプト27本。
ChatGPT / Claude / Gemini どれでも使えます。【 】の中だけ自分の情報に置き換えてください。

---

## Start Here — 6人のAI役員に仕事を任せる

全部ひとりでやるのをやめて、AIに「役員」を割り当てます。

| 役員 | 担当 | このOSでの道具 |
|---|---|---|
| CMO マーケ | 集客・発信 | SNS/記事ネタ/英語要約プロンプト |
| CPO 商品 | 商品・教材づくり | 商品説明/LP/メニュー文プロンプト |
| CFO 財務 | お金・採算 | 請求書/価格決め/原価相談プロンプト |
| CSO 営業 | 売る・顧客対応 | 営業メール/返信/クレーム対応プロンプト |
| CAO 分析 | 振り返り・改善 | 作業ログ分析/週次振り返りプロンプト |
| CDO 技術 | 効率化・自動化 | 要約/整理/文章の自分の言葉化プロンプト |

## The Revenue Loop — お金が生まれる流れ

```
作る（記事・商品） → 出す（SNS・販売ページ） → 売る → 測る（採算） → 改善
```

無料の発信で人を集め、実用の商品（このプロンプト集のような道具）で換金する。
高い固定費も借入もいりません。**売れた分だけ手数料を払う**ところから始められます。

## How to use — 精度を上げる3つのコツ

1. 各プロンプトの「あなたは〜」を消さない（出力が安定します）
2. 「こういうのは避けて」を1行足すと、欲しくない方向を防げます
3. 一度で完璧を狙わず「もっと短く」「もっと柔らかく」と返して調整

---

# Part 1 — ひとり会社の実務 15本

"""

BRIDGE = "\n\n---\n\n# Part 2 — 飲食店と小さな食ビジネス 12本\n\n"


def strip_title(text):
    # 各パックの先頭H1とリード文を落として本文(##以降)から使う
    idx = text.find("\n## ")
    return text[idx:].lstrip() if idx != -1 else text


def main():
    with open(PACK1, encoding="utf-8") as f:
        p1 = f.read()
    with open(PACK2, encoding="utf-8") as f:
        p2 = f.read()
    body = HEADER + strip_title(p1) + BRIDGE + strip_title(p2)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(body.rstrip() + "\n")
    print(f"✅ 生成: {os.path.relpath(OUT, REPO)}（{len(body.splitlines())}行）")
    print("これ1本をGumroadにアップすればOK（27プロンプト＋操作ガイド入り）")


if __name__ == "__main__":
    main()
