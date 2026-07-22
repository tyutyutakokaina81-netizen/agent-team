# CMO Batch2：英語Pages 高需要"欠落"3ページ新設

- 作成：2026-07-22 / CMO（code）
- 出典発注：`projects/2026-07-13_世界配信フル稼働/cao_en_seo_gap.md` §2 の #2/#3/#4
- テンプレ元：`apps/toyama-guide/en-kurobe-dam.html` を全文クローン（head canonical/og/ld+json/analytics.js・reader-follow-block ¥100 CTA・affiliates.js include・CSS一式）
- 制約順守：¥0／A4（町名・番地・個人民宿名なし＝村/hamlet レベルまで）／A5（誇張・断定なし、料金/券種/所要は [confirm on the official site] で逃す）／著作権配慮（数値・固有価格を引用しない）
- 語数：各 921〜966語（600〜1000内）。h1×1・h2×4〜6。全内部リンク実在を検証済（リンク切れ0）。
- sitemap.xml は未編集（code がまとめる）。commit も code 側。

## 作成3ページ

| # | ファイル | 主要クエリ | 独自角度（住人一次情報） |
|---|---|---|---|
| 1 | `apps/toyama-guide/en-to-shirakawago-bus.html` | "Shirakawa-go from Takaoka" / "World Heritage Bus timetable" / "Toyama to Shirakawa-go bus" | 一般記事は金沢/高山発。**高岡発=世界遺産バス**の地元優位。券種は「単発/往復/途中下車バンドル」の考え方だけ提示し金額は非引用 |
| 2 | `apps/toyama-guide/en-hokuriku-arch-pass.html` | "Hokuriku Arch Pass worth it" / "does Hokuriku Arch Pass cover Alpine Route" | **頻出誤解の解消**＝「アルペンルートはJR鉄道でない→どのJRパスも非対象、麓の駅まで」を住人視点で明言。価格は非引用 |
| 3 | `apps/toyama-guide/en-gassho-stay.html` | "Gokayama farmhouse stay overnight" / "gassho house stay" / "minshuku Gokayama booking" | 囲炉裏・山の食・**最終バス後に村が静けさを取り戻す一時間**を一次記述。民宿名/番地なし・予約は公式へ誘導 |

## 内部リンク（実在ファイルのみ・相互リンク成立）

- **en-to-shirakawago-bus** → en-takaoka / en-gokayama / en-shirakawa-go / en-gokayama-vs-shirakawa / en-gassho-stay / en-daytrip
- **en-hokuriku-arch-pass** → en-rail-pass / en-alpine-cost / en-alpine / en-vs-kanazawa / en-getting-around / en-from-tokyo
- **en-gassho-stay** → en-gokayama / en-to-shirakawago-bus / en-gokayama-vs-shirakawa / en-gokayama-lightup / en-shirakawa-go / en-where-to-stay
- クラスタ相互：shirakawago-bus ↔ gassho-stay ↔ gokayama/shirakawa-go 成立。arch-pass ↔ rail-pass/alpine-cost/alpine 成立。

## 次アクション（code）

1. sitemap.xml に3URL追加（`en-to-shirakawago-bus` / `en-hokuriku-arch-pass` / `en-gassho-stay`）
2. ハブ/関連ページ（en-gokayama, en-shirakawa-go, en-rail-pass, en-alpine-cost, en-kurobe-gorge 等）から新3ページへの逆リンクを1本ずつ足すと集約強化（任意）
3. commit & push → 公開後 Search Console で主要クエリの表示回数/CTR を検証
