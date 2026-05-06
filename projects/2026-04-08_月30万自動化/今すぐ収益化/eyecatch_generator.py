#!/usr/bin/env python3
"""
eyecatch_generator.py — note 用アイキャッチ画像生成

各 Vol について 1280x670 px（note 推奨サイズ）の PNG を自動生成する。
- 価格・タイトル・サブタイトルを大きく表示
- 統一感のある配色（柱別カラー）

【使い方】
  python eyecatch_generator.py
  → C_テンプレ販売/dist/eyecatch/Vol2.png 〜 Vol11.png が出力される
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent.parent / "C_テンプレ販売"
OUT = ROOT / "dist" / "eyecatch"
OUT.mkdir(parents=True, exist_ok=True)

WIDTH, HEIGHT = 1280, 670

# 日本語フォントを探す
JP_FONT_PATH = None
for c in [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
    "/usr/share/fonts/truetype/ipafont-gothic/ipag.ttf",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
]:
    if Path(c).exists():
        JP_FONT_PATH = c
        break

if not JP_FONT_PATH:
    print("[ERROR] 日本語フォントが見つかりません")
    exit(1)

print(f"[INFO] 使用フォント: {JP_FONT_PATH}")

# Vol 別メタデータ
VOLS = [
    {"id": "Vol2",  "title": "SNSコンテンツ\nカレンダー",      "subtitle": "30日分のテーマ + 50選",          "price": "¥680",   "color": "#E8743B"},
    {"id": "Vol3",  "title": "飲食店向け\nプロンプト集",        "subtitle": "Instagram/X 即使える 20本",       "price": "¥1,980", "color": "#D94E4E"},
    {"id": "Vol5",  "title": "確定申告\n準備5シート",          "subtitle": "青色申告 65万円控除対応",         "price": "¥1,480", "color": "#2E86AB"},
    {"id": "Vol6",  "title": "クライアント\n管理DB",            "subtitle": "案件・請求・契約 4テーブル連携",  "price": "¥1,980", "color": "#1A5490"},
    {"id": "Vol7",  "title": "週次レビュー\nテンプレ",          "subtitle": "毎週30分 KPT＋数値振り返り",      "price": "¥980",   "color": "#5C8001"},
    {"id": "Vol8",  "title": "士業向け\n営業メール 20選",       "subtitle": "税理士・社労士・行政書士",        "price": "¥1,980", "color": "#3E1E68"},
    {"id": "Vol9",  "title": "SEOブログ\n記事構成 20選",        "subtitle": "2,000〜8,000字対応",              "price": "¥1,980", "color": "#0F4C5C"},
    {"id": "Vol10", "title": "月次売上\nダッシュボード",        "subtitle": "柱別・月次・年間 自動集計",       "price": "¥1,480", "color": "#7C3626"},
    {"id": "Vol11", "title": "個人事業主向け\n契約書5種パック", "subtitle": "業務委託・NDA・月額顧問 ほか",    "price": "¥2,480", "color": "#1F5F3F"},
]


def hex_to_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def draw_eyecatch(meta: dict, out_path: Path):
    main_color = hex_to_rgb(meta["color"])
    img = Image.new("RGB", (WIDTH, HEIGHT), main_color)
    draw = ImageDraw.Draw(img)

    # 左側に白いボックス（タイトル・価格）
    box_w = int(WIDTH * 0.62)
    draw.rectangle([(40, 40), (box_w, HEIGHT - 40)], fill="white")

    # タイトル
    f_title = ImageFont.truetype(JP_FONT_PATH, 64)
    f_subtitle = ImageFont.truetype(JP_FONT_PATH, 28)
    f_price = ImageFont.truetype(JP_FONT_PATH, 88)
    f_label = ImageFont.truetype(JP_FONT_PATH, 24)
    f_id = ImageFont.truetype(JP_FONT_PATH, 22)

    # Vol ID（左上）
    draw.text((70, 60), f"テンプレ販売 {meta['id']}", font=f_id, fill=main_color)

    # タイトル（複数行）
    title_y = 130
    for line in meta["title"].split("\n"):
        draw.text((70, title_y), line, font=f_title, fill="black")
        title_y += 80

    # サブタイトル（黒の下線付き）
    draw.text((70, HEIGHT - 200), meta["subtitle"], font=f_subtitle, fill="#444444")
    draw.line([(70, HEIGHT - 165), (70 + 300, HEIGHT - 165)], fill=main_color, width=4)

    # 右側に価格表示
    price_x = box_w + 60
    draw.text((price_x, 200), "¥価格", font=f_label, fill="white")
    draw.text((price_x, 240), meta["price"], font=f_price, fill="white")
    draw.text((price_x, 360), "買い切り型", font=f_label, fill="white")
    draw.text((price_x, 390), "永久利用OK", font=f_label, fill="white")

    img.save(out_path, "PNG")
    print(f"[OK] {out_path}")


def main():
    for meta in VOLS:
        out = OUT / f"{meta['id']}.png"
        draw_eyecatch(meta, out)
    print(f"\n{len(VOLS)} 件のアイキャッチを {OUT} に生成。")


if __name__ == "__main__":
    main()
