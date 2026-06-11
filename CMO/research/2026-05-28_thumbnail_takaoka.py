#!/usr/bin/env python3
# note記事サムネ生成（高岡・デザイン版・1280x670）
# 高岡銅器にちなんだ銅色(カッパー/ブロンズ)基調。実写ではなくデザイングラフィック。
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 670
FONT = "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"

img = Image.new("RGB", (W, H))
px = img.load()

# 銅器を思わせるグラデ（上:深い焦茶 → 下:暗いブロンズ）
top = (26, 17, 12)
bot = (54, 33, 18)
for y in range(H):
    t = y / (H - 1)
    r = int(top[0] + (bot[0] - top[0]) * t)
    g = int(top[1] + (bot[1] - top[1]) * t)
    b = int(top[2] + (bot[2] - top[2]) * t)
    for x in range(W):
        px[x, y] = (r, g, b)

draw = ImageDraw.Draw(img, "RGBA")

# 右側に溶けた銅のような暖色グロー
glow_cx, glow_cy = int(W * 0.82), int(H * 0.46)
max_r = 540
for i in range(max_r, 0, -4):
    a = int(50 * (1 - i / max_r))
    if a <= 0:
        continue
    draw.ellipse([glow_cx - i, glow_cy - i, glow_cx + i, glow_cy + i],
                 fill=(206, 122, 58, a))  # copper

# 左下に可読性用の暗いグラデ帯
for y in range(H):
    t = max(0, (y - H * 0.42) / (H * 0.58))
    a = int(130 * t)
    if a > 0:
        draw.line([(0, y), (int(W * 0.64), y)], fill=(0, 0, 0, a))

def text_bold(xy, s, font, fill, sw=2):
    draw.text(xy, s, font=font, fill=fill, stroke_width=sw, stroke_fill=fill)

f_title = ImageFont.truetype(FONT, 92)
f_sub   = ImageFont.truetype(FONT, 46)
f_en    = ImageFont.truetype(FONT, 28)
f_tag   = ImageFont.truetype(FONT, 26)

MX = 84
COPPER = (224, 158, 96)

# タイトル（2行）
text_bold((MX, 138), "400年、ひとりで", f_title, (245, 240, 232), sw=2)
text_bold((MX, 248), "価値を生む。",   f_title, (245, 240, 232), sw=2)

# サブコピー（銅色アクセント）
text_bold((MX, 372), "富山・高岡の職人に学ぶ", f_sub, COPPER, sw=1)

# 区切りの細い線
draw.line([(MX, 440), (MX + 360, 440)], fill=(224, 158, 96, 200), width=3)

# 英語併記
draw.text((MX, 470), "Lessons from Takaoka's 400-year craftsmen",
          font=f_en, fill=(214, 206, 196, 255))

# 下部タグ
draw.text((MX, 600), "#高岡  #ものづくり  #soloentrepreneur",
          font=f_tag, fill=(168, 150, 132, 255))

img.save("/home/user/agent-team/CMO/outputs/2026-05-28_note_thumbnail_takaoka.png", "PNG")
print("saved")
