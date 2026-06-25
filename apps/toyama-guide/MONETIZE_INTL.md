# 海外向け収益化（国際アフィリ）— 全役員会 2026-06-25 結論＋実装

## 役員会の合意（CAO/CMO/CFO/CPO/CSO/CDO）
- **最大の弱点**：英語ページの予約導線が「じゃらん(日本語)」だけ＝海外客は成約しにくい（=取りこぼし）。
- **最優先策**：海外読者が母国語・自国通貨で予約できる**国際アフィリ**を文脈別に併設。
  - **Travelpayouts 1社登録**で Booking.com(宿)・Klook/GetYourGuide(ツアー)・12Go(鉄道)・Airalo(eSIM) をまとめてカバー（英語・海外送金OK・owner登録は1回）。
- **配置方針(A5)**：1ページ1-2枠・**ページ意図に一致する売り物だけ**（スパム化＝信頼/検索評価の毀損を回避）。
- **副収入**：①旅程PDF(¥500-800/Gumroad・CPO) ②問い合わせ導線→高単価相談(CSO)。当面は無料記事の回遊を死守。
- **正直な律速(CFO/CAO)**：収益＝トラフィック×成約×単価。今はトラフィックほぼ0＝当面の実収入は小。ただし旅行は単価が高く、少数の読者でも当たれば大きい。Travelpayoutsは最低支払額(約$50)・審査あり。

## 実装（code・完了・owner操作ゼロ）
- `apps/toyama-guide/affiliates.js`：ページのファイル名から「意図」を判定し、合う海外ボタンだけ自動表示。
  - 意図マップ：access/vs-kanazawa→鉄道・eSIM・宿／itinerary・季節→宿・ツアー・鉄道／alpine・gokayama・kurobe等→ツアー・宿／onsen・himi・takaoka等→宿・ツアー／食ほか→宿のみ。
  - **`LINKS` が空ならボタンを一切表示しない**（冪等・無害）。既存のじゃらん/楽天リンクは不変（併用）。
- 全英語ページ(35)に `<script ... toyama/affiliates.js>` を注入、`pages.yml` で配信。

## owner の唯一のアクション（収益オン）
1. **Travelpayouts に登録**（無料）。
2. Booking/ツアー/鉄道/eSIM の自分のリンクを `affiliates.js` の `LINKS` に貼る（or code に渡す）。
→ 全英語ページの「Plan your Toyama trip」ボタンが一斉に有効化。
