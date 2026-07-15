# CAO 分析：英語SEOの欠落トピック＆検索クエリ調査

- 作成：2026-07-14 / CAO
- North Star：高岡・氷見・富山を海外個人旅行者に読ませる（`AGENTS.md` §0）
- 対象チャネル：GitHub Pages 英語ガイド `apps/toyama-guide/en-*.html`（97ページ・LIVE）
- 手法：既存97ファイルの**ファイル名照合** ＋ WebSearch（¥0・実測）。制約 A4（地区名PII禁止）/ A5（誇張禁止・断定回避）。
- **読み取り専用。HTMLは編集していない。**

---

## 0. 前提と精度の限界（自責・不都合な事実）

- 既存ページの「対応済み判定は**ファイル名のみ**」で行った。中身までは読んでいない → 「既存で対応済み」判定は解像度が粗い。本文レベルの過不足は `[要確認]` を付す。
- 検索需要は WebSearch のヒット密度・上位ドメインの厚み・関連クエリ数からの**体感**であり、実測ボリューム（月間検索数）ではない。すべて `[体感/要確認]`。
- したがって本レポートは「仮説の優先順位」であり、確定計画ではない。確定前に(1)対象HTML本文の実読、(2)Search Console等での実クエリ照合、が必要。

---

## 1. 既存97ページのカバレッジ地図（重複回避の土台）

| 領域 | 既存ファイル（抜粋） | 判定 |
|---|---|---|
| アクセス/交通 | access, airport, from-tokyo, from-kansai, getting-around, car-rental, bike-rental, rail-pass, tram-day-pass, luggage-lockers | 厚い |
| 立山黒部/山岳 | alpine, alpine-cost, murodo, mikurigaike, tateyama-snow-wall, tateyama-worth-it, kurobe-gorge, kurobe-vs-tateyama, kurobe-worth-it, unazuki-onsen, shomyo-falls | 厚いが**黒部ダム単独が無い** |
| 食 | food, crab, buri-yellowtail, firefly-squid, shiroebi, genge, masuzushi, seafood-bowl, toyama-bay-sushi, himi-udon, toyama-black, onigiri-kelp, kamaboko, sake, wagashi, halal, vegetarian ほか | 非常に厚い |
| 比較 | vs-kanazawa, vs-takayama, takaoka-vs-toyama, himi-vs-toyama-seafood, gokayama-vs-shirakawa, kurobe-vs-tateyama | 厚い |
| アニメ/聖地 | doraemon, manga-pilgrimage | 中 |
| 行程/計画 | itinerary, how-many-days, days-2-3, daytrip, golden-route-detour, off-beaten-path, worth-visiting, when-to-go | 中〜厚 |
| 季節 | spring, summer, autumn, winter, cherry-blossoms, tulips | 厚い |
| 実務 | sim-wifi, cards-cash, money, budget, is-toyama-safe, what-to-wear, accessibility, with-kids, rainy-day, faq, at-night, where-to-stay, photo-spots | 厚い |
| 工芸/文化 | copperware, glass-art, inami-woodcarving, medicine-history, zuiryuji, takaoka-daibutsu, souvenirs | 中 |
| 世界遺産/村 | gokayama, shirakawa-go, gokayama-lightup, johana, yatsuo-owara | 中（**宿泊体験・行き方が薄い**） |

→ 食・季節・実務・比較は飽和。**穴は「特定の高需要スポット単独ページ」「予約/行き方の実務how-to」「立山黒部の予約・開通時期・1日縦断ロジ」**に集中している。

---

## 2. (A) 本当に欠けている新規ページ候補 10件（優先順）

判定軸：①需要`[体感]` ②既存ファイルに無い（照合済） ③当社が勝てる＝**高岡・氷見・富山 住人の一次情報**。

