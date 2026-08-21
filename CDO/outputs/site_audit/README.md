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

## 監査6項目
| # | 項目 | 種別 | 内容 |
|---|---|---|---|
| 1 | sitemap網羅 | error | `apps/toyama-guide/*.html` が `sitemap.xml` の `<loc>` に全て載っているか |
| 2 | sitemap不整合 | error | `<loc>` にあるが実ファイルが無い（嘘のsitemap） |
| 3 | リンク切れ | error | 内部の `.html` href が実在ファイルを指すか |
| 4 | hreflang相互性 | error | 相互リンク集合が `x-default` を含むか |
| 5 | 孤立ページ | warning | sitemapにあるのに内部inboundリンク0本 |
| 6 | アセット実在 | warning | `<img src>`/`og:image` のローカル参照が実ファイルか |

## なぜ作ったか（設計思想）
- **発見はコントロールできる側**（自責）。オンサイトの取りこぼしは機械で潰せる → 律速をオフサイトに寄せる。
- **「やったと書いたが実物は無い」型の事故を構造的に防ぐ**（8/19空note・アウディ サムネ）。
  ⑥アセット実在チェックは「サムネ登録した」を実ファイルで裏取りする発想と同型。
- **検証ループの常設化**（黄金律③）。季節シリーズ等を増やした直後に即再監査できる。

## 初回運用（2026-08-21）
初回実行で **10ページに `x-default` 欠落** を検知（toyama言語LP 6本＋manga 3言語＋about）。
各ページの `hreflang="en"` と同じURLを指す `x-default` を追加して解消。再監査で errors=0/warnings=0。

## 拡張余地
- CIゲート化（pages.yml の前段で `--strict` を回し、欠陥時はデプロイ前に気づく）。
- 対象を toyama 以外の `apps/*` に広げる（`PAGES_DIR`/`SITEMAP`/`LOC_MARK` を引数化）。
