#!/usr/bin/env python3
"""
全generator (Reddit / X / EN article) を1記事に対して一括実行する。

使い方:
    python3 gen_all.py                                # 最新記事
    python3 gen_all.py --article CMO/outputs/xxx.md   # 指定
    python3 gen_all.py --since 2026-05-31             # 当該日以降の全記事に一括適用
"""
import argparse
import subprocess
import sys
from pathlib import Path

from _common import find_article, ARTICLES_DIR

HERE = Path(__file__).resolve().parent
GENS = [
    HERE / "gen_reddit_post.py",
    HERE / "gen_x_tweets.py",
    HERE / "gen_en_article.py",
]


def run_for(md_path: Path):
    print(f"\n=== {md_path.name} ===")
    for g in GENS:
        r = subprocess.run([sys.executable, str(g), "--article", str(md_path)],
                           capture_output=True, text=True)
        out = (r.stdout + r.stderr).strip()
        print(f"  [{g.name}] {out.splitlines()[0] if out else 'no output'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--article", default=None)
    ap.add_argument("--since", default=None, help="YYYY-MM-DD 以降の全記事に適用")
    args = ap.parse_args()

    if args.since:
        targets = sorted([p for p in ARTICLES_DIR.glob("*_note記事_*.md")
                          if p.name[:10] >= args.since])
        if not targets:
            sys.exit(f"対象記事なし (since={args.since})")
        print(f"📦 {len(targets)} 件に一括適用")
        for p in targets:
            run_for(p)
    else:
        run_for(find_article(args.article))
    print("\n✅ 完了")


if __name__ == "__main__":
    main()
