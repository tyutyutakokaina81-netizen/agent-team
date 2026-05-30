#!/usr/bin/env python3
"""
写真選択ヘルパー: ファイル選択ダイアログを5回出して、選んだ写真を
自動で ~/Pictures/note/YYYY-MM-DD/ に photo_01..05 命名で保存する。
そのまま続けて publish_to_note.py も走らせられる。

使い方:
    python3 prepare_photos.py                       # 写真選択だけ
    python3 prepare_photos.py --then-publish        # 写真選択→続けて自動公開
    python3 prepare_photos.py --date 2026-05-28     # 日付指定
"""
import argparse
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import filedialog
except ImportError:
    sys.exit("tkinterが必要（標準ライブラリのはず）。pythonインストールを確認してください。")

LABELS = [
    "① 広場の集合（ドラえもん中央／のび太・しずか・ジャイアン）= サムネ",
    "② スネオ単独",
    "③ 別アングルの広場",
    "④ ジャイアン（ベンチ・拳上げ）",
    "⑤ しずか + ドラミ",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=date.today().isoformat(),
                    help="日付フォルダ名 (YYYY-MM-DD)。省略時は今日")
    ap.add_argument("--count", type=int, default=5, help="選ぶ枚数")
    ap.add_argument("--then-publish", action="store_true",
                    help="選び終わったらそのまま publish_to_note.py を実行")
    args = ap.parse_args()

    out_dir = Path.home() / "Pictures" / "note" / args.date
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 保存先: {out_dir}")

    root = tk.Tk()
    root.withdraw()

    saved = []
    for i in range(1, args.count + 1):
        label = LABELS[i - 1] if i <= len(LABELS) else f"写真{i}"
        print(f"\n→ {label}")
        path = filedialog.askopenfilename(
            title=f"写真{i:02d} を選択 — {label}",
            filetypes=[("画像", "*.jpg *.jpeg *.png *.heic *.HEIC *.JPG *.JPEG *.PNG")],
        )
        if not path:
            print(f"⚠️ 写真{i} がキャンセルされました。中断します。")
            return 1
        src = Path(path)
        dst = out_dir / f"photo_{i:02d}{src.suffix.lower()}"
        shutil.copy2(src, dst)
        saved.append(dst)
        print(f"  ✅ {dst.name}  ← {src.name}")

    print(f"\n✅ {len(saved)}枚すべて保存完了。")

    if args.then_publish:
        print("\n🚀 続けて publish_to_note.py を実行します...")
        publisher = Path(__file__).parent / "publish_to_note.py"
        result = subprocess.run(
            [sys.executable, str(publisher), "--photos", str(out_dir)],
        )
        return result.returncode

    print("\n次のコマンドで公開：")
    print(f"   python3 publish_to_note.py --photos {out_dir}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
