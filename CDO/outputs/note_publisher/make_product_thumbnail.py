#!/usr/bin/env python3
"""
有料デジタル商品（note）のサムネ（見出し画像）を確定的に生成する。

A2「画像生成AIなし」に抵触しない＝AI生成ではなくテキスト×図形の確定描画。
情報商材のカバーは写真風(A3)より「タイトルが読めるデザインカバー」が適切なため、
日本語フォント(IPAGothic)で可読性の高いカバーをPNG出力する。

使い方:
  python3 make_product_thumbnail.py        # 定義済みの全商品を生成
出力: 各商品フォルダ直下に cover.png（1280x670, note見出し画像比率1.91:1）
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[3]
FONT = "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"
W, H = 1280, 670

# 商品定義（背景色, アクセント色, 文字色, タイトル, サブ, 補足, 価格帯ラベル, 出力先）
PRODUCTS = [
    dict(
        out=REPO / "projects/2026-06-23_収益化_AIひとり会社商品/prompt_pack/cover.png",
        bg=(22, 32, 52), accent=(94, 191, 168), fg=(238, 242, 248),
        kicker="フリーランス・個人事業・副業のための",
        title=["AI業務自動化", "プロンプト集 Vol.1"],
        sub="メール・見積・SNS・振り返りまで、実務でそのまま使える30本",
        foot="ChatGPT / Claude / Gemini 対応 ・ コピーして穴埋めするだけ",
    ),
    dict(
        out=REPO / "projects/2026-06-23_収益化_AIひとり会社商品/template_kit/cover.png",
        bg=(26, 42, 34), accent=(212, 170, 92), fg=(240, 244, 238),
        kicker="ひとり会社の日々の事務を、すぐ使える書式に",
        title=["ひとり会社の", "実務テンプレ集 全8種"],
        sub="請求・見積・案件管理など8種。案件別の「実質時給」も出せる・CSV同梱",
        foot="Googleスプレッドシート / Excel / Numbers 対応",
    ),
]


def font(sz, bold_path=FONT):
    return ImageFont.truetype(bold_path, sz)


def wrap(draw, text, fnt, max_w):
    """日本語向け：文字単位で max_w に収まるよう折り返す。"""
    lines, cur = [], ""
    for ch in text:
        if draw.textlength(cur + ch, font=fnt) <= max_w:
            cur += ch
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def make(p):
    img = Image.new("RGB", (W, H), p["bg"])
    d = ImageDraw.Draw(img)

    # 左の縦アクセントバー
    d.rectangle([0, 0, 14, H], fill=p["accent"])
    # 右上の控えめな装飾（テキストに干渉しない角の角丸枠）
    d.rounded_rectangle([W - 150, -90, W + 90, 150], radius=40,
                        outline=p["accent"], width=3)

    margin = 86
    y = 96

    # キッカー（小見出し）
    fk = font(30)
    d.text((margin, y), p["kicker"], font=fk, fill=p["accent"])
    y += 64

    # タイトル（大）
    ft = font(78)
    for line in p["title"]:
        for wl in wrap(d, line, ft, W - margin - 120):
            d.text((margin, y), wl, font=ft, fill=p["fg"])
            y += 96
    y += 14

    # アクセントの下線
    d.rectangle([margin, y, margin + 150, y + 6], fill=p["accent"])
    y += 44

    # サブコピー
    fs = font(36)
    for wl in wrap(d, p["sub"], fs, W - margin - 90):
        d.text((margin, y), wl, font=fs, fill=p["fg"])
        y += 50

    # フッター（補足・帯）
    ff = font(28)
    fy = H - 78
    d.rectangle([0, fy - 22, W, H], fill=tuple(min(255, c + 10) for c in p["bg"]))
    d.text((margin, fy), p["foot"], font=ff, fill=p["accent"])

    p["out"].parent.mkdir(parents=True, exist_ok=True)
    img.save(p["out"], "PNG")
    print(f"✅ {p['out'].relative_to(REPO)}  ({W}x{H})")


if __name__ == "__main__":
    for prod in PRODUCTS:
        make(prod)
    print("完了：note の見出し画像に cover.png をアップロードしてください。")
