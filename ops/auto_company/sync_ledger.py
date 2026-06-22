#!/usr/bin/env python3
"""
sync_ledger.py — 台帳乖離の自動修復（根因R5・学習ループを閉じる）

設計思想:
- LLMを呼ばない決定論的処理（API課金ゼロ）
- CMO/outputs にあるのに CMO/_index.md に未記載の記事を検出し、**追記のみ**で同期
- 破壊的操作はしない（既存行の削除・上書きなし。末尾に同期セクションを追加するだけ）
- 6/12インシデントの「台帳乖離」を機械的に解消し、再発を防ぐ

使い方:
  python3 ops/auto_company/sync_ledger.py --dry-run   # 検出のみ
  python3 ops/auto_company/sync_ledger.py             # 追記実行
"""
import os
import re
import sys
import datetime

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTPUTS = os.path.join(REPO, "CMO", "outputs")
INDEX = os.path.join(REPO, "CMO", "_index.md")


def title_of(fname):
    t = re.sub(r"^\d{4}-\d{2}-\d{2}_note記事_", "", fname)
    return re.sub(r"\.md$", "", t)


def date_of(fname):
    m = re.match(r"(\d{4}-\d{2}-\d{2})", fname)
    return m.group(1) if m else ""


def main():
    dry = "--dry-run" in sys.argv
    if not os.path.isdir(OUTPUTS) or not os.path.isfile(INDEX):
        print("CMO/outputs か CMO/_index.md が見つからない")
        return 1

    with open(INDEX, encoding="utf-8") as fh:
        ledger = fh.read()

    files = sorted(f for f in os.listdir(OUTPUTS) if f.endswith(".md"))
    # guard_checks と同じ厳密判定：フルファイル名（拡張子除く）が台帳に無ければ未記載
    missing = [f for f in files
               if f not in ledger and re.sub(r"\.md$", "", f) not in ledger]

    print(f"記事 {len(files)}本 / 台帳未記載 {len(missing)}件")
    if not missing:
        print("✅ 台帳は同期済み。乖離なし。")
        return 0

    rows = []
    for f in missing:
        rows.append(f"| {date_of(f)} | {f} | note記事 | {title_of(f)} | 完了（自動同期） |")

    block = (
        f"\n\n## 自動同期で追加（sync_ledger.py / {datetime.date.today()}）\n\n"
        "> 台帳乖離の自動修復。outputsに存在するが未記載だった記事を機械追記（追記のみ・非破壊）。\n\n"
        "| 日付 | ファイル名 | 種別 | 概要 | ステータス |\n"
        "|------|-----------|------|------|-----------|\n"
        + "\n".join(rows) + "\n"
    )

    if dry:
        print("--- 追記予定（dry-run・先頭10件）---")
        for r in rows[:10]:
            print(r)
        print(f"... 計{len(rows)}件")
        return 0

    with open(INDEX, "a", encoding="utf-8") as fh:
        fh.write(block)
    print(f"✅ {len(missing)}件を CMO/_index.md に追記（台帳乖離を解消）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
