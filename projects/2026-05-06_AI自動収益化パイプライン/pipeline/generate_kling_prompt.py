"""Kling AI（および Runway / Hailuo / Pixverse 互換）動画プロンプト生成。

要件：
- cinematic, realistic
- Japanese local atmosphere
- Toyama / Takaoka / quiet life
- short video format (5s)
- no fake text signs / no unreadable captions
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from _common import OUTPUTS, append_log, stamp, write_output
from themes import Theme, theme_for


# テーマslug → 映像シーン定義
SCENE_MAP: dict[str, str] = {
    "quiet-life-takaoka": (
        "Quiet residential street in Takaoka, Toyama at early morning, "
        "soft golden light filtering through low wooden houses, "
        "an empty road and a single bicycle leaning against a fence, "
        "calm autumn air, leaves slowly falling, no people"
    ),
    "amaharashi-coast": (
        "Amaharashi Coast Toyama Japan at golden sunrise, "
        "snow-capped Tateyama Alps rising 3000 meters behind calm Sea of Japan, "
        "cinematic wide shot, breathtaking natural beauty, muted elegant tones"
    ),
    "ai-side-hustle-50s": (
        "Close-up of a 50-year-old Japanese man's hands typing on a laptop "
        "in a quiet wooden room at dawn, soft window light, steam rising from "
        "a ceramic cup of green tea, calm and focused atmosphere, no faces visible"
    ),
    "seasonal-food-toyama": (
        "Top-down macro shot of a Japanese seasonal meal on a wooden tray, "
        "white shrimp sashimi and bowl of rice, condensation on a cold sake glass, "
        "morning light from the side, traditional Japanese tableware, no text"
    ),
    "from-employee-to-solo": (
        "A man walking alone on an empty platform of a small Japanese rural "
        "train station at dusk, blue hour, no passengers, soft station lights, "
        "mood of transition and quiet determination, cinematic medium shot"
    ),
    "takaoka-craft": (
        "Macro close-up of a craftsman's hands polishing a Takaoka copperware bowl "
        "in a dim workshop, warm tungsten light, fine metal dust catching the light, "
        "patina texture, traditional Japanese workshop atmosphere, no faces"
    ),
    "morning-routine-rural": (
        "Steam rising from a ceramic kettle on a wooden table in a quiet Japanese "
        "kitchen, soft sunrise light through paper screens, single bowl and chopsticks, "
        "tatami floor visible in background, slow living mood"
    ),
}


COMMON_SUFFIX = (
    "cinematic, realistic, shot on 35mm film, "
    "muted elegant tones, shallow depth of field, "
    "no fake text signs, no unreadable captions, no on-screen text, "
    "Japanese local atmosphere, 5 seconds, 16:9"
)


def build_kling_prompt(now: datetime | None = None) -> Path:
    now = now or datetime.now()
    theme = theme_for(now.date())
    scene = SCENE_MAP.get(theme.slug, SCENE_MAP["quiet-life-takaoka"])

    main_prompt = f"{scene}, {COMMON_SUFFIX}"

    # 縦動画（Shorts）バリエーション
    vertical_prompt = main_prompt.replace("16:9", "9:16 vertical for short-form video")

    negative = (
        "low quality, blurry, oversaturated colors, neon signs, "
        "fake japanese text, distorted faces, watermark, logo, "
        "captions, subtitles, text overlay"
    )

    body = f"""# Kling AI 動画プロンプト（自動生成）

- 生成日時：{now.isoformat(timespec='seconds')}
- テーマslug：`{theme.slug}`
- タイトル：{theme.title_en}

## メインプロンプト（横位置 16:9 / 5秒）
```
{main_prompt}
```

## 縦位置プロンプト（YouTube Shorts / TikTok 9:16）
```
{vertical_prompt}
```

## ネガティブプロンプト
```
{negative}
```

## カメラ動き候補
- slow dolly-in
- static tripod shot
- subtle handheld
- gentle pan left-to-right

## 切替先（無料枠混雑時）
1. **Kling AI スタンダード** ($6.99/月) — 第一候補
2. **Runway Gen-3** — 高品質・短尺向き
3. **Hailuo** — 写実系で軽量
4. **Pixverse** — 縦動画に強い

## 失敗時のメモ
- 失敗ログは `logs/run.log` に `kling_prompt FAILED` を含むかで判別
- 連続3日失敗したら有料プラン移行を検討する
"""
    out = write_output(f"{stamp(now)}_kling_prompt.md", body)
    append_log("daily", f"kling_prompt generated: {out.name}")
    return out


if __name__ == "__main__":
    path = build_kling_prompt()
    print(f"Kling AI プロンプトを生成しました: {path.relative_to(OUTPUTS.parent)}")
