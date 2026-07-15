# 世界向け「売れるスキーム」— Toyama Guide 収益マシン（実行キット）

- **作成**: 2026-07-07 ／ owner「世界に向けて／すぐ実行／売れるスキームつくること」
- **中核商品**: 電子書籍『Toyama: Japan's Uncrowded Coast』(英語・約18,400語・原稿完成 `Toyama_Uncrowded_Coast_manuscript.md`)
- **原則**: ¥0（成果報酬/無料出品のみ）・広告費なし・**プラットフォーム側が買い手を連れてくるチャネルに集中**。

---

## 0. スキーム全体（1枚）

```
 Pinterest(旅行の最強流入・無料)   Google/Bing(SEO・IndexNow済)   Amazon検索(購買客)
        │                              │                            │
        └───────────┬──────────────────┘                            │
                    ▼                                                ▼
        英語49ページ(GitHub Pages・世界公開済)  ←── 各ページに2つの出口 ──→  Kindle電子書籍 $5.99
                    │                                                (KDP Select=KU読了ページでも課金)
        ┌───────────┴───────────┐
        ▼                       ▼
  アフィリ予約(成果報酬)      「Get the full guide」→Kindle/Gumroad
  Booking/Agoda/eSIM/Amazon
```

**要点**：既存の英語ページを"入口"にして、**2つの現金化出口（アフィリ予約 ＋ 電子書籍購入）**を全ページに付ける。流入はPinterest（無料・evergreen）とSEO（自動）で積む。=**観客を自前で育てず、プラットフォームから借りる。**

## 1. 市場リサーチ（実データ・2026-07 WebSearch）→ 戦略根拠

- **訪日は2026年に3,900万人超の見込み・国策で「ゴールデンルートの外」＝地方へ誘導**。宣材が名指しするのは「金沢(日本海側)」「日本アルプスの山あいの町」＝**富山はまさにその中間**。当社ニッチが市場の追い風の中心。（出典1,2）
- **客層**：韓国が最大(+22%・117万人)、次いで台湾・米・欧・豪。中国は半減。→ **英語＋韓国語**が主戦場（中国語より優先）。
- **KDP経済圏**：$2.99–9.99で**ロイヤリティ70%**、$6前後が最適。広告なしの現実は月$100〜1,000帯（10〜20冊＋キーワード/カテゴリ最適化）。**KU（Kindle Unlimited）は読了ページ数でも課金**＝売れる前に初¥が出やすい。→ **1冊で終わらせず、富山→北陸/アルプスへ"シリーズ化"**が勝ち筋。（出典3,4）
- **含意**：①英語ページのアフィリは「宿予約（訪日客が実際に泊まる）」が本命 ②電子書籍は"観客を借りる"最短の資産型 ③韓国語版は次の一手（最大成長市場・競合薄）。

## 2. Amazon KDP リスティングキット（そのまま登録）

- **Title**: `Toyama: Japan's Uncrowded Coast`
- **Subtitle**: `A Local's Guide to Takaoka, Himi & the Sea-of-Japan Side of the Alps (Beyond Tokyo & Kyoto)`
- **Author**: （ownerのペンネーム or "Tetsu, a Toyama local"）
- **Price**: $5.99（JP¥800）／70%ロイヤリティ帯・KDP Select 登録（KU課金＋無料キャンペーン可）
- **7 Keywords（検索最適化）**:
  1. off the beaten path Japan
  2. Japan travel guide 2026
  3. Japan Alps Kurobe Tateyama
  4. Sea of Japan coast Toyama
  5. Japan second trip beyond Tokyo Kyoto
  6. Kanazawa Hokuriku day trip
  7. uncrowded Japan itinerary
- **Categories（2つ）**: Travel › Asia › Japan ／ Travel › Reference & Tips
- **Description（HTML可・そのまま貼る）**:
  > You've done Tokyo. You've done Kyoto. Now go where the Japanese coast is still quiet.
  > Written by a resident of Takaoka, this is an honest, fact-checked guide to Toyama — the Sea-of-Japan side of the Japan Alps, 30 minutes from Kanazawa and a bullet-train hop from Tokyo. Fresh seafood, real scenery, and streets without crowds.
  > Inside: how to get there and around · when to go, season by season · Toyama City, Takaoka, Himi & the coast · the Alps, gorges and falls · the food of the bay (crab, white shrimp, firefly squid, Toyama Black, sake) · where to stay, money, SIM, budget, with kids · and ready-made 2–3 day itineraries.
  > No filler, no hype — just what a local would actually tell you. Perfect for a second trip to Japan, or anyone who wants the country at a quieter altitude.
