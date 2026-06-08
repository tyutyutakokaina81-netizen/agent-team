# site/ — 英語SEOサイト（海外読者の到達面）

note.com は海外Google検索に弱い。所有・高速・meta制御できる**英語ネイティブのSEO面**を
持ち、Doraemon / Kanazawa day trip / hidden Japan 等のクエリで実際に見つかるようにする。
（North Star＝海外の人に読んでもらう）。

## 何をするか

`CMO/outputs/*_note記事_*.md` の **「## English」ブロック**を抽出し、SEO最適化済みの
静的HTML（個別ページ＋index＋sitemap.xml＋robots.txt）を `site/public/` に生成する。
依存ゼロ（Python標準ライブラリのみ）。現状 **約43本**の英語記事をページ化。

各ページに付与：`<title>` / meta description / canonical / Open Graph / Twitter card /
JSON-LD(Article) / モバイル対応CSS / クリーンURL（`/slug/`）。

## ローカルでビルド・プレビュー

```bash
python3 site/build.py
# 独自ドメインを使う場合：
SITE_BASE_URL=https://your-domain.com python3 site/build.py
# プレビュー（http://localhost:8000）：
python3 -m http.server 8000 -d site/public
```

`site/public/` は生成物なので Git 管理外（.gitignore）。記事を足して再ビルドすれば増える。

## 公開（GitHub Pages / Cloudflare Pages）

> ⚠️ **このリポジトリの GitHub Pages は現在 `tavern.html`（ルイーダの酒場）が使用中**。
> Pages はリポジトリに1つなので、英語サイトの公開方法はオーナー判断（下記いずれか）。

### 案A：GitHub Pages を英語サイトに切替（tavernを置換 or 退避）
1. `.github/workflows/` に Pages デプロイ用ワークフローを追加（`python3 site/build.py` → `site/public` を deploy）。
2. リポジトリ Settings → Pages → Source: **GitHub Actions**。
3. （任意）独自ドメイン：Settings → Pages → Custom domain＋DNS、Variables に `SITE_BASE_URL` を設定。
4. main にマージ → 自動ビルド＆公開。

### 案B：Cloudflare Pages（tavernはGH Pagesに残す・推奨の住み分け）
1. Cloudflare Pages で本リポジトリを連携。
2. Build command: `python3 site/build.py` ／ Output dir: `site/public`。
3. 環境変数 `SITE_BASE_URL` に独自ドメイン。→ 別ドメインで英語サイトを配信、tavernと共存。

## 設定（build.py 冒頭）

- `SITE_NAME`（既定 "Hidden Hokuriku"）／`SITE_TAGLINE`／`SITE_BASE_URL`（独自ドメイン）。
- 記事は `## English` ブロックを持つものが対象。新規記事は最低ボリューム基準（英語350-450語）で書けば自動で良質ページになる。
