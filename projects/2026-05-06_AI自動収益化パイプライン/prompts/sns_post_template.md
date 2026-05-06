# SNS / Reddit 投稿補助テンプレート

## 共通方針
- 完全自動投稿はしない（規約リスク）
- 「生成 → コピー → ブラウザ起動 → 人間が公開」の半自動運用
- 同じ文面を5アカウント以上に連投しない

## Reddit
### 推奨サブレディット
- r/JapanTravel — 旅行視点／質問形で締める
- r/japanlife — 在住者視点／宣伝控えめ
- r/Toyama — 地元コミュ／タイトルに地域名必須
- r/JapanPics — 画像必須／短文＋風景描写

### フォーマット
```
Title:
{theme_title_en}

Body:
（在住者視点で3〜5文）
（最後に質問で締める）
```

## X (Twitter)
- 1日3投稿まで（自動化しない）
- 1投稿140字以内
- ハッシュタグは2〜3個

```
📍 {theme_title_ja}
{theme_angle}
（一文補足）
続きはnoteに書きました → [URL]
#{kw1} #{kw2} #地方暮らし
```

## Instagram
- キャプションは画像とセットで初めて機能する
- ハッシュタグは10〜15個（過剰NG）
- 改行を多めに、読み物として読める形に

```
{theme_title_ja} ／ {theme_title_en}

{theme_angle}

—
📓 noteに記事を公開しました（プロフィールリンクから）
—
#日本の暮らし #静かな日常 #高岡 #富山 ...
```

## 投稿後マーカ（手動）
```
echo "$(date -Iseconds) sns_post {slug}" >> logs/posted_$(date +%F)_{slug}.log
```
