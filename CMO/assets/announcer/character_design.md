# 架空女子アナウンサー キャラクター設定書

## キャラクター名
**高岡アイ（たかおか あい）**
英語表記: Ai Takaoka

## プロフィール
| 項目 | 内容 |
|------|------|
| 年齢 | 28歳（設定・20代後半） |
| 出身 | 富山県高岡市 |
| 職業 | 富山県観光PR大使（架空） |
| 性格 | 明るく親しみやすい、地元愛が強い |
| 口癖 | 「実はですね〜！」「知ってました？」 |

---

## 画像生成プロンプト（DALL-E / Stable Diffusion 用）

### ▼ メインビジュアル（立ち絵・全身）
```
A professional Japanese female TV announcer named Ai Takaoka, 
late 20s, 28 years old, warm smile, wearing a navy blue blazer with a 
traditional Takaoka copper brooch, holding a microphone, 
standing confidently, anime-style illustration, clean lines, 
soft lighting, white background, full body shot
```

### ▼ サムネイル用（上半身・笑顔）
```
Cute Japanese female announcer, upper body portrait, 
bright smile, navy blazer, long black hair, 
holding a small Takaoka copper ornament, 
anime illustration style, vibrant colors, 
YouTube thumbnail style, 1280x720
```

### ▼ 驚き顔（情報紹介シーン）
```
Anime female announcer with surprised/excited expression, 
open mouth, pointing gesture, navy blazer, 
speech bubble with exclamation mark, 
clean anime style illustration
```

### ▼ 案内ポーズ（観光地紹介シーン）
```
Anime female tour guide gesturing toward background, 
welcoming pose, arm extended, warm smile, 
navy blue professional outfit, 
traditional Japanese temple visible in soft focus background
```

---

## 使い方

1. 上のプロンプトをChatGPT（DALL-E）またはAdobe Fireflyに貼る
2. 生成された画像を `CMO/assets/announcer/` に保存
   - `ai_takaoka_main.png`（全身）
   - `ai_takaoka_smile.png`（上半身）
   - `ai_takaoka_surprise.png`（驚き）
   - `ai_takaoka_guide.png`（案内）
3. `auto_youtube_produce.py` が自動で読み込んで動画に合成する

---

## 声の設定（VOICEVOX）

| 設定 | 値 |
|------|-----|
| キャラクター | 春日部つむぎ（speaker_id=8）または四国めたん（speaker_id=2） |
| 話速 | 1.1（少し速め・テンポよく） |
| 音程 | +0.02（明るめ） |
| 抑揚 | 1.2（メリハリあり） |

VOICEVOXダウンロード: https://voicevox.hiroshiba.jp/

---

## 背景画像 プロンプト集

### ① 高岡市全景（オープニング）
```
Aerial view of Takaoka city, Toyama Prefecture Japan, 
golden hour lighting, traditional rooftops and modern cityscape, 
cinematic wide shot, high resolution travel photography
```

### ② 瑞龍寺
```
Zuiryuji Temple Takaoka Japan, national treasure Zen Buddhist temple, 
stone pathway with lanterns, morning mist, 
dramatic sky, professional travel photography, 
wide angle shot showing mountain gate and main hall
```

### ③ 高岡大仏
```
Takaoka Daibutsu giant bronze Buddha statue, Toyama Japan, 
blue sky background, dramatic low angle shot looking up, 
traditional Japanese temple architecture, 
golden hour warm lighting
```

### ④ 金屋町
```
Kanayamachi historic street Takaoka, cobblestone path, 
traditional Japanese wooden lattice houses, 
copper craftsmen working, warm afternoon light, 
travel photography, HDR colors
```

### ⑤ 高岡グルメ
```
Japanese street food flat lay, Takaoka korokke croquette, 
Himi udon noodles, tofu, local ingredients, 
food photography style, warm colors, appetizing
```

### ⑥ 北陸新幹線
```
Hokuriku Shinkansen bullet train arriving at 
Shin-Takaoka station, motion blur, 
dramatic perspective shot, sunset sky, 
Japanese railway photography
```
