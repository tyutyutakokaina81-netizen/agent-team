#!/usr/bin/env python3
"""ops/x_queue.txt の整形フィクサー（依存ゼロ）。

問題: 番号付きスレッドで「N/ …」の続き行（箇条書き等）が別行にあると、投稿時に別ツイート化する
（x_poster/note_to_x は 1行=1ツイート）。
修正: 各スレッド内で、`\\d+/` で始まらない継続行を直前の番号ツイート行へ結合（半角スペース連結）。
      単発スレッド（番号なし1行）はそのまま。ヘッダのコメントと [POSTED] は保持。280字超は警告。

使い方:
  python3 ops/fix_x_queue.py           # プレビュー（変更しない）
  python3 ops/fix_x_queue.py --write    # x_queue.txt を修正
"""
import os, re, argparse

QUEUE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ops", "x_queue.txt")
NUM = re.compile(r"^\d+/")
MAXLEN = 280

def fix(text):
    lines = text.split("\n")
    out, i = [], 0
    # 先頭のコメント/空行（最初の === より前）はそのまま
    while i < len(lines) and not lines[i].startswith("==="):
        out.append(lines[i]); i += 1
    changed = 0
    warnings = []
    while i < len(lines):
        line = lines[i]
        if line.startswith("==="):
            out.append(line); i += 1
            # このスレッドの本文行を収集（次の === まで）
            body = []
            while i < len(lines) and not lines[i].startswith("==="):
                body.append(lines[i]); i += 1
            # 空行を保持しつつ、非空行をツイートへ
            tweets = []
            numbered = any(NUM.match(b.strip()) for b in body if b.strip())
            for b in body:
                if not b.strip():
                    continue
                if numbered:
                    bs = b.strip()
                    if NUM.match(bs) or not tweets:
                        tweets.append(bs)
                    elif len(tweets[-1] + " " + bs) <= MAXLEN:
                        # 継続行 → 280字を超えない範囲でのみ直前ツイートへ結合
                        tweets[-1] = tweets[-1] + " " + bs
                        changed += 1
                    else:
                        # 結合すると280字超 → 独立した(次の)ツイートとして残す
                        tweets.append(bs)
                else:
                    tweets.append(b.strip())
            slug = out[-1]
            for t in tweets:
                if len(t) > MAXLEN:
                    warnings.append(f"{slug} : {len(t)}字 > {MAXLEN} → 手動分割が必要")
            # スレッド見出しの後に空行、ツイート、末尾空行
            for t in tweets:
                out.append(t)
            out.append("")
        else:
            out.append(line); i += 1
    return "\n".join(out).rstrip() + "\n", changed, warnings

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    text = open(QUEUE, encoding="utf-8").read()
    fixed, changed, warnings = fix(text)
    print(f"結合した継続行: {changed} 行")
    for w in warnings:
        print("  ⚠️", w)
    if text == fixed:
        print("変更なし（既に整形済み）。")
        return
    if not args.write:
        print("[プレビュー] 変更あり。適用するには --write。")
        # 差分の要点だけ表示
        return
    open(QUEUE, "w", encoding="utf-8").write(fixed)
    print(f"[書込] {QUEUE} を整形。")

if __name__ == "__main__":
    main()