| # | ページ案（想定ファイル名） | 想定クエリ | 需要`[体感]` | なぜ勝てるか（1行） |
|---|---|---|---|---|
| 1 | 黒部ダム（`en-kurobe-dam`） | "Kurobe Dam", "Kurobe Dam water discharge", "how to visit Kurobe Dam from Toyama" | 高 | 既存は"gorge/worth-it/vs"のみで**ダム単独が無い**。観光放水6/26–10/15・220段の実務を富山側発の実体験で書ける `[要確認:日付]` |
| 2 | 合掌造りに泊まる（`en-gassho-stay`） | "gassho house stay overnight", "Gokayama farmhouse stay", "minshuku Gokayama booking" | 高 | 宿泊単独ページが無い。囲炉裏・こきりこ・観光客が引いた後の静けさを一次記述（村レベル表記でA4順守） |
| 3 | 高岡/富山から白川郷・五箇山への行き方（`en-to-shirakawago-bus`） | "Shirakawa-go from Takaoka", "World Heritage Bus timetable", "Toyama to Shirakawa-go bus" | 高 | 一般記事は金沢/高山発が主。**高岡発（世界遺産バス）**は当社の地元優位。券種6種の実務 `[要確認:料金]` |
| 4 | 北陸アーチパス徹底解説（`en-hokuriku-arch-pass`） | "Hokuriku Arch Pass worth it", "does Hokuriku Arch Pass cover Alpine Route" | 高 | 既存 rail-pass はあるが個別ページ無し。「パスは登山口までで**立山黒部は非対象**」という頻出誤解を住人視点で解消 |
| 5 | 立山黒部アルペンルート2026 開通時期カレンダー（`en-alpine-season`） | "when does Alpine Route open 2026", "Alpine Route opening dates", "best month snow wall" | 高 | 開通4月中旬〜11月末・雪壁の見頃窓を年次更新で押さえる高CVクエリ。既存 when-to-go は全県一般で薄い `[要確認]` |
| 6 | 金沢から高岡日帰り（`en-takaoka-from-kanazawa`） | "day trip from Kanazawa to Takaoka", "Kanazawa to Takaoka" | 中〜高 | 既存 daytrip は富山発。**金沢滞在者（母数大）を逆流入**。40分・国宝2件・地元半日プラン |
| 7 | アルペンルート1日縦断ロジ（`en-alpine-one-day`） | "cross Alpine Route in one day", "Alpine Route order of transport", "luggage Alpine Route" | 中〜高 | 既存 alpine は概説。乗継順・方向（東西どちら発）・荷物預けの**当日実務**は住人が最も強い |
| 8 | 富山を拠点にした中部7日ルート（`en-central-japan-route`） | "7 day itinerary Toyama Kanazawa Takayama", "Japan Alps itinerary" | 中 | 既存 golden-route-detour と補完。**富山拠点が金沢より安い**の費用論で差別化 `[要確認:料金]` |
| 9 | 万葉線（ドラえもんトラム含む）乗車ガイド（`en-manyosen-tram`） | "Manyosen tram", "Takaoka tram to Shinminato", "Doraemon tram ride" | 中 | doraemonはキャラ中心。**路線として**高岡〜新湊・海王丸まで結ぶ乗り鉄視点は未整備 |
| 10 | 富山のローカル私鉄・ICカード攻略（`en-local-trains`） | "Ainokaze Toyama Railway", "IC card Toyama non-JR", "Dentetsu Toyama" | 中 | JR外の私鉄（あいの風・地鉄・万葉線）の乗り方/IC可否は訪日者が詰まる実務。getting-aroundを実務で補完 |

**最優先＝#1 黒部ダム単独ページ**（高需要 × 既存に完全欠落 × 富山側発の実体験で勝てる）。

---

## 3. (B) 既存ページで強化すべきもの 10件

判定はファイル名照合ベース。本文の実装状況は未読 → 過不足は `[要確認]`。

