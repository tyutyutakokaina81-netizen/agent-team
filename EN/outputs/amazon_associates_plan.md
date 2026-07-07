# Amazon Associates 収益化 配線計画（英語・食/工芸ページ）

- 作成: 2026-07-07 / 担当: CDO（技術）
- 目的: 英語ページ（食・工芸）に「Amazonで買える富山土産」商品ブロックを冪等に配線し、成果報酬(¥0初期費用)で収益化する
- 前提制約: **A4=具体的な地区名/町名/住所は書かない（市レベルまで）**・**A5=誇張/断定/テンプレ乱用しない**・**A7=commitしないと消える**
- 位置づけ: 既存の `apps/toyama-guide/affiliates.js`（旅行系＝宿/ツアー/鉄道/eSIM）の**姉妹スクリプト**。旅行系は「体験を売る」、本計画は「持ち帰れる物産を売る」。役割が違うので併存させる。
- 本ドキュメントは**計画とテキストのみ**。実装（`amazon.js` 生成・各HTMLへの1行追加）は後で code が行う。

---

## 0. 設計原則（affiliates.js の作法に合わせる）

`affiliates.js` の良い点をそのまま踏襲する:

1. **リンクが入っている時だけ表示・空なら何も出ない（冪等・無害）** — owner がリンク未登録でもページは壊れない。
2. **ページのファイル名で「意図」を判定** — 関係ない商品を出さない（=A5 スパム回避）。
3. **owner の負担は「登録＋リンクを渡す」だけ** — 商品URLは1箇所（`PRODUCTS` オブジェクト）に集約。code が受け取って貼る。
4. `rel="sponsored nofollow noopener"`・`target="_blank"`・**PR表記必須**。

> owner がやるのは2つだけ:
> (a) Amazonアソシエイト・プログラムに登録（無料・審査あり）。
> (b) 富山物産の商品ページで「テキストリンク」を発行し、そのURLを code に渡す（or `PRODUCTS` の "" に貼る）。
> → 貼った商品カテゴリだけ全対応ページで一斉に有効化される。

---

## 1. 対応表（どのページに・どのAmazon商品カテゴリを付けるか）

商品カテゴリは「Amazonで実際に買える・常温で国際/国内発送しやすい富山物産」を基準に選定。生鮮（活カニ・生シロエビ等）は配送困難なので**加工品/常温品に寄せる**。

| 商品カテゴリ (key) | 内容（Amazonで買える形） | 主な対応ページ | 補足 |
|---|---|---|---|
| `kombu` | とろろ昆布・おぼろ昆布・だし昆布 | `en-onigiri-kelp` / `en-food` | 昆布文化の記事と直結。常温・軽量で最も相性が良い |
| `shrimp_snack` | 白えびせんべい・白えび素干し | `en-shiroebi` / `en-food` | 生シロエビは不可→煎餅/素干しの土産形で |
| `ramen` | 富山ブラック 即席/生麺パック | `en-toyama-black` / `en-food` | 常温インスタントが土産定番。相性◎ |
| `squid_snack` | ホタルイカ 素干し/沖漬け風おつまみ（常温） | `en-firefly-squid` / `en-food` | 生/観賞は現地体験、持ち帰りは乾き物で |
| `masuzushi_kit` | ますずし関連（押し寿司型・保存版セット等） | `en-masuzushi` | 生鮮ますずし本体は輸送難→型/キット/日持ち版に限定。**要注意扱い(§5)** |
| `crab_preserved` | 紅ズワイ缶詰・ほぐし身等の常温加工 | `en-crab` | 活/冷凍は不可→缶詰/加工のみ。無ければ非表示 |
| `sake_ware` | 酒器（ぐい呑み・徳利）・地酒ガイド本 | `en-sake` | **酒類本体はAmazon物販/配送規制が厳しい**→酒器・書籍に寄せる(§5) |
| `glassware` | ガラス工芸品・ガラスの酒器/小物 | `en-glass-art` / `en-sake` | 富山ガラス文脈。工芸→酒器で `sake_ware` と自然につながる |
| `assortment` | 富山物産の詰め合わせ/ギフトセット | `en-food` | 総合フードガイドの「まとめ買い」導線 |

### ページ別の表示カテゴリ（INTENT 相当・ファイル名判定）

| ページ | 表示するカテゴリ（順序=優先度） |
|---|---|
| `en-onigiri-kelp` | `kombu`, `assortment` |
| `en-food` | `assortment`, `kombu`, `ramen`, `shrimp_snack` |
| `en-shiroebi` | `shrimp_snack`, `kombu` |
| `en-firefly-squid` | `squid_snack`, `assortment` |
| `en-masuzushi` | `masuzushi_kit`, `assortment` |
| `en-toyama-black` | `ramen`, `assortment` |
| `en-crab` | `crab_preserved`, `assortment` |
| `en-sake` | `sake_ware`, `glassware` |
| `en-glass-art` | `glassware`, `sake_ware` |

