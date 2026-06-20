#!/usr/bin/env python3
"""
重複noteの編集ページを「5本ずつ」ブラウザで開く補助（オーナーのMacで実行）。

unpublish_notes.py の自動クリックが note のUIで空振りしたため、
「ページを開く」だけ自動化し、各ページで手動で『…』→『公開を停止/下書きに戻す』を押す方式。
URLを74回コピペする手間をなくす。ログイン済みのデフォルトブラウザで開く。

dedup_unpublish_list.tsv の action=unpublish 行（74本）を対象にする。

使い方:
  python3 open_dup_edits.py                 # 5本ずつ開く（既定）。Enterで次の5本
  python3 open_dup_edits.py --batch 3       # 3本ずつ
  python3 open_dup_edits.py --start 40      # 40番目から再開（途中で中断した時）
"""
from __future__ import annotations
import argparse
import sys
import time
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEDUP_TSV = HERE / "dedup_unpublish_list.tsv"


def load_targets(p: Path):
    if not p.exists():
        sys.exit(f"✗ {p} が見つかりません。先に note_cleanup_all.py を実行してください。")
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("action") or line.startswith("#"):
            continue
        c = line.split("\t")
        if len(c) >= 2 and c[0].strip() == "unpublish":
            out.append((c[1].strip(), c[2].strip() if len(c) >= 3 else ""))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", default=str(DEDUP_TSV))
    ap.add_argument("--batch", type=int, default=5)
    ap.add_argument("--start", type=int, default=1, help="何本目から開くか（1始まり）")
    args = ap.parse_args()

    targets = load_targets(Path(args.list))
    total = len(targets)
    print(f"対象 {total} 本。{args.batch}本ずつ開きます。")
    print("各ページで『…』メニュー →『公開を停止』または『下書きに戻す』を押してください。\n")

    i = args.start - 1
    while i < total:
        batch = targets[i:i + args.batch]
        for j, (nid, title) in enumerate(batch, start=i + 1):
            url = f"https://note.com/notes/{nid}/edit"
            print(f"  [{j}/{total}] 開く: {title[:40]}  {url}")
            webbrowser.open(url)
            time.sleep(1.0)
        i += len(batch)
        if i < total:
            ans = input(f"\n→ この{len(batch)}本を公開停止したら Enter で次へ（qで中断 / 再開は --start {i + 1}）: ")
            if ans.strip().lower() == "q":
                print(f"中断しました。再開は: python3 {Path(__file__).name} --start {i + 1}")
                return
            print()
    print("\n✅ 全部開き終えました。各ページで公開停止できているか確認してください。")
    print("   確認後：note一覧を再取得して残重複ゼロをチェック →")
    print("   python3 note_cleanup_all.py")


if __name__ == "__main__":
    main()
