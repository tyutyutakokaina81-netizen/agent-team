# CDO 技術SEO監査ログ — 英語ガイド15ページ（2026-07-14）

担当：CDO（技術・実装・検証ループ）／目的：LIVE な `apps/toyama-guide/en-*.html` を Google に確実に拾わせる技術SEO底上げ。
制約：本文（prose）書き換え禁止・`<head>`とリンクの整備のみ・¥0・A4/A5・リンク切れ厳禁・sitemap.xml / en-index / en-start-here には触れない。

## 結論（要点）
- 対象15ページはいずれも **title / description / canonical / og:url / og:title / robots / 妥当なJSON-LD** を既に保有（大半はCMO側で整備済み）。
- **実際の欠落は og:image の未設定（5ページ）のみ** → 追加して解消。
- hreflang は **付与せず**（下記理由）。schema @type は既存の Article を維持（下記理由）。
- 検証：全15ページで og:image=1・JSON-LD が妥当JSON・`<script>`タグ対応（open=close=3）を確認。HTML破損なし。

## 触ったページと追加要素

| ページ | 追加/変更した要素 | 備考 |
|---|---|---|
| en-from-tokyo.html | `og:image` 追加 | 既存の他タグは維持 |
| en-from-kansai.html | `og:image` 追加 | 同上 |
| en-crab.html | `og:image` 追加 | 同上 |
| en-buri-yellowtail.html | `og:image` 追加 | 同上 |
| en-glass-art.html | `og:image` 追加 | 同上 |

- 追加した og:image は **既存の実在画像** `…/toyama/og/en.png` を安全なフォールバックとして使用。
  - 理由：これら5ページの専用OG画像（`og/en-<slug>.png`）は**ディスク上に存在しない**ため、専用URLを書くと**壊れた参照**になる（fail-closed）。実在するサイト共通OG画像を指すことで、リンク切れを作らずソーシャルカードを有効化。
  - 専用OG画像が後日生成されたら、この5ページの og:image を差し替え可能（TODO）。

## 触っていないページ（既に技術SEO充足・確認のみ）
en-access, en-food, en-himi, en-doraemon, en-hattori, en-amaharashi, en-alpine, en-daytrip, en-how-many-days, en-gokayama
（title一意・description一意・canonical/og:url がファイル名と一致・og:image 実在PNGを参照・JSON-LD妥当・本文末に実在enページへの内部リンク2〜3本を確認済み）

## 意図的に「やらなかった」判断（無退行・最小変更）

### 1. hreflang は全ページで付与せず
- ルール：日本語対応ページ（`en-` を外した同名 `*.html`）が存在する場合のみ相互 hreflang を張る。
- 実測：`access.html / food.html / himi.html / alpine.html / crab.html / gokayama.html …` など、対象15スラッグの **ja版同名ファイルは1つも存在しない**（`himi-fish.html`・`kanburi.html` 等はあるが同名ではない）。
- よって hreflang を張ると **リンク切れ**になるため、A制約・「リンク切れ厳禁」に従い付与しない。

### 2. schema.org @type は既存の Article を維持（TouristAttraction へ強制変換しない）
- 対象15ページは全て **妥当な `Article` JSON-LD** を既に保有（`headline`/`url`/`publisher` 等）。
- 観光地系（himi/amaharashi/alpine/gokayama/glass-art 等）を TouristAttraction へ変換するには `headline` 除去などの再構成が必要で、**LIVE かつインデックス済みの正しいページに退行リスク**を持ち込む。
- タスク方針「あれば整える／最小構成でよい」に照らし、妥当なJSON-LDは温存が最善と判断（無退行原則）。将来オーナー指示があれば個別に TouristAttraction 化する。

## 検証（実機・簡易）
- Python で15ページを走査：`og:image`件数=各1、JSON-LDブロックを `json.loads` で全件パース成功（BAD=0）、`<script>`開閉数一致（3/3）。
- 内部リンク先の実在確認：en-itinerary / en-things-to-do / en-seafood-bowl / en-winter / en-toyama-city / en-food / en-himi いずれも実在。

## 次アクション（code担当）
- 変更は commit 不要指示のため未commit。code が sitemap.xml と併せて一括 commit & push → deploy（IndexNow通知）。
- 中期TODO：5ページ専用OG画像（`og/en-from-tokyo.png` 等）が生成できたら og:image を専用URLへ差し替え。
