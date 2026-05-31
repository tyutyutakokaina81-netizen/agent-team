# Cross-Post Tools — note記事を海外チャネルへ展開する

「外国人アクセスを伸ばす」戦略の実装。CMO/outputs/ にあるnote記事から、
Reddit / X / Substack 向けの素材を**Macで自動生成**します。

私（Claude）のクラウドコンテナは外部接続できないため、これらは全て**オーナーのMacで実行**する想定。

## ファイル

| 用途 | スクリプト | 出力先 |
|---|---|---|
| Reddit投稿テンプレ生成 | `gen_reddit_post.py` | `EN/outputs/reddit/` |
| X(Twitter)英語ツイート生成 | `gen_x_tweets.py` | `EN/outputs/x_tweets/` |
| Substack英語記事用プロンプト生成 | `gen_en_article.py` | `EN/research/` |
| 共通パーサ | `_common.py` | — |

## 初回セットアップ

依存ライブラリなし（Python標準のみ）。即動きます。
```bash
cd ~/agent-team/CDO/outputs/cross_post
python3 gen_reddit_post.py --article ../../../CMO/outputs/2026-06-01_note記事_細工かまぼこ_結婚式に鯛がついてくる富山.md
```

## 推奨ワークフロー

### A. Reddit展開（最短）
```bash
python3 gen_reddit_post.py --article <記事パス> --copy
```
- `EN/outputs/reddit/` に複数サブレディット用のテンプレが保存
- 最初の候補がクリップボードにコピーされる
- そのまま reddit.com で submit

### B. X(Twitter)展開
```bash
python3 gen_x_tweets.py --article <記事パス> --copy
```
- 単発ツイート＋スレッド型の両方を生成
- 単発がクリップボードへ

### C. Substack/Medium 英語記事化
```bash
python3 gen_en_article.py --article <記事パス> --copy
```
- 完成形ではなく、**Claude/ChatGPT へ貼って完成させるためのプロンプト**を生成
- プロンプトがクリップボードへ
- Claude等で完成英語記事を得たら、`EN/outputs/YYYY-MM-DD_en_*.md` に保存

## 一括展開（今後の運用想定）

最新note記事に対して、Reddit/X/Substack の3チャネル分を一気に生成：
```bash
cd ~/agent-team/CDO/outputs/cross_post
python3 gen_reddit_post.py
python3 gen_x_tweets.py
python3 gen_en_article.py
```
（引数なしで最新記事を自動選択）

## 注意

- ハッシュタグは記事mdから抽出（英語タグが少ない記事は手で足す）
- Reddit運用：規約に従い、宣伝目的ではなく**コミュニティへの貢献**として投稿
- X運用：同じ記事を何度も投稿しない（スパム判定回避）
- Substack/Medium：1記事ごとに翻訳→公開でローテーション

## 関連戦略文書

- `CAO/outputs/2026-05-31_海外アクセス強化戦略.md` — KPI と運用方針
- `CAO/outputs/2026-05-31_全39記事監査と是正計画.md` — 既存記事の品質状況
