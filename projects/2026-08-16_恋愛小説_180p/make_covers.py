#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
雨晴を待つ / Where the Rain Clears — マガジン表紙＋全12話サムネ生成
- 画像生成AIは不使用（A2順守）。外部素材の取得もしない（A1）。
- PIL で「雨晴海岸の夜明け（海・女岩・立山連峰・朝日）」を図案として描画＝統一デザインの表紙シリーズ。
- note 見出し画像比率 1280x670。出力: repo直下 thumbnails/amaharashi_cover.jpg / amaharashi_epNN.jpg
- A4: 特定の私有地/個人を写さない図案。A5: 実写ではなくイメージ図案（本文にも明記）。
"""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "thumbnails"
OUT.mkdir(exist_ok=True)
FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
W, H = 1280, 670
HORIZON = int(H * 0.60)

def font(sz): return ImageFont.truetype(FONT, sz)

def lerp(a, b, t): return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

def vgrad(draw, x0, y0, x1, y1, stops):
    """縦グラデ。stops=[(pos0..1, (r,g,b)), ...]"""
    h = y1 - y0
    for yy in range(y0, y1):
        t = (yy - y0) / max(1, h - 1)
        # 区間探索
        for i in range(len(stops) - 1):
            p0, c0 = stops[i]; p1, c1 = stops[i + 1]
            if p0 <= t <= p1:
                col = lerp(c0, c1, (t - p0) / max(1e-6, p1 - p0)); break
        else:
            col = stops[-1][1]
        draw.line([(x0, yy), (x1, yy)], fill=col)

def mountains(img, base_y, palette):
    """立山連峰＝多層シルエット＋雪冠。palette=(遠, 近)"""
    d = ImageDraw.Draw(img)
    import random
    for layer, (col, snow, amp, yb) in enumerate([
        (palette[0], (222, 226, 236), 70, base_y - 6),
        (palette[1], (238, 240, 248), 104, base_y + 6),
    ]):
        rnd = random.Random(1234 + layer)
        pts = [(0, yb)]
        x = 0
        peaks = []
        while x <= W:
            step = rnd.randint(70, 150)
            x += step
            peak = yb - rnd.randint(int(amp * 0.4), amp)
            pts.append((x, peak)); peaks.append((x, peak))
        pts += [(W, yb), (W, base_y + 120), (0, base_y + 120)]
        d.polygon(pts, fill=col)
        # 雪冠
        for (px, py) in peaks:
            d.polygon([(px, py), (px - 16, py + 26), (px + 16, py + 26)], fill=snow)

def sun(img, cx, cy, r, core, glow):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(r * 3, 0, -1):
        a = int(120 * (1 - i / (r * 3)) ** 2)
        d.ellipse([cx - i, cy - i, cx + i, cy + i], fill=glow + (a,))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=core + (255,))
    layer = layer.filter(ImageFilter.GaussianBlur(2))
    img.alpha_composite(layer)

def meiwa(img, x, y, scale=1.0):
    d = ImageDraw.Draw(img)
    w = int(58 * scale); h = int(46 * scale)
    d.polygon([(x - w, y), (x - int(w*0.5), y - h), (x + int(w*0.3), y - int(h*0.8)),
               (x + w, y)], fill=(28, 30, 46))
    # 女岩の松（数本）
    for dx in (-10, 2, 12):
        d.line([(x + dx, y - int(h*0.7)), (x + dx, y - h - int(10*scale))], fill=(24, 26, 40), width=2)
        d.ellipse([x + dx - 7, y - h - int(16*scale), x + dx + 7, y - h - int(4*scale)], fill=(22, 30, 30))

def sea(img, horizon, sky_low, deep):
    d = ImageDraw.Draw(img)
    vgrad(d, 0, horizon, W, H, [(0.0, sky_low), (1.0, deep)])
    # 日の反射柱
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dl = ImageDraw.Draw(layer)
    for yy in range(horizon, H, 3):
        t = (yy - horizon) / (H - horizon)
        ww = int(24 + t * 120)
        a = int(150 * (1 - t))
        dl.line([(W//2 - ww//2, yy), (W//2 + ww//2, yy)], fill=(250, 224, 150, a), width=2)
    # さざなみ
    for yy in range(horizon + 10, H, 12):
        a = int(60 * (1 - (yy - horizon) / (H - horizon)))
        dl.line([(0, yy), (W, yy)], fill=(255, 255, 255, max(0, a)))
    layer = layer.filter(ImageFilter.GaussianBlur(1))
    img.alpha_composite(layer)

def draw_scene(sky_stops, sun_core, sun_glow, mtn_pal, sea_low, sea_deep):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    d = ImageDraw.Draw(img)
    vgrad(d, 0, 0, W, HORIZON, sky_stops)
    # stars（上部）
    import random
    rnd = random.Random(7)
    for _ in range(70):
        x = rnd.randint(0, W); y = rnd.randint(0, int(HORIZON * 0.5))
        a = rnd.randint(40, 160)
        d.point((x, y), fill=(255, 255, 255))
    sun(img, W // 2, HORIZON - 26, 42, sun_core, sun_glow)
    mountains(img, HORIZON, mtn_pal)
    sea(img, HORIZON, sea_low, sea_deep)
    meiwa(img, int(W * 0.66), HORIZON + 26, 1.0)
    return img

def text_with_shadow(d, xy, s, fnt, fill=(255,255,255), sh=(0,0,0), off=2, anchor="la"):
    x, y = xy
    d.text((x+off, y+off), s, font=fnt, fill=sh, anchor=anchor)
    d.text((x, y), s, font=fnt, fill=fill, anchor=anchor)

# 季節/情感で空色を12話ぶん変える（構図は統一）
def sky_for(mood):
    table = {
        "winter_dawn": [(0.0,(20,28,58)),(0.45,(70,74,120)),(0.7,(206,120,120)),(1.0,(246,206,120))],
        "spring":      [(0.0,(38,54,92)),(0.5,(120,120,160)),(0.78,(238,170,150)),(1.0,(250,224,150))],
        "night_blue":  [(0.0,(10,16,40)),(0.55,(28,40,90)),(0.82,(60,80,140)),(1.0,(150,150,190))],
        "summer":      [(0.0,(30,70,130)),(0.5,(90,140,190)),(0.8,(220,200,170)),(1.0,(250,235,180))],
        "autumn":      [(0.0,(46,40,78)),(0.5,(150,110,120)),(0.8,(236,168,120)),(1.0,(250,214,140))],
        "winter":      [(0.0,(26,34,66)),(0.5,(80,92,130)),(0.82,(180,150,160)),(1.0,(226,206,190))],
        "gold_dawn":   [(0.0,(22,26,60)),(0.4,(80,70,120)),(0.66,(224,138,110)),(1.0,(252,214,120))],
    }
    return table[mood]

SUN = {"warm":((255,244,214),(250,190,120)), "cool":((235,240,255),(150,180,230)),
       "gold":((255,250,220),(252,196,110))}
MTN = {"cool":((58,66,110),(40,48,86)), "warm":((92,74,104),(64,52,84)), "grey":((70,80,110),(52,60,88))}

# 各話: (mood, sun, mtn, 海上端色, 海底色, サブJP, サブEN)
EP = [
 ("winter_dawn","warm","cool",(232,180,130),(18,26,54),"海の見える駅","The Station by the Sea"),
 ("spring","warm","cool",(238,196,150),(22,34,66),"汀という喫茶店","The Coffee Shop Called Migiwa"),
 ("night_blue","cool","cool",(80,110,170),(8,14,36),"ほたるいかの夜","The Night of the Firefly Squid"),
 ("spring","warm","cool",(240,200,150),(22,36,70),"女岩の約束","The Promise at Meiwa Rock"),
 ("spring","warm","cool",(242,206,150),(24,38,72),"白えびの季節","The Season of White Shrimp"),
 ("summer","cool","cool",(226,206,170),(20,60,110),"海王丸の帆","The Sails of the Kaiwo Maru"),
 ("autumn","warm","warm",(236,180,130),(30,30,60),"開かずの引き出し","The Locked Drawer"),
 ("autumn","warm","warm",(232,172,128),(28,32,62),"すれ違いの秋","A Misunderstanding in Autumn"),
 ("autumn","gold","warm",(240,190,130),(26,30,58),"新湊の夕暮れ","Dusk at Shinminato"),
 ("winter","cool","grey",(200,178,180),(20,30,58),"寒ぶり起こし","The Thunder That Wakes the Yellowtail"),
 ("winter","cool","grey",(206,196,200),(24,34,62),"雪の予報","The Forecast of Snow"),
 ("gold_dawn","gold","cool",(246,206,140),(20,28,58),"冬の夜明け","The Winter Daybreak"),
]

def compose(mood, sunk, mtnk, sea_low, sea_deep, title_lines, ep_label=None, sub=None, sub_en=None):
    img = draw_scene(sky_for(mood), *SUN[sunk], MTN[mtnk], sea_low, sea_deep)
    d = ImageDraw.Draw(img)
    # 下部に可読性の帯
    band = Image.new("RGBA", (W, 220), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    for i in range(220):
        bd.line([(0, i), (W, i)], fill=(6, 10, 24, int(150 * (i / 220))))
    img.alpha_composite(band, (0, H - 220))
    if ep_label:
        text_with_shadow(d, (60, H - 176), ep_label, font(30), fill=(250, 214, 150))
        text_with_shadow(d, (60, H - 132), title_lines[0], font(64), fill=(255,255,255))
        text_with_shadow(d, (60, H - 60), sub, font(40), fill=(240,240,245))
        text_with_shadow(d, (W-60, H-58), sub_en, font(26), fill=(210,214,230), anchor="ra")
    else:
        # 表紙
        text_with_shadow(d, (W//2, H//2 - 60), title_lines[0], font(96), fill=(255,255,255), anchor="ma")
        text_with_shadow(d, (W//2, H//2 + 44), title_lines[1], font(44), fill=(244,224,180), anchor="ma")
        text_with_shadow(d, (W//2, H - 92), title_lines[2], font(30), fill=(220,224,236), anchor="ma")
    return img.convert("RGB")

# 表紙
cov = compose("gold_dawn","gold","cool",(244,204,140),(18,26,56),
              ["雨晴を待つ","Where the Rain Clears","富山湾・海の見える町の恋物語 ｜ 全12話・日英併記"])
cov.save(OUT / "amaharashi_cover.jpg", quality=88)
print("saved", OUT / "amaharashi_cover.jpg")

# 各話
for i, (mood, sk, mt, slo, sdp, sub, suben) in enumerate(EP, 1):
    im = compose(mood, sk, mt, slo, sdp, ["雨晴を待つ"], ep_label=f"第{i}話 ／ Episode {i}"+("（最終話）" if i==12 else ""),
                 sub=sub, sub_en=suben)
    p = OUT / f"amaharashi_ep{i:02d}.jpg"
    im.save(p, quality=88)
    print("saved", p)
print("DONE")
