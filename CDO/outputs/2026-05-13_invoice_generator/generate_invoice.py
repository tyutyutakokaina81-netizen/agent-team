#!/usr/bin/env python3
"""
請求書PDFジェネレーター

事業柱A（SEO記事制作代行）想定の請求書を生成する。
日本語表示には reportlab 内蔵の CID フォント（HeiseiKakuGo-W5 / HeiseiMin-W3）を使用するため、
追加のフォントファイル設置は不要。

Usage:
    python3 generate_invoice.py [出力先パス]

    引数を省略した場合は以下に出力する:
      <repo_root>/CFO/outputs/<YYYY-MM-DD>_dummy_invoice.pdf
"""

import sys
from datetime import date, timedelta
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas


FONT_GOTHIC = "HeiseiKakuGo-W5"
FONT_MINCHO = "HeiseiMin-W3"


def register_fonts() -> None:
    pdfmetrics.registerFont(UnicodeCIDFont(FONT_GOTHIC))
    pdfmetrics.registerFont(UnicodeCIDFont(FONT_MINCHO))


def yen(amount: int) -> str:
    return f"¥{amount:,}"


def draw_invoice(c: canvas.Canvas, data: dict) -> None:
    width, height = A4

    # タイトル
    c.setFont(FONT_GOTHIC, 24)
    c.drawCentredString(width / 2, height - 25 * mm, "請求書")

    # 請求番号・発行日・支払期日（右上）
    c.setFont(FONT_GOTHIC, 9)
    right_x = width - 20 * mm
    y = height - 38 * mm
    c.drawRightString(right_x, y, f"請求書番号: {data['invoice_no']}")
    c.drawRightString(right_x, y - 5 * mm, f"発行日:     {data['issue_date']}")
    c.drawRightString(right_x, y - 10 * mm, f"支払期日:   {data['due_date']}")

    # 宛先（左）
    left_x = 20 * mm
    y = height - 55 * mm
    c.setFont(FONT_GOTHIC, 14)
    c.drawString(left_x, y, f"{data['client_name']}  御中")
    c.setLineWidth(0.5)
    c.line(left_x, y - 2 * mm, left_x + 100 * mm, y - 2 * mm)

    c.setFont(FONT_MINCHO, 10)
    c.drawString(left_x, y - 10 * mm, "下記の通りご請求申し上げます。")

    # 合計金額ボックス
    y_total = y - 22 * mm
    c.setFillColor(colors.HexColor("#f0f4f8"))
    c.rect(left_x, y_total - 12 * mm, 110 * mm, 14 * mm, stroke=1, fill=1)
    c.setFillColor(colors.black)
    c.setFont(FONT_GOTHIC, 11)
    c.drawString(left_x + 4 * mm, y_total - 4 * mm, "ご請求金額（税込）")
    c.setFont(FONT_GOTHIC, 18)
    total = data["total_incl_tax"]
    c.drawRightString(left_x + 106 * mm, y_total - 9 * mm, yen(total) + "  -")

    # 発行元情報（右）
    issuer_x = width - 80 * mm
    y_issuer = y_total
    c.setFont(FONT_GOTHIC, 10)
    c.drawString(issuer_x, y_issuer, data["issuer"]["name"])
    c.setFont(FONT_MINCHO, 9)
    for i, line in enumerate(data["issuer"]["address_lines"], start=1):
        c.drawString(issuer_x, y_issuer - i * 4.5 * mm, line)
    base = y_issuer - (len(data["issuer"]["address_lines"]) + 1) * 4.5 * mm
    c.drawString(issuer_x, base, f"TEL: {data['issuer']['tel']}")
    c.drawString(issuer_x, base - 4.5 * mm, f"Email: {data['issuer']['email']}")
    if data["issuer"].get("registration_no"):
        c.drawString(issuer_x, base - 9 * mm, f"登録番号: {data['issuer']['registration_no']}")

    # 明細テーブル
    table_top = y_total - 30 * mm
    col_x = [left_x, left_x + 95 * mm, left_x + 115 * mm, left_x + 140 * mm, left_x + 170 * mm]
    headers = ["項目", "数量", "単価", "金額"]

    c.setFillColor(colors.HexColor("#34495e"))
    c.rect(left_x, table_top - 8 * mm, 170 * mm, 8 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont(FONT_GOTHIC, 10)
    c.drawString(col_x[0] + 2 * mm, table_top - 5.5 * mm, headers[0])
    c.drawRightString(col_x[2] - 2 * mm, table_top - 5.5 * mm, headers[1])
    c.drawRightString(col_x[3] - 2 * mm, table_top - 5.5 * mm, headers[2])
    c.drawRightString(col_x[4] - 2 * mm, table_top - 5.5 * mm, headers[3])
    c.setFillColor(colors.black)

    row_h = 9 * mm
    y_row = table_top - 8 * mm
    c.setFont(FONT_MINCHO, 10)
    for item in data["items"]:
        y_row -= row_h
        c.drawString(col_x[0] + 2 * mm, y_row + 3 * mm, item["description"])
        c.drawRightString(col_x[2] - 2 * mm, y_row + 3 * mm, f"{item['qty']} {item.get('unit', '')}")
        c.drawRightString(col_x[3] - 2 * mm, y_row + 3 * mm, yen(item["unit_price"]))
        c.drawRightString(col_x[4] - 2 * mm, y_row + 3 * mm, yen(item["qty"] * item["unit_price"]))
        c.setStrokeColor(colors.HexColor("#cccccc"))
        c.line(left_x, y_row, left_x + 170 * mm, y_row)

    # 小計・消費税・合計
    subtotal = sum(it["qty"] * it["unit_price"] for it in data["items"])
    tax_rate = data.get("tax_rate", 0.10)
    tax = int(subtotal * tax_rate)
    total_calc = subtotal + tax

    y_sum = y_row - 6 * mm
    label_x = left_x + 115 * mm
    value_x = left_x + 170 * mm
    c.setFont(FONT_GOTHIC, 10)
    c.drawRightString(label_x, y_sum, "小計")
    c.drawRightString(value_x, y_sum, yen(subtotal))
    y_sum -= 6 * mm
    c.drawRightString(label_x, y_sum, f"消費税（{int(tax_rate * 100)}%）")
    c.drawRightString(value_x, y_sum, yen(tax))
    y_sum -= 7 * mm
    c.setLineWidth(1)
    c.setStrokeColor(colors.black)
    c.line(left_x + 95 * mm, y_sum + 5 * mm, left_x + 170 * mm, y_sum + 5 * mm)
    c.setFont(FONT_GOTHIC, 12)
    c.drawRightString(label_x, y_sum, "合計（税込）")
    c.drawRightString(value_x, y_sum, yen(total_calc))

    # 振込先
    y_bank = y_sum - 18 * mm
    c.setFont(FONT_GOTHIC, 11)
    c.drawString(left_x, y_bank, "お振込先")
    c.setLineWidth(0.5)
    c.line(left_x, y_bank - 2 * mm, left_x + 60 * mm, y_bank - 2 * mm)
    c.setFont(FONT_MINCHO, 10)
    bank = data["bank"]
    c.drawString(left_x, y_bank - 8 * mm, f"{bank['bank_name']}  {bank['branch']}")
    c.drawString(left_x, y_bank - 13 * mm, f"{bank['account_type']}  {bank['account_no']}")
    c.drawString(left_x, y_bank - 18 * mm, f"口座名義: {bank['account_holder']}")

    # 備考
    y_note = y_bank - 30 * mm
    c.setFont(FONT_GOTHIC, 10)
    c.drawString(left_x, y_note, "備考")
    c.line(left_x, y_note - 2 * mm, left_x + 30 * mm, y_note - 2 * mm)
    c.setFont(FONT_MINCHO, 9)
    for i, line in enumerate(data["notes"], start=1):
        c.drawString(left_x, y_note - 4 * mm - i * 4.5 * mm, line)

    # フッター
    c.setFont(FONT_MINCHO, 8)
    c.setFillColor(colors.grey)
    c.drawCentredString(width / 2, 12 * mm, "本書類はサンプル（ダミー）として生成されました。")


def build_dummy_data() -> dict:
    today = date(2026, 5, 13)
    items = [
        {"description": "SEO記事制作（2,000字／キーワード設計込み）", "qty": 8, "unit": "本", "unit_price": 15000},
        {"description": "SEO記事制作（3,000字／競合調査込み）",     "qty": 4, "unit": "本", "unit_price": 18000},
        {"description": "構成案作成のみ（2,000字想定）",              "qty": 3, "unit": "本", "unit_price": 5000},
    ]
    subtotal = sum(it["qty"] * it["unit_price"] for it in items)
    tax = int(subtotal * 0.10)
    return {
        "invoice_no": "INV-2026-0513-001",
        "issue_date": today.strftime("%Y年%m月%d日"),
        "due_date": (today + timedelta(days=30)).strftime("%Y年%m月%d日"),
        "client_name": "株式会社サンプルコーポレーション",
        "issuer": {
            "name": "AIエージェントチーム合同会社",
            "address_lines": [
                "〒100-0001",
                "東京都千代田区千代田1-2-3",
                "サンプルビル 4F",
            ],
            "tel": "03-1234-5678",
            "email": "billing@example.com",
            "registration_no": "T1234567890123",
        },
        "items": items,
        "tax_rate": 0.10,
        "total_incl_tax": subtotal + tax,
        "bank": {
            "bank_name": "サンプル銀行",
            "branch": "千代田支店",
            "account_type": "普通",
            "account_no": "1234567",
            "account_holder": "ｴｰｱｲｴｰｼﾞｪﾝﾄﾁｰﾑ(ｺﾞｳ)",
        },
        "notes": [
            "・お支払いは発行日より30日以内に上記口座へお振込ください。",
            "・振込手数料は貴社にてご負担をお願いいたします。",
            "・ご不明点は billing@example.com までご連絡ください。",
        ],
    }


def main() -> int:
    register_fonts()

    if len(sys.argv) >= 2:
        out_path = Path(sys.argv[1])
    else:
        repo_root = Path(__file__).resolve().parents[3]
        out_dir = repo_root / "CFO" / "outputs"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{date.today().isoformat()}_dummy_invoice.pdf"

    data = build_dummy_data()
    c = canvas.Canvas(str(out_path), pagesize=A4)
    c.setTitle(f"請求書 {data['invoice_no']}")
    draw_invoice(c, data)
    c.showPage()
    c.save()

    print(f"Generated: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