> 1ページの物販ボタンは**最大2〜3個まで**（A5=スパム回避）。旅行系(affiliates.js)ボタンと合算しても過剰にならないよう、食ページの物販は「昆布/その物の主役1つ＋詰め合わせ1つ」を基本形にする。
> 干物(himono)・かまぼこ等は現状**英語ページが未整備**。将来 `en-himono` / `en-kamaboko` 等を作った時に `himono`・`kamaboko` カテゴリを追加する余地を残す（この計画の対応表に追記するだけで拡張可能）。

---

## 2. 実装方針（後で code が作る `amazon.js` の設計仕様）

`affiliates.js` と同じ構造の**独立スクリプト** `apps/toyama-guide/amazon.js` を作る。各食/工芸HTMLの末尾（既存の `affiliates.js` の1行の**直後**）に:

```html
<script defer src="/agent-team/toyama/amazon.js"></script>
```

を1行足すだけ。スクリプトの論理仕様（擬似・実装は後日）:

1. `PRODUCTS = { kombu:"", shrimp_snack:"", ramen:"", squid_snack:"", masuzushi_kit:"", crab_preserved:"", sake_ware:"", glassware:"", assortment:"" }`
   - **すべて空文字で出荷**。owner がURLを入れたキーだけ後述のボタンが出る。
2. `META` に各カテゴリの emoji・英語ラベル・中立紹介文（§3）を持つ。
3. `INTENT`（§1のページ別表）で `location.pathname` から表示カテゴリを決定。
4. `PRODUCTS[key]` が**空なら push しない**。有効なボタンが0個なら**セクション自体を描画しない**（=無害・冪等、affiliates.js の `if (!btns.length) return;` と同じ）。
5. セクションは既存 `.aff` / `.pr` / `.muted` のスタイルを流用（新規CSS不要）。見出しは `"Bring a taste of Toyama home"` 等、旅行ブロック（"Plan your Toyama trip"）と区別。
6. 各リンク: `a.rel = "sponsored nofollow noopener"; a.target = "_blank";`。
7. ブロック冒頭に**PR表記**（§4）、末尾に**免責**（§4）を必ず入れる。
8. 挿入位置: 既存の物販/関連リンク直前（`affiliates.js` と同様に最後の `p.tag` の前）。旅行ブロックと物販ブロックが**二重PR表記**にならないよう、物販ブロックは自前のPR/免責を1つずつ持つ。

**owner の負担 = ゼロコーディング**: 「Amazonアソシエイト登録」→「商品テキストリンクを発行」→「URLを code に渡す（またはPRODUCTSに貼る）」の3操作のみ。技術作業は一切不要。

---

## 3. 各ページ紹介文の下書き（英語・2〜3文・中立・A5厳守）

いずれも「断定・誇張・世界唯一」を避け、事実ベース＋やわらかい案内に留める。ボタンラベルは短く、本文は補足として `META` の説明に入れる。

**kombu（→ en-onigiri-kelp / en-food）**
> Toyama has a long kelp habit, and shaved kelp (tororo kombu) keeps well, so it's an easy thing to take home. A bag lets you try the kelp-wrapped rice ball or a quick kelp soup in your own kitchen.
> Button: `🍙 Tororo kombu (shaved kelp) on Amazon →`

**shrimp_snack（→ en-shiroebi / en-food）**
> Fresh white shrimp is hard to ship, but dried white shrimp and shrimp crackers travel well and keep the same gentle sweetness. They make a simple, shelf-stable way to taste this Toyama Bay specialty at home.
> Button: `🦐 White shrimp crackers & dried shrimp →`

**ramen（→ en-toyama-black / en-food）**
> Toyama black ramen has a dark, soy-forward broth, and instant and fresh-noodle packs are widely sold. They're a low-effort way to get close to the local bowl, though a shop version is still the real thing.
> Button: `🍜 Toyama black ramen (instant packs) →`

**squid_snack（→ en-firefly-squid / en-food）**
> Seeing firefly squid glow is a spring experience you have to come for, but dried and simmered versions are sold year-round as a snack. They pair naturally with sake and keep at room temperature.
> Button: `🦑 Firefly squid snacks (dried) →`

**masuzushi_kit（→ en-masuzushi）**
> Fresh masuzushi is best eaten locally, but pressing molds and shelf-stable kits let you try the trout pressed-sushi idea at home. Treat it as a fun approximation rather than the station-bought original.
> Button: `🍱 Pressed-sushi mold & kits →`

