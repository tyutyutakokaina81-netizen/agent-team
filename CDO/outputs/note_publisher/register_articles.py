#!/usr/bin/env python3
"""
register_articles.py — 新しいnote記事を CMO/_index.md に自動登録する。

CMO/outputs/ の *_note記事_*.md を走査し、まだ台帳(CMO/_index.md)に
記載の無いファイルを「## 自動登録ログ（新規記事）」セクションへ追記する。
冪等（既登録は二重に追加しない）。日次自動公開パイプラインから呼ぶ想定。

使い方:
  python3 register_articles.py            # 未登録を全部登録
  python3 register_articles.py --dry-run  # 追加されるものを表示するだけ
"""
from __future__ import annotations
import argparse
import re
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parents[2]
ARTICLES_DIR = REPO / "CMO" / "outputs"
INDEX = REPO / "CMO" / "_index.md"
AUTO_HEADER = "## 自動登録ログ（新規記事）"
TABLE_HEADER = (
    "| 日付 | ファイル名 | 種別 | 概要 | ステータス |\n"
    "|------|-----------|------|------|-----------|\n"
)


def extract_summary(text: str) -> str:
    """記事mdから概要を作る。テーマ/メモ行 → タイトル の順で拾う。"""
    for pat in (r"\*\*テーマ\*\*[:：]\s*(.+)", r"-\s*\*\*メモ\*\*[:：]\s*(.+)"):
        m = re.search(pat, text)
        if m:
            return m.group(1).strip()[:60]
    m = re.search(r"##\s*タイトル.*?\n```\n(.+?)\n```", text, re.S)
    if m:
        return m.group(1).strip().splitlines()[0].strip()[:60]
    return "（概要未抽出）"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not INDEX.exists():
        print(f"✗ 台帳が見つかりません: {INDEX}")
        return 1

    index_text = INDEX.read_text(encoding="utf-8")
    articles = sorted(ARTICLES_DIR.glob("*_note記事_*.md"))

    # 既に台帳本文中にファイル名が出現するものは登録済みとみなす
    new = []
    for p in articles:
        if p.name in index_text:
            continue
        m = re.match(r"(\d{4}-\d{2}-\d{2})_", p.name)
        date = m.group(1) if m else ""
        summary = extract_summary(p.read_text(encoding="utf-8"))
        new.append((date, p.name, summary))

    if not new:
        print("✅ 新規登録なし（台帳は最新）")
        return 0

    print(f"📝 新規 {len(new)} 件を登録:")
    for d, name, _ in new:
        print(f"  + {name}")

    if args.dry_run:
        print("（--dry-run のため台帳は変更しません）")
        return 0

    rows = "".join(
        f"| {d} | {name} | note記事 | {summary} | 自動登録 |\n"
        for d, name, summary in new
    )

    if AUTO_HEADER in index_text:
        # 既存の自動登録テーブル末尾に追記
        new_text = index_text.rstrip() + "\n" + rows
    else:
        stamp = datetime.now().strftime("%Y-%m-%d")
        block = (
            f"\n\n---\n\n{AUTO_HEADER}\n\n"
            f"> register_articles.py が自動追記（最終: {stamp}）。"
            f"手動ログと重複しても害は無い。\n\n"
            f"{TABLE_HEADER}{rows}"
        )
        new_text = index_text.rstrip() + block

    INDEX.write_text(new_text, encoding="utf-8")
    print(f"✅ {len(new)} 件を {INDEX} に登録しました")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