| # | 既存ファイル | 狙うクエリ | 不足の疑い（要本文確認） |
|---|---|---|---|
| 1 | `en-alpine.html` | "how to book Alpine Route tickets", "Alpine Route web ticket reservation" | 事前Web予約の手順導線。検索者は明確に「予約方法」を打つが概説止まりの懸念 `[要確認]` |
| 2 | `en-alpine-cost.html` | "Alpine Route total cost", "is JR Pass valid on Alpine Route" | 「どの鉄道パスも本ルート非対象」の明記＋片道/往復割引の数値 `[要確認:料金]` |
| 3 | `en-rail-pass.html` | "Hokuriku Arch Pass", "which Japan rail pass for Toyama" | パス比較表と #4新規への内部リンク。アーチパス個別解説が薄い懸念 `[要確認]` |
| 4 | `en-vs-kanazawa.html` | "Toyama or Kanazawa where to stay/base" | 「富山＝金沢より安い拠点」費用角度＋両市20–25分の事実の前面化 `[要確認]` |
| 5 | `en-daytrip.html` | "day trip from Kanazawa" | 逆方向（金沢発で高岡/富山へ）の導線・#6への内部リンクが無い懸念 `[要確認]` |
| 6 | `en-firefly-squid.html` | "firefly squid boat tour time", "how to book Namerikawa" | 3:00am集合の実務・4〜5月ピーク・非乗船者向けミュージアム代替 `[要確認]` |
| 7 | `en-gokayama.html` | "Gokayama overnight stay", "Gokayama vs Shirakawa-go worth it" | 「泊まる」CTAと#2新規への内部リンク。日帰り前提に寄っている懸念 `[要確認]` |
| 8 | `en-kurobe-gorge.html` | "Kurobe Gorge Railway tickets", "Kurobe Gorge vs Kurobe Dam" | 検索者が峡谷とダムを混同。**ダムとの違い明記**＋#1への内部リンク `[要確認]` |
| 9 | `en-when-to-go.html` | "when does Alpine Route open", "best month Toyama" | 立山黒部の開通/雪壁カレンダーの個別コールアウト。全県一般で埋もれる懸念 `[要確認]` |
| 10 | `en-toyama-bay-sushi.html` | "where to eat sushi Toyama", "sushi reservation Toyama no Japanese" | 日本語不要予約（byFood/autoreserve等）と店選びガイド `[要確認:店名/手段]` |

---

## 4. 次アクション（数字と期限に落とす）

1. **7/16まで**：最優先 #1 黒部ダム を CMO へ発注（英語1ページ・住人一次情報・観光放水期間は `[要確認]`→出典明記）。峡谷ページ(en-kurobe-gorge)から相互リンク。
2. **7/18まで**：#2 合掌造り宿泊、#3 白川郷への行き方 を続けて発注（世界遺産クラスタで内部リンクを束ねSEO集約）。
3. **強化(B)は本文未読が前提** → CMO/CDO が対象10ファイルの本文を実読し、`[要確認]`を潰してから着手（願望実装を避ける）。
4. 効果測定：公開後、Search Console の対象クエリ表示回数/CTRで #1〜#3 の仮説を検証。上がらなければ「何が/なぜ/次どう変える」で記録。

---

## 5. 出典（WebSearch・2026-07-14）

- Toyama itinerary/things to do: japan-guide.com/e/e7500.html, visit-toyama-japan.com/en/travel-plan, barefootsurfer.com/toyama-itinerary
- 金沢→高岡日帰り: visitkanazawa.jp/en/itineraries/detail_138.html, japan-guide.com/e/e7526.html, kanazawastation.com/day-trip-from-kanazawa-to-toyama
- アルペンルート予約/雪壁: alpen-route.com/en/transport/ticket.html, jrpass.com/blog/the-kurobe-alpine-route-a-detailed-guide, snowmonkeyresorts.com/activities/the-snow-walls-of-tateyama-kurobe, japan.travel/en/spot/1419
- 拠点比較: barefootsurfer.com/toyama-vs-kanazawa, snowmonkeyresorts.com/smr/.../best-places-to-stay-in-toyama
- 世界遺産バス: japan-guide.com/bus/gokayama.html, visit-toyama-japan.com/en/travel-inspiration/World%20Heritage%20Bus
- 合掌造り宿泊: japan-guide.com/e/e5952.html, e5955.html, visit-toyama-japan.com/en/travel-inspiration/Gokayama_stay
- 北陸アーチパス: livejapan.com/.../article-a2000917, klook.com/en-US/blog/hokuriku-arch-pass-guide
- ほたるいか: visit-toyama-japan.com/en/places-to-go/50004, japan.travel/en/sports/diving/travel/hotaru-ika-firefly-squid-boat-tour
- 黒部ダム: japan.travel/en/spot/1422, japan-guide.com/e/e7554.html, jeepe.jp/en/articles/kurobedam-travel-guide-1145
- ドラえもんトラム/万葉線: visit-toyama-japan.com/en/things-to-do/21137, wattention.com/the-takaoka-doraemon-tour
- 富山の寿司: visit-toyama-japan.com/en/travel-inspiration/Sushi, toyamashi-kankoukyoukai.jp/en/sushi
