# site/og/ — OG画像（SNSシェア時のサムネ）の置き場

ここに**フリー画像（写真風・商用可）**を置くと、ビルド時に `/og/` へ配信され、
各ページの `og:image` / `twitter:image` に自動設定される。
→ Pinterest・X・Facebook・LINE 等でリンクを貼ったとき、**大きなサムネ付き**で表示され、
クリック率が上がる（North Star=海外読者の流入）。

## 命名規則

- **記事ごと**: `<記事のスラッグ>.jpg`（推奨 1200×630px）。
  例: `skip-shirakawa-go-for-a-day-the-real-hometown-of-doraemon.jpg`
  スラッグは公開URL `…/agent-team/<スラッグ>/` の `<スラッグ>` 部分。
- **共通フォールバック**: `default.jpg`（記事個別が無いときに使われる）。**まず1枚これを置くと全ページに効く。**
- 対応拡張子: `.jpg .jpeg .png .webp`

## 入手（私=Claudeは画像取得不可なので cowork/オーナーが配置）

- フリー素材（商用可）: Unsplash / Pexels / Pixabay 等で `Takaoka` `Toyama` `Gokayama` `Japan tram` 等。
- ドラえもん系は**キャラ画像NG**（著作権）。場所・風景のフリー画像 or オーナー撮影の実物の像/トラム写真。
- 写真風で統一（イラスト/テキストデザインはNG）。

## 反映

画像を置いて main に push すれば、GitHub Actions が再ビルドして自動反映。
（`site/public/` は生成物。ソース画像はこの `site/og/` に置く＝コミット対象。）

## まず1枚だけでも

`default.jpg`（高岡/富山/立山連峰などの写真風・横長）を1枚置くだけで、
全55ページのシェアサムネが付く。記事別は後から差し替え可。
