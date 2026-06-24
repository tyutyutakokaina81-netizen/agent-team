#!/usr/bin/env python3
# note アイキャッチ画像生成（確定レンダリング・実写なし／A2準拠）
# サイズ: 1280x670（note 推奨比 ≒1.91:1）
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 670
FONT = "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"
OUT = "note_thumb.png"

# 海の色（富山湾）= 深い藍 → ティールのグラデーション
top = (16, 52, 74)      # 深い藍
bottom = (28, 110, 105)  # ティール
img = Image.new("RGB", (W, H), top)
px = img.load()
for y in range(H):
    t = y / (H - 1)
    r = int(top[0] + (bottom[0] - top[0]) * t)
    g = int(top[1] + (bottom[1] - top[1]) * t)
    b = int(top[2] + (bottom[2] - top[2]) * t)
    for x in range(W):
        px[x, y] = (r, g, b)
d = ImageDraw.Draw(img)

# 水平線（波）のアクセント
for i, yy in enumerate([H - 150, H - 110, H - 78]):
    alpha = 70 - i * 18
    d.line([(0, yy), (W, yy)], fill=(255, 255, 255, alpha), width=2)

f_main = ImageFont.truetype(FONT, 78)
f_sub = ImageFont.truetype(FONT, 38)
f_tag = ImageFont.truetype(FONT, 30)
f_url = ImageFont.truetype(FONT, 26)

def center(text, font, y, fill, ls=0):
    bbox = d.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    d.text(((W - w) / 2, y), text, font=font, fill=fill, spacing=ls)

# 上部の小ラベル
label = "TOYAMA / TAKAOKA / HIMI"
bbox = d.textbbox((0, 0), label, font=f_tag)
lw = bbox[2] - bbox[0]
d.text(((W - lw) / 2, 92), label, font=f_tag, fill=(150, 220, 205))

# メインタイトル（2行）
center("富山の味、", f_main, 188, (255, 255, 255))
center("地元目線で。", f_main, 286, (255, 255, 255))

# 区切り線
d.line([(W/2 - 90, 410), (W/2 + 90, 410)], fill=(150, 220, 205), width=3)

# サブ
center("白えび・氷見の魚・ます寿司・地酒", f_sub, 438, (224, 240, 236))
center("お取り寄せの探し方つき／短編小説も無料", f_tag, 500, (170, 205, 198))

# 下部URL帯
d.rectangle([(0, H - 56), (W, H)], fill=(10, 38, 54))
url = "tyutyutakokaina81-netizen.github.io/agent-team/toyama"
bbox = d.textbbox((0, 0), url, font=f_url)
uw = bbox[2] - bbox[0]
d.text(((W - uw) / 2, H - 44), url, font=f_url, fill=(190, 215, 210))

img.save(OUT, "PNG")
print("saved", OUT, img.size)
