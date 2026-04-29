#!/usr/bin/env python3
"""
auto_youtube_setup.py — YouTube動画生成の初回セットアップ確認

実行: python3 auto_youtube_setup.py
"""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).parent
ASSET_DIR = REPO / "CMO" / "assets" / "announcer"
ASSET_DIR.mkdir(parents=True, exist_ok=True)


def check(label, ok):
    mark = "✅" if ok else "❌"
    print(f"  {mark} {label}")
    return ok


def main():
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  YouTube動画生成 セットアップ確認")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    all_ok = True

    # FFmpeg
    r = subprocess.run(["ffmpeg", "-version"], capture_output=True)
    ok = r.returncode == 0
    check("FFmpeg", ok)
    if not ok:
        print("    → brew install ffmpeg")
    all_ok = all_ok and ok

    # VOICEVOX
    try:
        import requests
        r = requests.get("http://localhost:50021/version", timeout=2)
        ok = r.status_code == 200
    except Exception:
        ok = False
    check("VOICEVOX（起動中）", ok)
    if not ok:
        print("    → https://voicevox.hiroshiba.jp/ からダウンロード・起動")
    # VOICEVOX はなくても動く（サイレント動画）

    # Python requests / Pillow
    try:
        import requests
        check("requests", True)
    except ImportError:
        check("requests", False)
        print("    → pip install requests")
        all_ok = False

    # アナウンサー画像
    images = {
        "メイン立ち絵": ASSET_DIR / "ai_takaoka_main.png",
        "笑顔（上半身）": ASSET_DIR / "ai_takaoka_smile.png",
    }
    print()
    for label, path in images.items():
        exists = path.exists()
        check(f"キャラ画像: {label}", exists)
        if not exists:
            print(f"    → CMO/assets/announcer/character_design.md のプロンプトで生成して配置")

    # 背景画像
    bg_files = [
        "takaoka_overview.jpg", "zuiryuji.jpg", "daibutsu.jpg",
        "kanayamachi.jpg", "takaoka_food.jpg", "shinkansen.jpg",
    ]
    missing_bg = [f for f in bg_files if not (ASSET_DIR / f).exists()]
    if missing_bg:
        check("背景画像（実写）", False)
        print(f"    → {len(missing_bg)}枚不足。プレースホルダーで代替生成します")
        print(f"    → 実写真は CMO/assets/announcer/ に配置")
    else:
        check("背景画像（実写）", True)

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    if all_ok:
        print("  準備OK → python3 auto_youtube_produce.py")
    else:
        print("  上記の❌を解消してから実行してください")
        print()
        print("  最低限の手順:")
        print("    brew install ffmpeg")
        print("    open https://voicevox.hiroshiba.jp/")
        print("    → VOICEVOXを起動してから:")
        print("    python3 auto_youtube_produce.py")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    main()