**crab_preserved（→ en-crab）**
> Live crab is a winter, eat-it-here treat, but canned and pre-picked red snow crab is available all year. It's a convenient way to add a little of the flavor to a meal at home.
> Button: `🦀 Canned / picked snow crab →`

**sake_ware（→ en-sake / en-glass-art）**
> Shipping sake abroad is often restricted, so a nice cup travels better than the bottle. A local-style sake cup, or a small guidebook, is an easy way to bring the drinking culture home.
> Button: `🍶 Sake cups & guides →`

**glassware（→ en-glass-art / en-sake）**
> Toyama has built a modern glass-craft scene, and small glass pieces — including sake cups — are sold as everyday objects. A single cup is a light, practical souvenir of that craft.
> Button: `🥃 Toyama-style glassware →`

**assortment（→ en-food）**
> If you'd rather sample a few things at once, Toyama food gift sets bundle items like kelp, crackers and local snacks. It's a simple way to try several regional flavors in one order.
> Button: `🎁 Toyama food gift sets →`

---

## 4. PR表記 / 免責の文面（英語・既存 .pr / .muted に流用）

**PR表記（物販ブロック冒頭・`.pr` スタイル）**
> As an Amazon Associate, this page earns from qualifying purchases. The links below are advertising (affiliate links); they don't change the price you pay.

**免責（物販ブロック末尾・`.muted` スタイル）**
> Availability, prices and sellers on Amazon change often — please check each product page for current details. These are suggestions, not endorsements of any specific seller, and nothing here is a private address or a guarantee of any outcome.

> 注: 既存の旅行ブロック（affiliates.js）にも同種のPR/免責がある。物販ブロックは**自分専用のPR/免責**を持ち、両ブロックが同一ページに出ても各々が独立して開示を満たす形にする（Amazonの開示規約は「明確・近接」を要求）。

---

## 5. リスク注記（運用上の注意）

1. **Amazonアソシエイトの「180日ルール」**: 登録後**180日以内に最低1件の適格販売**が発生しないとアカウントが解約される。英語ページのトラフィックが立ち上がる前に登録すると空振りで失効しうる。→ **アクセスが出てきてから登録**、または登録直後に owner 自身/身内以外の実売を1件確保する運用が安全。**自己購入は成果対象外**なので失効回避にならない点に注意。
2. **地域ストア(locale)の分裂**: 読者は米国(amazon.com)・英国(.co.uk)等バラバラ。日本のアソシエイト(amazon.co.jp)リンクは海外読者が買いにくい。→ 当面は **amazon.co.jp** で富山物産を確実に用意しつつ、将来 OneLink 的な地域振り分けを検討（初期は無理に多国対応しない）。
3. **酒類・生鮮の制約**: 日本酒本体・活カニ・生シロエビ等は Amazon 物販/国際配送で扱いにくい/規制対象。→ 本計画は**常温加工品・酒器・書籍・詰め合わせ**に寄せてリスク回避済み（§1）。生鮮を貼らない。
4. **在庫消滅リンク**: 個別商品は廃番になりやすい。→ 可能なら「検索結果/カテゴリ」寄りのリンク、または owner が定期的にリンク死活を確認。空にすれば §2 の冪等設計で**自動的に非表示**になり、リンク切れが表に出ない。
5. **開示義務(A5と両立)**: Amazonアソシエイト運営規約は「Associateである旨の明示」を必須とする。§4のPR表記を必ず残す。誇張表現（"best"/"world-famous"）は規約違反かつA5違反なので使わない。
6. **併存の過剰化**: 旅行系(affiliates.js)＋物販(amazon.js)＋既設じゃらんリンクが同一ページに集中しすぎるとA5(スパム感)に触れる。→ 食ページの物販は**最大2〜3ボタン**、1ページ全体でリンクブロックが過密にならないよう code がレビューして調整。
7. **税/送金**: Amazonアソシエイトの報酬受取・税務情報の登録は owner 側。code/技術側は関与しない（CFO領域）。

---

## 6. 次アクション（owner向け・要点）

1. Amazonアソシエイト（まず amazon.co.jp）に登録（無料・審査あり）。§5-1の180日ルールを踏まえ、英語ページのアクセスが立ち上がってからが安全。
2. §1の商品カテゴリごとに、富山物産の商品/カテゴリ「テキストリンク」を発行し、code に渡す（or `PRODUCTS` に貼る）。
3. code が `amazon.js` を実装し、§1対応ページの末尾に1行追加してコミット。owner はコーディング不要。
