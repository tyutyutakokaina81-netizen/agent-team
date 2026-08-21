# site_audit — Pages発見インフラの機械監査

海外読者リーチ(North Star)の律速＝「発見」。作った多言語Pagesが**技術的に発見可能な状態**を
保っているかを、毎回手作業でなく1コマンドで検証する常設ツール。ゼロ依存・完全ローカル（A1準拠・
ネット/認証に触れない）。

## 使い方
```bash
python3 CDO/outputs/site_audit/audit_pages.py          # 人間向けレポート
python3 CDO/outputs/site_audit/audit_pages.py --json   # JSON（集計/CIゲート用）
python3 CDO/outputs/site_audit/audit_pages.py --strict # 警告(孤立/アセット欠落)もexit=1に含める
# 終了コード: 0=致命的欠陥なし / 1=欠陥あり
```

## 監査項目
| # | 項目 | 種別 | 内容 |
|---|---|---|---|
| 1 | sitemap網羅 | error | `apps/toyama-guide/*.html` が `sitemap.xml` の `<loc>` に全て載っているか |
| 2 | sitemap不整合 | error | `<loc>` にあるが実ファイルが無い（嘘のsitemap） |
| 3 | リンク切れ | error | 内部の `.html` href が実在ファイルを指すか |
| 4a | hreflang x-default | error | 各hreflangクラスタが `x-default` を含むか |
| 4b | hreflang alternate実在 | error | hreflang の alternate 先ファイルが実在するか（削除ページを指していないか） |
| 4c | hreflang非相互 | warning | A→B と宣言するのに B→A が無いページ（下記の注） |
| 5 | 孤立ページ | warning | sitemapにあるのに内部inboundリンク0本 |
| 6 | アセット実在 | warning | `<img src>`/`og:image` のローカル参照が実ファイルか |

> **公開ルート正規化**: `/toyama/`・`/toyama` の参照は `index.html` と同一視して判定する
> （トップが2つのURL表記を持つことによる誤検知を防ぐ）。

## hreflang非相互(4c)を warning に留める理由
非相互hreflangは Google が**無視するだけでペナルティは無い**。当サイトの非相互の大半は
「英語サブページが `ja` alternate に日本語トップ(index.html)を指すが、トップは全サブページを
相互宣言できない」型（多対一）で、正すには**各英語ページの"真の日本語対訳"を決める**か、
**対訳の無いページの ja hreflang を外す**かのコンテンツ判断が要る。機械で一括改変すると
誤った対訳を生むため、**可視化に留め、判断はowner/CMOに委ねる**設計にした。
`--strict` を付けると warning も exit=1 になる（CIで厳格運用したい時用）。

## なぜ作ったか（設計思想）
- **発見はコントロールできる側**（自責）。オンサイトの取りこぼしは機械で潰せる → 律速をオフサイトに寄せる。
- **「やったと書いたが実物は無い」型の事故を構造的に防ぐ**（8/19空note・アウディ サムネ）。
  ⑥アセット実在チェックは「サムネ登録した」を実ファイルで裏取りする発想と同型。
- **検証ループの常設化**（黄金律③）。季節シリーズ等を増やした直後に即再監査できる。

## 運用ログ
- **2026-08-21 初回**: **10ページに `x-default` 欠落** を検知（言語LP6＋manga3言語＋about）。
  各ページの英語版と同じURLの `x-default` を追加して解消。
- **2026-08-21 監査項目強化**: 4b(alternate実在)・4c(非相互)・ルート正規化を追加。
  再実行で **6言語LP→en.html の非相互** を検知→ **en.html に6言語siblingのhreflangを追記**して相互化。
  残り **56件の非相互**＝英語サブページ→日本語トップの多対一（上記4cの注のとおり要コンテンツ判断・owner案件）。
  致命的欠陥は0を維持。

## 拡張余地
- CIゲート化（pages.yml の前段で `--strict` を回し、欠陥時はデプロイ前に気づく）。
- 対象を toyama 以外の `apps/*` に広げる（`PAGES_DIR`/`SITEMAP`/`LOC_MARK` を引数化）。
