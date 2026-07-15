#!/usr/bin/env python3
"""記事mdの タイトル→本文 を順にクリップボードへコピーする（macOS pbcopy）。
note編集画面へ手で貼るための最小ヘルパー。公開処理は一切しない（読み取り専用）。

使い方:
  python3 CDO/outputs/note_publisher/copy_article.py <記事md パス>
  1) タイトルがコピーされる → noteのタイトル欄に貼る → ターミナルでEnter
  2) 本文がコピーされる     → noteの本文欄に貼る
"""
import re, sys, subprocess, pathlib

def pbcopy(text: str):
    subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)

def main():
    if len(sys.argv) < 2:
        sys.exit("使い方: python3 copy_article.py <記事md パス>")
    p = pathlib.Path(sys.argv[1])
    s = p.read_text(encoding="utf-8")
    fence = chr(96) * 3
    title_m = re.search(r"##\s*タイトル.*?\n" + fence + r"\n(.+?)\n" + fence, s, re.S)
    body_m = re.search(r"##\s*本文.*?\n" + fence + r"\n(.+?)\n" + fence, s, re.S)
    if not title_m or not body_m:
        sys.exit("タイトル/本文ブロックが抽出できませんでした。mdの書式を確認してください。")
    title, body = title_m.group(1).strip(), body_m.group(1)
    tags_m = re.search(r"##\s*ハッシュタグ.*?\n" + fence + r"\n(.+?)\n" + fence, s, re.S)

    pbcopy(title)
    print(f"① タイトルをコピーしました（{title}）")
    print("   → note のタイトル欄に貼り付けたら、ここで Enter")
    input()
    pbcopy(body)
    print(f"② 本文をコピーしました（{len(body)}字）")
    print("   → note の本文欄に貼り付けてください")
    if tags_m:
        print("   → 貼り終えたら Enter（ハッシュタグをコピーします）")
        input()
        pbcopy(tags_m.group(1).strip())
        print("③ ハッシュタグをコピーしました → 公開設定画面のタグ欄に貼ってください")
    print("完了。有料記事の場合は 有料ライン(¥300) の設定と ◆◆マーカー行の削除を忘れずに。")

if __name__ == "__main__":
    main()
