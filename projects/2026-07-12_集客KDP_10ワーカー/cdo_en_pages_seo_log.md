# CDO作業ログ — 英語ページ 内部リンク＋note/¥100 CTA 実装

- 日付: 2026-07-12
- 担当: CDO（技術・実装）
- North Star: 高岡・氷見・富山を海外読者に。既存97枚の英語ページ（`apps/toyama-guide/en-*.html`）の**変換率・回遊率を上げる**（記事は増やさない）。
- 方針: 主要15ページに絞り、既存レイアウト/文体を壊さず**該当箇所のみ**編集。1ページ1CTA厳守・リンク切れゼロ（存在ファイルのみ）。

## 実装内容（各ページ共通パターン）
1. **note/¥100 CTA（1ページ1つ）**: 既存の `reader-follow-block`（Follow on note →）paragraph の末尾に `<br>` で1文追記。押し売りせず「役に立ったら支援」トーン（A5準拠）。英語読者向けのため **¥100(EN) `https://note.com/safe_canna441/n/nba958ccd6cb8`** を使用。
2. **関連ページ内部リンク（2〜3本）**: `<!-- reader-follow-block -->` の直前に `<p class="tag">Related: …</p>` を新規挿入。既存 tag 行と重複しない、実在する関連ページのみへリンク（回遊率UP・crawl改善）。
- 冪等スクリプトで実施（再実行しても二重挿入しない）。全 Related リンクの実在チェック済み（BROKEN=0）。CTA重複チェック済み（各ページ1）。

## 触ったページ一覧（15ページ）

| # | ページ | 追加した関連リンク（Related行） | ¥100 CTA |
|---|--------|------------------------------|----------|
| 1 | en.html（EN home/hub） | （ハブのため関連行はスキップ・既存ナビ十分） | ✅ |
| 2 | en-food.html | en-crab / en-shiroebi / en-toyama-black | ✅ |
| 3 | en-access.html | en-rail-pass / en-from-tokyo / en-getting-around | ✅ |
| 4 | en-alpine.html | en-murodo / en-mikurigaike / en-tateyama-snow-wall | ✅ |
| 5 | en-amaharashi.html | en-photo-spots / en-takaoka / en-food | ✅ |
| 6 | en-manga-pilgrimage.html | en-takaoka / en-himi / en-things-to-do | ✅ |
| 7 | en-doraemon.html | en-takaoka-daibutsu / en-copperware / en-zuiryuji | ✅ |
| 8 | en-himi.html | en-himi-udon / en-crab / en-buri-yellowtail | ✅ |
| 9 | en-takaoka.html | en-takaoka-daibutsu / en-zuiryuji / en-doraemon | ✅ |
| 10 | en-crab.html | en-himi / en-buri-yellowtail / en-seafood-bowl | ✅ |
| 11 | en-onsen.html | en-unazuki-onsen / en-kurobe-gorge / en-where-to-stay | ✅ |
| 12 | en-itinerary.html | en-how-many-days / en-where-to-stay / en-access | ✅ |
| 13 | en-daytrip.html | en-amaharashi / en-food / en-access | ✅ |
| 14 | en-things-to-do.html | en-itinerary / en-food / en-manga-pilgrimage | ✅ |
| 15 | en-where-to-stay.html | en-onsen / en-unazuki-onsen / en-budget | ✅ |

- CTA設置: **15ページ / 各1つ**（合計15）
- Related内部リンク行: **14ページ**（en.html除く）／新規内部リンク計42本

## 制約遵守
- ¥0: 静的HTML編集のみ、API/課金なし。
- A5: 誇張なし・断定なし・1ページ1CTA・押し売り回避（「役に立ったら」トーン）。
- A4: 町名/番地は追記していない（既存本文にも触れず）。
- リンク切れ: Related全リンクの実在を確認（BROKEN=0）。既存情報・レイアウト・文体は非改変。
- 認証情報: 未取扱い。**pushはしない**（code が最後にまとめてpush）。

## 検証
- `grep -c nba958ccd6cb8` 各ページ=1（CTA二重なし）。
- Related href の実在チェック: 全て存在。
- 既存 `Follow on note →` / affiliate / p.tag 行は保持（末尾追記のみ）。
