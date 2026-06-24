#!/usr/bin/env python3
"""小説『海の見える台所』の Kindle 表紙を確定描画で生成（AI画像生成でなくPIL描画＝A2非抵触）。
KDP推奨サイズ 1600x2560（縦・1.6:1）。"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "cover.png"
FONT = "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"
W, H = 1600, 2560

def font(sz): return ImageFont.truetype(FONT, sz)

img = Image.new("RGB", (W, H))
d = ImageDraw.Draw(img)

# --- 背景：夕暮れの空→海のグラデーション ---
horizon = int(H * 0.46)
# 空（上）：濃紺→橙
top = (22, 38, 66); mid = (212, 140, 96)
for y in range(0, horizon):
    t = y / horizon
    c = tuple(int(top[i] + (mid[i]-top[i])*t) for i in range(3))
    d.line([(0, y), (W, y)], fill=c)
# 海（下）：橙の照り返し→深い藍
sea_top = (150, 120, 120); sea_bot = (16, 28, 50)
for y in range(horizon, H):
    t = (y - horizon) / (H - horizon)
    c = tuple(int(sea_top[i] + (sea_bot[i]-sea_top[i])*t) for i in range(3))
    d.line([(0, y), (W, y)], fill=c)

# --- 水平線の光・遠い山影 ---
d.rectangle([0, horizon-3, W, horizon+1], fill=(240, 210, 170))
# 立山連峰の影（水平線の上に薄く）
pts = [(0, horizon)]
import math
peaks = [(0.12,40),(0.25,80),(0.4,55),(0.55,95),(0.7,60),(0.85,85),(1.0,45)]
for fx, ph in peaks:
    pts.append((int(W*fx), horizon - ph))
pts += [(W, horizon)]
d.polygon(pts, fill=(70, 78, 104))

# --- 海の照り返し（縦の光の帯） ---
for i in range(horizon, H, 14):
    a = max(0, 1 - (i-horizon)/(H-horizon))
    c = tuple(min(255, int(sea_top[k]*a + sea_bot[k]*(1-a) + 18*a)) for k in range(3))
    d.line([(W*0.5-2, i), (W*0.5+2, i)], fill=c)

# --- 窓枠モチーフ（「海の見える台所」＝窓から海）---
m = 150
d.rectangle([m, m, W-m, H-m], outline=(245, 240, 232), width=6)
d.line([(W//2, m), (W//2, horizon)], fill=(245, 240, 232, 120), width=4)
d.line([(m, horizon), (W-m, horizon)], fill=(245, 240, 232), width=4)

# --- タイトル ---
title = "海の見える台所"
ft = font(150)
tw = d.textlength(title, font=ft)
ty = int(H*0.62)
# 影で可読性
for dx,dy in [(3,3),(2,2)]:
    d.text(((W-tw)//2+dx, ty+dy), title, font=ft, fill=(10, 18, 34))
d.text(((W-tw)//2, ty), title, font=ft, fill=(248, 244, 236))

# サブ
sub = "富山湾の小さな港町の、食と再生の物語"
fs = font(46)
sw = d.textlength(sub, font=fs)
d.text(((W-sw)//2, ty+200), sub, font=fs, fill=(238, 224, 206))

# 著者（プレースホルダ）
au = "著　＿＿＿＿＿＿"
fa = font(44)
aw = d.textlength(au, font=fa)
d.text(((W-aw)//2, H-m-90), au, font=fa, fill=(230, 226, 218))

img.save(OUT, "PNG")
print(f"OK: {OUT} ({W}x{H})")
