#!/usr/bin/env python3
"""
note 一括公開ヘルパー

指定した日付の記事をまとめて公開する。
publish_to_note.py を日付でフィルタして順番に実行する。

使い方:
  # 2026-06-23 の記事を全部 text-only で公開
  python3 batch_publish.py --date 2026-06-23

  # 最新5日分の記事を一覧表示だけ（実行しない）
  python3 batch_publish.py --date 2026-06-23 --dry-run
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTICLES_DIR = REPO_ROOT / "CMO" / "outputs"
PUBLISHER = Path(__file__).resolve().parent / "publish_to_note.py"


def find_articles_by_date(date_str: str) -> list[Path]:
    """指定日付のnote記事を返す（ファイル名昇順）"""
    pattern = f"{date_str}_note記事_*.md"
    articles = sorted(ARTICLES_DIR.glob(pattern))
    return articles


def main():
    ap = argparse.ArgumentParser(description="note 一括公開ヘルパー")
    ap.add_argument("--date", required=True, metavar="YYYY-MM-DD", help="公開する記事の日付")
    ap.add_argument("--dry-run", action="store_true", help="記事一覧を表示するだけ（公開しない）")
    ap.add_argument("--draft", action="store_true", help="下書き保存のみ（公開ボタンを押さない）")
    args = ap.parse_args()

    articles = find_articles_by_date(args.date)
    if not articles:
        sys.exit(f"❌ {args.date} の記事が見つかりません: {ARTICLES_DIR}/{args.date}_note記事_*.md")

    print(f"📅 {args.date} の記事: {len(articles)}本")
    for i, a in enumerate(articles, 1):
        print(f"  {i}. {a.name}")

    if args.dry_run:
        print("\n（--dry-run のため公開しません）")
        return

    print(f"\n{'='*50}")
    print(f"順番に公開します。各記事で自動クリックが失敗した場合は")
    print(f"ブラウザで「公開」を手動クリック → ターミナルで Enter を押してください。")
    print(f"{'='*50}\n")

    success = 0
    for i, article in enumerate(articles, 1):
        print(f"\n[{i}/{len(articles)}] {article.name}")
        print("-" * 40)
        cmd = [
            sys.executable,
            str(PUBLISHER),
            "--text-only",
            "--article", str(article),
        ]
        if args.draft:
            cmd.append("--draft")
        result = subprocess.run(cmd)
        if result.returncode == 0:
            success += 1
        else:
            print(f"⚠️  記事 {i} の処理でエラーが発生しました（続行します）")

    print(f"\n{'='*50}")
    print(f"✅ 完了: {success}/{len(articles)} 本")


if __name__ == "__main__":
    main()
