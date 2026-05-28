#!/usr/bin/env python3
# note記事サムネ生成（デザイン版・1280x670）
# 注意：実写ではなく、IPAゴシックを使ったデザイングラフィックです。
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 670
FONT = "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"

img = Image.new("RGB", (W, H))
px = img.load()

# 夜明けグラデーション（上:濃紺 → 下:暖色）
top = (11, 22, 46)      # deep navy (5am sky)
bot = (40, 24, 16)      # warm dark
for y in range(H):
    t = y / (H - 1)
    r = int(top[0] + (bot[0] - top[0]) * t)
    g = int(top[1] + (bot[1] - top[1]) * t)
    b = int(top[2] + (bot[2] - top[2]) * t)
    for x in range(W):
        px[x, y] = (r, g, b)

draw = ImageDraw.Draw(img, "RGBA")

# 右側に夜明け/画面の光（暖色のソフトな放射光）
glow_cx, glow_cy = int(W * 0.80), int(H * 0.42)
max_r = 520
for i in range(max_r, 0, -4):
    a = int(46 * (1 - i / max_r))  # 外ほど薄く
    if a <= 0:
        continue
    col = (255, 176, 92, a)  # amber
    draw.ellipse([glow_cx - i, glow_cy - i, glow_cx + i, glow_cy + i], fill=col)

# 左下に読みやすさ用の暗いグラデ帯
for y in range(H):
    t = max(0, (y - H * 0.45) / (H * 0.55))
    a = int(120 * t)
    if a > 0:
        draw.line([(0, y), (int(W * 0.62), y)], fill=(0, 0, 0, a))

def text_bold(xy, s, font, fill, sw=2):
    draw.text(xy, s, font=font, fill=fill, stroke_width=sw, stroke_fill=fill)

f_title = ImageFont.truetype(FONT, 96)
f_sub   = ImageFont.truetype(FONT, 52)
f_en    = ImageFont.truetype(FONT, 30)
f_tag   = ImageFont.truetype(FONT, 26)

MX = 84
# タイトル（2行）
text_bold((MX, 150), "ひとりで会社を", f_title, (255, 255, 255), sw=2)
text_bold((MX, 262), "始めました。",   f_title, (255, 255, 255), sw=2)

# サブコピー（暖色アクセント）
text_bold((MX, 392), "社員は5人、全員AIです。", f_sub, (255, 196, 120), sw=1)

# 5人を示すモチーフ（小さな丸5個）
dot_y = 470
for i in range(5):
    cx = MX + 18 + i * 46
    draw.ellipse([cx - 12, dot_y - 12, cx + 12, dot_y + 12],
                 outline=(255, 196, 120, 230), width=3)
    draw.ellipse([cx - 4, dot_y - 4, cx + 4, dot_y + 4], fill=(255, 196, 120, 230))

# 英語併記
draw.text((MX, 512), "I run a company with 5 AI executives.",
          font=f_en, fill=(208, 214, 230, 255))

# 下部タグ
draw.text((MX, 600), "#AI  #soloentrepreneur  #buildinpublic",
          font=f_tag, fill=(150, 160, 180, 255))

img.save("/home/user/agent-team/CMO/outputs/2026-05-28_note_thumbnail.png", "PNG")
print("saved")
