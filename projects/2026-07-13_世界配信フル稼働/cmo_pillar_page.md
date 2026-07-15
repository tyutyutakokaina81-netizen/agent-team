# CMO作業ログ — 英語ピラー(ハブ)ページ

日付: 2026-07-14 / 担当: CMO / North Star: 高岡・氷見・富山を海外読者に

## 目的
新規量産ではなく、既存の約97本のenページを1枚で束ね、検索評価と回遊を上げる「Start Here / 完全ガイド入口」を作る。

## 作成・変更ファイル
- 新規: `apps/toyama-guide/en-start-here.html`（en-access.html の構造をクローン。head/canonical/og/ld+json/analytics.js include・.lang/.tag/.muted/.pr/.aff クラス・note CTA形式を踏襲）
- 変更: `apps/toyama-guide/en.html`（ヒーロー直下に導線1行のみ追加。既存レイアウト非破壊）
  - 追加文言: `New here? → Start with our complete first-timer's guide (en-start-here.html)`

## canonical / og:url
`https://tyutyutakokaina81-netizen.github.io/agent-team/toyama/en-start-here.html`

## ピラーが束ねた既存enページ（内部リンク・全て実在確認済 27本）
1. en-worth-visiting.html
2. en-off-beaten-path.html
3. en-from-tokyo.html
4. en-from-kansai.html
5. en-access.html
6. en-how-many-days.html
7. en-itinerary.html
8. en-days-2-3.html
9. en-toyama-city.html
10. en-where-to-stay.html
11. en-food.html
12. en-shiroebi.html
13. en-buri-yellowtail.html
14. en-crab.html
15. en-manga-pilgrimage.html
16. en-doraemon.html
17. en-hattori.html
18. en-alpine.html
19. en-kurobe-gorge.html
20. en-amaharashi.html
21. en-gokayama.html
22. en-takaoka.html
23. en-himi.html
24. en-when-to-go.html
25. en-money.html
26. en-sim-wifi.html
27. en-faq.html
（+ 末尾ナビ/CTAで en.html ハブへ戻す）

## 構成（初訪問者が迷わない順）
where/why → getting here → how many days → where to stay → food → manga towns → mountains&coast → two towns → practical → in short

## 制約遵守
- ¥0（コード変更のみ）
- A4: 町名/番地なし・市レベルまで（Takaoka/Himi/Toyama City止まり）
- A5: 「世界一」等の断定・誇張なし。住人トーン・盛らない。一次観察（高岡在住視点）を明記
- 著作権: 藤子作品画像は貼らず、テキストで史実（作者出身地）のみ言及
- リンク切れ: 27本すべて `os.path.exists` で実在確認済

## 検証
- python3でタグ対応チェック（html/head/body/table/tr）→ 不整合なし
- 内部enリンクの実在チェック → MISSINGなし
- 本文語数 ≈ 950語（800〜1200レンジ内）

## sitemap
指示どおり未編集（code側が追加）。commitもcode側でまとめて実施。
