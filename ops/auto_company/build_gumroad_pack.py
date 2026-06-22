#!/usr/bin/env python3
"""
build_gumroad_pack.py — 工程④PUBLISH補助: 商品の配布用クリーン版を生成

設計思想:
- LLMを呼ばない決定論的処理（API課金ゼロ）
- CPOの商品Markdownから「### 制作ノート（オーナー向け・公開時は削除）」以降を自動除去
- 削除し忘れ（内部メモ・実情報の流出）を機械的に防ぐ＝監視体制の一部

入力:  商品 .md（既定: CPO/outputs/2026-06-22_AIプロンプト集_ひとり会社の実務_先行版.md）
出力:  ops/outbox/gumroad/<同名>.md（制作ノート除去済みの配布用）
使い方: python3 ops/auto_company/build_gumroad_pack.py [商品.md]
"""
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT = os.path.join(REPO, "CPO", "outputs",
                       "2026-06-22_AIプロンプト集_ひとり会社の実務_先行版.md")
OUTDIR = os.path.join(REPO, "ops", "outbox", "gumroad")

# 公開してはいけない内部ブロックの目印
CUT_MARKERS = (r"###?\s*制作ノート", r"###?\s*内部メモ", r"<!--\s*internal")


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    if not os.path.isfile(src):
        print(f"商品ファイルが見つからない: {src}")
        return 1

    with open(src, encoding="utf-8") as fh:
        lines = fh.readlines()

    cut = len(lines)
    for i, line in enumerate(lines):
        if any(re.search(m, line) for m in CUT_MARKERS):
            cut = i
            break
    clean = "".join(lines[:cut]).rstrip() + "\n"

    # 配布版に残ってはいけないものの警告（除去はしない＝人が確認）
    leaks = []
    if "公開時は削除" in clean:
        leaks.append("「公開時は削除」の文字列が残存")
    if re.search(r"(振込先|口座番号|@gmail|@yahoo)", clean):
        leaks.append("連絡先/口座らしき文字列が残存")

    os.makedirs(OUTDIR, exist_ok=True)
    dst = os.path.join(OUTDIR, os.path.basename(src))
    with open(dst, "w", encoding="utf-8") as fh:
        fh.write(clean)

    print(f"✅ 配布用クリーン版を生成: {os.path.relpath(dst, REPO)}")
    print(f"   制作ノート以降 {len(lines) - cut} 行を除去")
    if leaks:
        print("⚠️  公開前に目視確認してください:")
        for x in leaks:
            print(f"   - {x}")
    print("   ※【 】プレースホルダはサンプルとして残してOK（使い方の説明）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
