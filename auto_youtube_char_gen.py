#!/usr/bin/env python3
"""
auto_youtube_char_gen.py — 高岡アイ キャラクター画像を自動生成（Pillow使用・無料）

外部APIなしでアナウンサー立ち絵を生成する。
"""

import math
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    import subprocess, sys
    subprocess.run([sys.executable, "-m", "pip", "install", "Pillow", "-q"])
    from PIL import Image, ImageDraw, ImageFont

ASSET_DIR = Path(__file__).parent / "CMO" / "assets" / "announcer"
ASSET_DIR.mkdir(parents=True, exist_ok=True)


def draw_announcer(size=(400, 600), name="高岡アイ") -> Image.Image:
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    w, h = size

    # ── 体（ネイビーブレザー） ──────────────────
    body_color = (25, 50, 100)
    # 肩〜裾
    draw.ellipse([w*0.15, h*0.52, w*0.85, h*0.95], fill=body_color)
    draw.rectangle([w*0.2, h*0.58, w*0.8, h*1.0], fill=body_color)
    # 白シャツ
    draw.polygon([
        (w*0.38, h*0.58), (w*0.5, h*0.7),
        (w*0.62, h*0.58), (w*0.55, h*0.55),
        (w*0.45, h*0.55)
    ], fill=(230, 230, 240))
    # ラペル
    draw.polygon([
        (w*0.38, h*0.58), (w*0.5, h*0.7), (w*0.38, h*0.65)
    ], fill=(20, 40, 90))
    draw.polygon([
        (w*0.62, h*0.58), (w*0.5, h*0.7), (w*0.62, h*0.65)
    ], fill=(20, 40, 90))

    # ── 首 ──────────────────────────────────
    skin = (255, 220, 190)
    draw.ellipse([w*0.43, h*0.43, w*0.57, h*0.62], fill=skin)

    # ── 顔 ──────────────────────────────────
    # 輪郭
    draw.ellipse([w*0.25, h*0.17, w*0.75, h*0.53], fill=skin)
    # あご先を少し細く
    draw.ellipse([w*0.3, h*0.38, w*0.7, h*0.58], fill=skin)

    # ── 髪（黒・ロング） ─────────────────────
    hair = (30, 20, 20)
    # 頭頂部〜後頭部
    draw.ellipse([w*0.22, h*0.12, w*0.78, h*0.42], fill=hair)
    # 前髪
    draw.ellipse([w*0.27, h*0.14, w*0.73, h*0.30], fill=hair)
    # サイド・後ろ髪
    draw.ellipse([w*0.15, h*0.25, w*0.38, h*0.65], fill=hair)
    draw.ellipse([w*0.62, h*0.25, w*0.85, h*0.65], fill=hair)
    # 前髪すき間（額）
    draw.ellipse([w*0.32, h*0.155, w*0.68, h*0.285], fill=skin)

    # ── 目 ──────────────────────────────────
    eye_y = h * 0.335
    # 左目
    draw.ellipse([w*0.33, eye_y-14, w*0.46, eye_y+8], fill=(255, 255, 255))
    draw.ellipse([w*0.355, eye_y-10, w*0.44, eye_y+5], fill=(80, 50, 30))
    draw.ellipse([w*0.37, eye_y-8, w*0.425, eye_y+3], fill=(20, 10, 5))
    draw.ellipse([w*0.38, eye_y-7, w*0.40, eye_y-4], fill=(255, 255, 255))  # ハイライト
    # まつ毛
    for dx in range(3):
        x = w * (0.34 + dx * 0.03)
        draw.line([(x, eye_y - 14), (x - 3, eye_y - 20)], fill=hair, width=2)
    # 右目
    draw.ellipse([w*0.54, eye_y-14, w*0.67, eye_y+8], fill=(255, 255, 255))
    draw.ellipse([w*0.56, eye_y-10, w*0.645, eye_y+5], fill=(80, 50, 30))
    draw.ellipse([w*0.575, eye_y-8, w*0.63, eye_y+3], fill=(20, 10, 5))
    draw.ellipse([w*0.585, eye_y-7, w*0.605, eye_y-4], fill=(255, 255, 255))
    for dx in range(3):
        x = w * (0.55 + dx * 0.03)
        draw.line([(x, eye_y - 14), (x - 3, eye_y - 20)], fill=hair, width=2)

    # ── 眉 ──────────────────────────────────
    brow_y = h * 0.295
    draw.arc([w*0.32, brow_y-6, w*0.46, brow_y+6], 200, 340, fill=hair, width=3)
    draw.arc([w*0.54, brow_y-6, w*0.68, brow_y+6], 200, 340, fill=hair, width=3)

    # ── 鼻 ──────────────────────────────────
    draw.ellipse([w*0.47, h*0.385, w*0.53, h*0.415], fill=(240, 195, 165))

    # ── 口（笑顔） ───────────────────────────
    mouth_y = h * 0.445
    draw.arc([w*0.39, mouth_y-10, w*0.61, mouth_y+12], 10, 170, fill=(200, 100, 110), width=3)
    # 上唇
    draw.arc([w*0.41, mouth_y-12, w*0.59, mouth_y+4], 190, 350, fill=(220, 130, 130), width=2)

    # ── 耳 ──────────────────────────────────
    draw.ellipse([w*0.23, h*0.31, w*0.3, h*0.41], fill=skin)
    draw.ellipse([w*0.7, h*0.31, w*0.77, h*0.41], fill=skin)

    # ── マイク ──────────────────────────────
    mic_x, mic_y = int(w * 0.72), int(h * 0.62)
    draw.ellipse([mic_x-12, mic_y-18, mic_x+12, mic_y+18], fill=(80, 80, 80))
    draw.rectangle([mic_x-5, mic_y+10, mic_x+5, mic_y+60], fill=(60, 60, 60))
    draw.ellipse([mic_x-4, mic_y-14, mic_x+4, mic_y+14], fill=(120, 120, 120))

    # ── 銅器ブローチ ─────────────────────────
    bx, by = int(w * 0.42), int(h * 0.595)
    draw.ellipse([bx-8, by-8, bx+8, by+8], fill=(180, 130, 60))
    draw.ellipse([bx-5, by-5, bx+5, by+5], fill=(210, 160, 80))

    # ── 名前テロップ（下部） ──────────────────
    bar_h = 52
    bar = Image.new("RGBA", (w, bar_h), (10, 30, 80, 220))
    img.paste(bar, (0, h - bar_h), bar)
    draw2 = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc", 22)
        font_small = ImageFont.truetype("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", 14)
    except Exception:
        font = ImageFont.load_default()
        font_small = font
    draw2.text((w//2, h - bar_h + 12), name, font=font,
               fill=(255, 255, 255), anchor="mt")
    draw2.text((w//2, h - bar_h + 34), "富山・高岡観光ナビゲーター", font=font_small,
               fill=(180, 210, 255), anchor="mt")

    return img


def generate_all():
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  高岡アイ キャラクター画像生成")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    variants = {
        "ai_takaoka_main.png":    (400, 600),
        "ai_takaoka_smile.png":   (400, 600),
    }
    for fname, size in variants.items():
        path = ASSET_DIR / fname
        img = draw_announcer(size)
        img.save(path, "PNG")
        print(f"  ✅ {fname} 生成完了")

    print(f"\n  保存先: {ASSET_DIR}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    generate_all()
