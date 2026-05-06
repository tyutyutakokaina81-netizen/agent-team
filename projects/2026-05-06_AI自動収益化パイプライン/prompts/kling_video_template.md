# Kling AI / Runway / Hailuo / Pixverse 共通テンプレート

## 入力
- シーン：{scene_description}
- カメラ：{camera_movement}（例：slow dolly-in / static / handheld）
- 比率：{aspect}（16:9 横 or 9:16 縦）
- 尺：{duration}（既定 5s）

## 出力（メインプロンプト）
```
{scene_description}, {camera_movement},
cinematic, realistic, shot on 35mm film,
muted elegant tones, shallow depth of field,
no fake text signs, no unreadable captions, no on-screen text,
Japanese local atmosphere, {duration}, {aspect}
```

## ネガティブプロンプト（共通）
```
low quality, blurry, oversaturated colors, neon signs,
fake japanese text, distorted faces, watermark, logo,
captions, subtitles, text overlay
```

## 注意
- Kling 無料枠は深夜2時でも混雑する。失敗が3日続いたらスタンダードプラン（$6.99/月）を検討。
- 文字情報は AI が捏造しがちなので、**no on-screen text** をネガティブに必ず入れる。
- 同じシーンでも camera_movement を変えるだけで雰囲気が大きく変わる。
