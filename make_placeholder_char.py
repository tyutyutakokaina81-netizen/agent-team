#!/usr/bin/env python3
"""Pillow で高岡アイのプレースホルダーキャラクター画像を生成（SD代替）"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ASSET_DIR = Path(__file__).parent / "CMO" / "assets" / "announcer"
ASSET_DIR.mkdir(parents=True, exist_ok=True)

def make_char(out_path: Path, w: int, h: int, label: str):
    img = Image.new("RGBA", (w, h), (10, 25, 70, 255))
    d = ImageDraw.Draw(img)

    # グラデーション風の背景ストライプ
    for i in range(0, h, 4):
        alpha = int(255 * (1 - i / h) * 0.3)
        d.line([(0, i), (w, i)], fill=(30, 80, 160, alpha))

    # 人物シルエット（楕円＋長方形で簡易表現）
    cx = w // 2
    head_y = int(h * 0.18)
    head_r = int(w * 0.10)
    # 頭
    d.ellipse([cx - head_r, head_y - head_r,
               cx + head_r, head_y + head_r],
              fill=(255, 210, 180, 255))
    # 髪
    d.ellipse([cx - head_r, head_y - head_r - 6,
               cx + head_r, head_y + int(head_r * 0.6)],
              fill=(30, 20, 20, 255))
    d.rectangle([cx - head_r - 5, head_y,
                 cx - head_r + 8, head_y + head_r + 20],
                fill=(30, 20, 20, 255))
    d.rectangle([cx + head_r - 8, head_y,
                 cx + head_r + 5, head_y + head_r + 20],
                fill=(30, 20, 20, 255))

    # 体（ネイビーのスーツ）
    body_top = head_y + head_r + 2
    body_w = int(w * 0.32)
    body_h = int(h * 0.45)
    d.rounded_rectangle([cx - body_w // 2, body_top,
                          cx + body_w // 2, body_top + body_h],
                         radius=10, fill=(15, 40, 100, 255))
    # 白シャツ/ブラウス
    d.polygon([(cx - 10, body_top), (cx + 10, body_top),
               (cx + 5, body_top + 30), (cx - 5, body_top + 30)],
              fill=(240, 240, 240, 255))

    # マイクのアイコン
    mic_x = cx + int(body_w * 0.4)
    mic_y = int(body_top + body_h * 0.3)
    d.rounded_rectangle([mic_x - 6, mic_y - 14, mic_x + 6, mic_y + 14],
                         radius=5, fill=(160, 160, 160, 255))
    d.line([mic_x, mic_y + 14, mic_x, mic_y + 28], fill=(160, 160, 160), width=3)
    d.arc([mic_x - 12, mic_y + 6, mic_x + 12, mic_y + 32],
          start=0, end=180, fill=(160, 160, 160), width=3)

    # 銅製ブローチ（胸元アクセント）
    d.ellipse([cx - 18, body_top + 20, cx - 8, body_top + 30],
              fill=(180, 120, 40, 255), outline=(210, 160, 60, 255), width=2)

    # 下部テロップバー
    bar_h = 60
    bar = Image.new("RGBA", (w, bar_h), (8, 20, 60, 220))
    img.paste(bar, (0, h - bar_h), bar)

    try:
        font_lg = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 22)
        font_sm = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 14)
    except Exception:
        try:
            font_lg = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
            font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        except Exception:
            font_lg = font_sm = ImageFont.load_default()

    d2 = ImageDraw.Draw(img)
    d2.text((cx, h - bar_h + 10), "高岡アイ", font=font_lg,
            fill=(255, 255, 255, 255), anchor="mt")
    d2.text((cx, h - bar_h + 36), "富山・高岡観光ナビゲーター", font=font_sm,
            fill=(160, 200, 255, 255), anchor="mt")

    out = img.convert("RGB")
    out.save(out_path, "PNG")
    print(f"  ✅ {out_path.name} 生成完了 ({w}x{h})")


if __name__ == "__main__":
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  高岡アイ キャラクター画像生成（Pillow版）")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    make_char(ASSET_DIR / "ai_takaoka_main.png", 512, 768, "main")
    make_char(ASSET_DIR / "ai_takaoka_smile.png", 512, 512, "smile")
    make_char(ASSET_DIR / "ai_takaoka_guide.png", 512, 768, "guide")
    print(f"\n  保存先: {ASSET_DIR}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
