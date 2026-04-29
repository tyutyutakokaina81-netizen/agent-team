#!/usr/bin/env python3
"""
auto_youtube_char_gen.py — Stable Diffusion で写真と見分けがつかない
架空の女子アナウンサー画像を自動生成（完全無料・課金なし）

Mac M1/M2: MPS acceleration で動作
所要時間: 初回モデルダウンロード約5GB / 生成1枚約30〜60秒（M1）
"""

import subprocess
import sys
from pathlib import Path

ASSET_DIR = Path(__file__).parent / "CMO" / "assets" / "announcer"
ASSET_DIR.mkdir(parents=True, exist_ok=True)

# ── キャラクター設定 ────────────────────────────────────────
CHARACTER_NAME = "高岡アイ"

# Stable Diffusion プロンプト（写真クオリティの女性アナウンサー）
PROMPTS = {
    "ai_takaoka_main.png": {
        "positive": (
            "professional female Japanese TV news anchor, mid 30s, 34 years old, "
            "photorealistic, high resolution portrait, "
            "navy blue blazer, white blouse, subtle copper brooch, "
            "long straight black hair, warm mature smile, "
            "holding a microphone, standing pose, "
            "studio lighting, clean white background, "
            "4k photo, hyperrealistic, sharp focus, "
            "beautiful mature face, elegant natural makeup, confident sophisticated expression, "
            "experienced broadcaster look"
        ),
        "negative": (
            "anime, cartoon, illustration, drawing, painting, sketch, "
            "young teen, child, deformed, blurry, bad anatomy, ugly, watermark, text, "
            "nsfw, revealing clothing, excessive jewelry"
        ),
        "size": (512, 768),
    },
    "ai_takaoka_smile.png": {
        "positive": (
            "professional female Japanese TV news anchor, mid 30s, 34 years old, "
            "photorealistic, upper body portrait, "
            "navy blue blazer, bright warm smile, looking at camera, "
            "long straight black hair, elegant natural makeup, "
            "studio lighting, soft bokeh background, "
            "4k photo, hyperrealistic, sharp focus, "
            "mature beautiful face, confident experienced presenter"
        ),
        "negative": (
            "anime, cartoon, illustration, deformed, blurry, "
            "young teen, bad anatomy, ugly, watermark, nsfw"
        ),
        "size": (512, 512),
    },
    "ai_takaoka_guide.png": {
        "positive": (
            "professional female Japanese TV presenter, mid 30s, 34 years old, "
            "photorealistic, full body shot, "
            "navy blue blazer, arm extended welcoming gesture, "
            "Japanese traditional architecture background, "
            "outdoor natural lighting, travel guide style, "
            "4k photo, hyperrealistic, mature elegant appearance"
        ),
        "negative": (
            "anime, cartoon, illustration, deformed, blurry, "
            "young teen, nsfw"
        ),
        "size": (512, 768),
    },
}


def install_deps():
    pkgs = ["diffusers", "transformers", "accelerate", "torch", "torchvision", "Pillow"]
    print("📦 Stable Diffusion ライブラリをインストール中（初回のみ）...")
    subprocess.run([sys.executable, "-m", "pip", "install"] + pkgs + ["-q"])


def generate_with_sd():
    try:
        import torch
        from diffusers import StableDiffusionPipeline
    except ImportError:
        install_deps()
        import torch
        from diffusers import StableDiffusionPipeline

    print("🤖 Stable Diffusion モデルを読み込み中...")
    print("   初回: ~5GB のダウンロードが発生します（以降はキャッシュ）")

    # Mac M1/M2 = mps / CPU fallback
    if torch.backends.mps.is_available():
        device = "mps"
    elif torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"
    print(f"   デバイス: {device}")

    # Realistic Vision v5 — 写真リアリティが高い無料モデル
    model_id = "SG161222/Realistic_Vision_V5.1_noVAE"

    pipe = StableDiffusionPipeline.from_pretrained(
        model_id,
        torch_dtype=torch.float16 if device != "cpu" else torch.float32,
        safety_checker=None,
        requires_safety_checker=False,
    )
    pipe = pipe.to(device)
    pipe.enable_attention_slicing()  # メモリ節約

    print("✅ モデル読み込み完了\n")

    for fname, cfg in PROMPTS.items():
        out_path = ASSET_DIR / fname
        if out_path.exists():
            print(f"  ✅ {fname} 既存（スキップ）")
            continue

        print(f"  🎨 {fname} 生成中...")
        w, h = cfg["size"]

        result = pipe(
            prompt=cfg["positive"],
            negative_prompt=cfg["negative"],
            width=w,
            height=h,
            num_inference_steps=30,
            guidance_scale=7.5,
            num_images_per_prompt=1,
        )
        img = result.images[0]

        # 名前テロップを下部に追加
        from PIL import Image, ImageDraw, ImageFont
        bar = Image.new("RGBA", (w, 50), (10, 30, 80, 210))
        img = img.convert("RGBA")
        img.paste(bar, (0, h - 50), bar)

        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype(
                "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc", 20)
            font_s = ImageFont.truetype(
                "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", 13)
        except Exception:
            font = font_s = ImageFont.load_default()

        draw.text((w // 2, h - 44), CHARACTER_NAME,
                  font=font, fill=(255, 255, 255), anchor="mt")
        draw.text((w // 2, h - 22), "富山・高岡観光ナビゲーター",
                  font=font_s, fill=(180, 210, 255), anchor="mt")

        img.save(out_path, "PNG")
        print(f"  ✅ {fname} 生成完了")

    print(f"\n  保存先: {ASSET_DIR}")


def generate_all():
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  架空女子アナ「高岡アイ」画像生成")
    print("  Stable Diffusion / 写真リアリティ")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    generate_with_sd()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    generate_all()
