#!/usr/bin/env python3
"""
apply_cta.py — 工程SELL: 全note記事末尾に商品CTAを一括挿入（集客→商品の動線）

設計思想:
- LLMを呼ばない決定論的処理（API課金ゼロ）
- 商品URLが確定した瞬間、127記事へワンコマンドでCTAを差し込む（CMO作業の無人化）
- 冪等：CTAマーカーが既にある記事はスキップ（再実行で二重挿入しない）
- 非破壊：本文は変更せず末尾に追記するだけ

使い方:
  python3 ops/auto_company/apply_cta.py --url https://gumroad.com/... --dry-run
  python3 ops/auto_company/apply_cta.py --url https://gumroad.com/...
"""
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTPUTS = os.path.join(REPO, "CMO", "outputs")
MARKER = "<!-- CTA:gumroad -->"

CTA_TEMPLATE = """

{marker}
─────────────
🛠 ひとり会社の実務を自動化する道具を作っています：
　AIプロンプト集（実務15本・¥980）→ {url}
　請求書・返信・SNS・営業メールを、毎回ゼロから書かなくて済みます。
─────────────
"""


def get_arg(name, default=None):
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def main():
    url = get_arg("--url")
    dry = "--dry-run" in sys.argv
    if not url:
        print("使い方: apply_cta.py --url <商品URL> [--dry-run]")
        print("（出品後のGumroad URLを指定。先に出品が必要）")
        return 1

    files = sorted(f for f in os.listdir(OUTPUTS) if f.endswith(".md"))
    to_apply, already = [], 0
    for f in files:
        path = os.path.join(OUTPUTS, f)
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
        if MARKER in content:
            already += 1
            continue
        to_apply.append(f)

    print(f"記事 {len(files)}本 / CTA既設 {already}本 / 新規挿入 {len(to_apply)}本")
    if dry:
        print("--- 挿入対象（dry-run・先頭5件）---")
        for f in to_apply[:5]:
            print(f"  {f}")
        print(f"... 計{len(to_apply)}件。URL={url}")
        return 0

    cta = CTA_TEMPLATE.format(marker=MARKER, url=url)
    for f in to_apply:
        path = os.path.join(OUTPUTS, f)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(cta)
    print(f"✅ {len(to_apply)}本にCTAを挿入（URL={url}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
