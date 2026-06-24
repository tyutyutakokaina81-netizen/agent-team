#!/usr/bin/env python3
# 配信キット6本ぶんの note 見出し画像（文字デザイン・1280x670）を生成。
# 出力: CDO/outputs/note_publisher/share_thumbs/01.png .. 06.png
# 実写ではなく確定レンダリング（A2準拠）。publish_share_notes.py が番号で対応付けて自動アップする。
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

W, H = 1280, 670
FONT = "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"
# Macで実行する場合のフォント候補（Linuxのパスが無ければ順に探す）
FONT_CANDS = [
    FONT,
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
]
OUT_DIR = Path(__file__).resolve().parent / "share_thumbs"
URL = "tyutyutakokaina81-netizen.github.io/agent-team/toyama"

def font(sz):
    for c in FONT_CANDS:
        if Path(c).exists():
            return ImageFont.truetype(c, sz)
    return ImageFont.load_default()

# (上段ラベル, メイン1, メイン2, サブ, 上色, 下色, 帯色)
CARDS = [
    ("TOYAMA SEAFOOD", "甘くて、手が届く。", "富山の紅ズワイガニ", "「高志の紅ガニ」をお取り寄せ・ふるさと納税で",
     (90, 28, 30), (180, 70, 55), (60, 16, 18)),
    ("TOYAMA WINTER", "冬の富山の、主役。", "氷見の寒ブリ", "天然と養殖の違い・刺身・ブリしゃぶの選び方",
     (16, 40, 74), (32, 96, 150), (10, 28, 54)),
    ("TOYAMA CRAFT", "祝いの席の、郷土の味。", "富山の細工かまぼこ", "鯛・鶴亀の引き出物文化と、お取り寄せ",
     (120, 40, 70), (200, 90, 120), (80, 24, 50)),
    ("TOYAMA DEEP SEA", "深海の、上品な白身。", "富山のげんげ（幻魚）", "ぷるぷるの干物・唐揚げ・汁物の食べ方",
     (18, 52, 60), (40, 110, 110), (10, 34, 40)),
    ("TOYAMA KOMBU", "おにぎりは、とろろ昆布。", "富山の昆布", "消費量トップクラスの食文化と、毎日の使い方",
     (28, 70, 40), (60, 130, 80), (16, 48, 28)),
    ("TOYAMA CRAFT BEER", "立山の水が、育てる一杯。", "富山の地ビール", "タイプ別の選び方と、飲み比べ・ギフト",
     (110, 78, 20), (190, 150, 55), (74, 52, 14)),
]

def make(idx, label, m1, m2, sub, top, bottom, band):
    img = Image.new("RGB", (W, H), top); px = img.load()
    for y in range(H):
        t = y / (H - 1)
        row = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        for x in range(W): px[x, y] = row
    d = ImageDraw.Draw(img)
    f_lbl, f_m1, f_m2, f_sub, f_url = font(30), font(50), font(72), font(34), font(26)
    def center(text, fnt, y, fill):
        b = d.textbbox((0, 0), text, font=fnt); w = b[2] - b[0]
        d.text(((W - w) / 2, y), text, font=fnt, fill=fill)
    light = tuple(min(255, c + 150) for c in bottom)
    center(label, f_lbl, 86, light)
    center(m1, f_m1, 168, (255, 255, 255))
    center(m2, f_m2, 248, (255, 255, 255))
    d.line([(W/2 - 90, 386), (W/2 + 90, 386)], fill=light, width=3)
    center(sub, f_sub, 420, (240, 240, 240))
    d.rectangle([(0, H - 56), (W, H)], fill=band)
    b = d.textbbox((0, 0), URL, font=f_url); uw = b[2] - b[0]
    d.text(((W - uw) / 2, H - 44), URL, font=f_url, fill=(225, 225, 225))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    p = OUT_DIR / f"{idx:02d}.png"
    img.save(p, "PNG")
    return p

if __name__ == "__main__":
    for i, c in enumerate(CARDS, 1):
        p = make(i, *c)
        print("saved", p)
