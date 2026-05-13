# 請求書PDFジェネレーター

事業柱A（SEO記事制作代行）想定の請求書PDFを生成するツール。
日本語表示には reportlab 内蔵の CID フォント（HeiseiKakuGo-W5 / HeiseiMin-W3）を使用するため、追加フォント不要。

## 依存

- Python 3.9+
- reportlab（`pip install reportlab`）

## 使い方

```bash
# デフォルト出力先（CFO/outputs/<YYYY-MM-DD>_dummy_invoice.pdf）
python3 CDO/outputs/2026-05-13_invoice_generator/generate_invoice.py

# 出力先を指定
python3 CDO/outputs/2026-05-13_invoice_generator/generate_invoice.py /tmp/invoice.pdf
```

## 出力内容

| 項目 | 値 |
|------|---|
| 請求書番号 | INV-2026-0513-001 |
| 発行日 | 2026年05月13日 |
| 支払期日 | 2026年06月12日（発行日 +30日） |
| 宛先 | 株式会社サンプルコーポレーション |
| 発行元 | AIエージェントチーム合同会社（架空） |
| 明細 | SEO記事制作 ×3行 |
| 合計（税込） | ¥249,000（税抜 ¥226,000 + 税 ¥22,600 → 切り捨て後 ¥22,600） |
| 振込先 | サンプル銀行 千代田支店（架空） |

すべての値は**架空のダミーデータ**。実請求時は `build_dummy_data()` を編集するか、
将来的に外部 JSON/CLI 引数から読み込むように拡張する。

## 注意

- 実生成された PDF は `.gitignore` により Git にコミットされない（`CFO/outputs/*` 除外）
- 実顧客向けの請求書を本ツールで生成した場合は、当然 Git にコミットしないこと
- フッターに「本書類はサンプル（ダミー）として生成されました。」と明記される

## 拡張ポイント

- 顧客データの外部化（JSON / YAML 入力）
- 複数明細パターン（事業柱A/B/C）テンプレート切替
- 通し番号の自動採番（管理台帳との連携）
- 押印画像の貼り付け（角印PNG）
