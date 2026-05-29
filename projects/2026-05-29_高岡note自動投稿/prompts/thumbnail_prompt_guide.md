# 実写サムネ プロンプト設計ガイド

note のサムネは横長（推奨 **1280×670 程度／約1.91:1**）。
記事ごとに `thumbnail_prompt`（英語）をフロントマターに持たせ、
`03_generate_thumbnail.py` が画像生成APIへ渡す。

## 「実写（フォトリアル）」を担保するキーワード

先頭に必ず付ける：
```
photorealistic, realistic photo, DSLR photo, natural lighting, high detail, 8k, --no illustration, no cg, no text
```

## 構図テンプレ

```
photorealistic DSLR photo of {{被写体}}, {{時間帯/光}}, {{画角}},
shallow depth of field, natural color, documentary travel photography style,
no text, no watermark, no people faces in focus, 16:9 wide composition
```

## トピック別 被写体の例

| トピック | 被写体プロンプト断片 |
|---------|------------------|
| 高岡コロッケ | freshly fried golden korokke (Japanese croquette) on paper, steam rising, close-up |
| 高岡銅器/金屋町 | traditional Japanese copperware workshop, old lattice townhouse street, cobblestone |
| 高岡大仏 | large bronze Great Buddha statue in a Japanese town, serene, overcast sky |
| 瑞龍寺 | grand wooden Zen temple complex, symmetrical corridors, moss garden |
| 雨晴海岸 | rocky Japanese coastline with snow-capped Tateyama mountains across the bay, sunrise |
| ます寿司/白えび | traditional trout sushi (masuzushi) round wooden box, white shrimp sashimi |

## 注意

- **文字は入れない**（noteのタイトルが別途乗るため）。`no text` を必ず付与。
- 人物の顔がはっきり写る構図は避ける（肖像権・違和感回避）。
- 生成画像は `thumbnails/` に保存（**gitignore対象**＝コミットしない）。
