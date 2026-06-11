#!/usr/bin/env python3
"""記事mdから本文ブロックを取り出してクリップボード(pbcopy)に流し込む簡易ユーティリティ。

使い方:
    python3 copy_body.py                      # CMO/outputs の最新note記事
    python3 copy_body.py 任意の_note記事.md   # 指定記事
"""
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTICLES_DIR = REPO_ROOT / "CMO" / "outputs"


def latest_article():
    candidates = sorted(
        ARTICLES_DIR.glob("*_note記事_*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        sys.exit(f"記事が見つかりません: {ARTICLES_DIR}")
    # 写真placeholder多いものを優先（v2版など）
    def n_ph(p):
        t = p.read_text(encoding="utf-8")
        m = re.search(r"##\s*本文.*?\n```\n(.+?)\n```", t, re.S)
        if not m:
            return 0
        return len(re.findall(r"\[(?:ここに)?写真", m.group(1)))
    candidates.sort(key=lambda p: (-n_ph(p), -p.stat().st_mtime))
    return candidates[0]


def main():
    md = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else latest_article()
    if not md.exists():
        sys.exit(f"ファイルがありません: {md}")
    text = md.read_text(encoding="utf-8")
    m = re.search(r"##\s*本文.*?\n```\n(.+?)\n```", text, re.S)
    if not m:
        sys.exit("本文ブロック(## 本文 直下の ``` ブロック)が見つかりません")
    body = m.group(1)
    subprocess.run(["pbcopy"], input=body.encode("utf-8"), check=True)
    print(f"✅ 本文をクリップボードにコピーしました")
    print(f"   記事: {md.name}")
    print(f"   文字数: {len(body)}")
    print(f"   次の操作: note を開いて ⌘+V で貼り付け、写真5枚をドラッグ、公開")


if __name__ == "__main__":
    main()
