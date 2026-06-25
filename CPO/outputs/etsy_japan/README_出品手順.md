# Etsy 日本旅行プリンタブル 10商品 — 出品手順（owner用）

code が**中身（印刷原稿）＋Etsy出品キット（タイトル/タグ/価格/説明文）**を10商品ぶん用意しました。
あなたの作業は「**PDF化 → Etsyにアップ**」だけです。各商品ファイルにそのまま使える出品情報が入っています。

## 商品ラインナップ
| # | ファイル | 商品 | 推奨価格 |
|---|---|---|---|
| 01 | 01_japan-trip-planner.md | Japan Trip Planner（主力・30p） | $7.9〜12.9 |
| 02 | 02_tokyo-itinerary-planner.md | Tokyo 5-Day Itinerary | $5〜9 |
| 03 | 03_kyoto-osaka-itinerary-planner.md | Kyoto & Osaka Itinerary | $5〜9 |
| 04 | 04_hidden-japan-hokuriku-planner.md | Hidden Japan: Hokuriku & Toyama（差別化） | $5〜9 |
| 05 | 05_japan-packing-checklist.md | Japan Packing Checklist | $3〜5 |
| 06 | 06_japan-budget-tracker.md | Japan Budget Tracker | $3〜5 |
| 07 | 07_japan-phrases-cheat-sheet.md | Japan Phrases Cheat Sheet | $3〜5 |
| 08 | 08_japan-food-bucket-list.md | Japan Food Bucket List | $3〜5 |
| 09 | 09_japan-blank-itinerary-template.md | Japan Itinerary Template（白紙汎用） | $3〜5 |
| 10 | 10_japan-first-timer-survival-guide.md | Japan First-Timer's Survival Guide | $4〜7 |

## ★ 完成品は生成済み（Canva不要・アップするだけ）
- **PDF商品本体**：`pdf/01〜10_*.pdf`（実際に売るDLファイル・印刷可）
- **表紙画像（サムネ）**：`covers/01〜10_*.png`（Etsy出品の1枚目）
- ※ code が reportlab/PIL で生成済み（A2準拠＝AI写真でなく確定レンダリング）。再生成は `python3 tools/make_etsy_products.py`。

## 出品の流れ（1商品あたり約5分）
1. **Etsyに出品**：Etsyショップ →「新しい商品」→ **デジタル商品**。
2. タイトル・タグ(13個)・説明文・価格は、商品ファイル(`NN_*.md`)の「Etsy Listing Kit」を**コピペ**。
3. **`pdf/NN_*.pdf` をアップロード**（販売ファイル）、**`covers/NN_*.png` を1枚目の画像に**。
4. 公開。慣れたら 1日1〜2本ずつ、まず10本そろえる（点数が増えるほど検索に乗りやすい）。

> もっと見栄えを良くしたい場合だけ Canva で表紙を作り直してOK（必須ではない・今の表紙でそのまま出せる）。

## コツ（リサーチ準拠）
- **最初は intro 価格（安め）**でレビューを集めると伸びやすい。
- タイトル・タグの英語キーワードはそのまま使う（検索流入の要）。
- 主力＝01（バンドル）と差別化＝04（Hidden Japan）を軸に、05〜09の小物で点数を稼ぐ。

## 正直な注意
- 売上はEtsyの管理画面でしか見えません（code は A1 で見えない）。**売れたら数字をここに貼ってください** → 「売れたものを増やす」具体策を出します（＝あなたの方針『売れてから提案』）。
- デザイン/サムネ作成と Etsy アップロードは owner 作業（私は外部不可）。中身は全部用意済み。