- **表紙**：実写（雨晴海岸×立山連峰 or 富山ガラス）＝A2/A3順守・¥0。ownerの写真 or Wikimedia/Pexels。code が表紙の文字レイアウト案を別途提供。

## 3. Gumroad（世界・カード決済・訪日客が"買える場所"）

- noteは日本語圏＝英語の訪日客は買えない。Gumroadで**同じ原稿をPDFで$5**、加えて**『Toyama 2–3 Day Itinerary (printable PDF + Google Map links)』$3**（en-itinerary/days-2-3 から抽出・軽量tripwire）。
- 商品ページ文はKDP Descriptionを流用。Pinterest/英語ページから直リンク。

## 4. 英語ページの2出口を配線（code作成→worker設置）

- **出口A=アフィリ予約**：`affiliates.js` の LINKS に Travelpayouts(Booking/Agoda/eSIM) を投入（開栓はworker自動化済）。食記事には **Amazon Associates**（昆布/干物/地酒/ガラス＝"buy Toyama on Amazon"）。
- **出口B=電子書籍CTA**：各英語ページ末尾に一文
  > *Want the whole thing offline? **Toyama: Japan's Uncrowded Coast** — the complete local guide on Kindle. [→ get it]*
  （KDPのURL確定後にworkerが差し込み。信頼ページ en-is-toyama-safe は広告なし方針のまま除外）

## 5. Pinterest 流入エンジン（無料・evergreen・旅行の最強ジャンル）

- 各英語ページ×3〜5枚の実写ピン→ボード「Japan off the beaten path」「Toyama travel」「Japan Alps」。
- 説明文テンプレ（code提供・`EN/outputs/pinterest/`）＋リンク先=該当英語ページ（=2出口へ）。
- 週次でN枚投下（workerテンプレ実行）。1年後も流入するストック資産。

## 6. 実行チェックリスト（順序・担当）

| # | アクション | 担当 | 状態 |
|---|---|---|---|
| 1 | Kindle原稿を最終整形（空見出し除去・章扉） | code | 原稿生成済→微修正 |
| 2 | 表紙レイアウト案（実写＋タイトル） | code案→owner/worker画像 | 未 |
| 3 | KDP登録→本アップロード→$5.99/KDP Select | owner+worker | 未（キット完備） |
| 4 | Gumroadに本PDF$5＋行程PDF$3出品 | owner+worker | 未 |
| 5 | Amazon Associates登録→食記事にリンク | owner+worker→code配線 | 未 |
| 6 | Travelpayouts開栓→LINKS投入 | worker自動 | 配線済・登録待ち |
| 7 | 英語ページに電子書籍CTA差し込み | code原稿→worker | URL待ち |
| 8 | Pinterestピン投下開始 | code文→worker | 未 |
| 9 | 韓国語版ガイド（最大成長市場・次の一手） | code | 次フェーズ |

## 7. 判定（2週B/W・週次レビュー）

| 出口 | 指標 | 合格 | 期限 |
|---|---|---|---|
| KDP | 初DL/KU読了 | 1件 | 出品+30日 |
| Gumroad | 初販売 | 1件 | 出品+30日 |
| アフィリ | 初クリック→初予約 | クリック→成果 | 開栓+30/90日 |
| Pinterest | 英語ページ流入 | 月100 | 開始+30日 |

出た出口に全振り（昇格=月¥10,000・10月末）。

### 出典（2026-07 WebSearch）
1. Travel And Tour World — Japan travel trends 2026 (beyond the Golden Route)
2. The Traveler — Japan's 2026 tourism boom (39M+, Korea #1, China −50%)
3. SellerMetrics / Zonguru — KDP earnings 2026（70%帯・現実分布・KU）
4. Kindlepreneur — KDP keyword/category 最適化
