"""
generate_thumbnail.py — Pollinations.ai（無料）でサムネ画像を自動生成

実行：
    python generate_thumbnail.py <article_path>

入力：
- 記事Markdown（タイトル+本文）

出力：
- 記事と同じディレクトリに <stem>_thumb.jpg を保存

特徴：
- APIキー不要・完全無料（Pollinations.ai のflux モデル）
- 記事タイトル+冒頭から英訳プロンプトを生成
- 過去サムネ参照ファイル（assets/thumbnail_reference/style_summary.txt）があれば
  スタイルヒントを上書き
"""

from __future__ import annotations

import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PROJECT_DIR = Path(__file__).resolve().parents[1]
REFERENCE_DIR = PROJECT_DIR / "assets" / "thumbnail_reference"

DEFAULT_STYLE = (
    "natural soft afternoon light, photorealistic, cinematic, "
    "slightly desaturated Fuji film color tones, casual everyday Japanese local scene, "
    "Takaoka Toyama Japan, no people in close shot, no text overlay, "
    "Kodak Portra color tones, shot on Fujifilm GFX, shallow depth of field"
)


KEYWORD_TO_SCENE = {
    "鋳物": "a traditional Japanese bronze casting workshop with glowing molten metal",
    "山町筋": "Yamachomachi historic street with black-walled kura warehouses",
    "雨晴": "Amaharashi coast with the Tateyama mountain range visible across the bay",
    "瑞龍寺": "Zuiryu-ji temple wooden corridor with paper shoji screens at dawn",
    "田んぼ": "newly water-filled rice paddies reflecting the spring sky",
    "喫茶店": "a quiet small Japanese cafe interior with warm afternoon light",
    "夕方": "soft golden hour evening light over a Japanese street",
    "新緑": "fresh spring greenery and young rice seedlings",
    "ホタルイカ": "Toyama Bay shoreline at twilight, late spring",
    "金屋町": "Kanayamachi old foundry district with cobblestone street",
    "高岡": "Takaoka city Toyama Japan",
    "海": "Toyama Bay calm sea with Tateyama mountains in distance",
    "朝": "early morning soft light over a Japanese local scene",
    "夜": "Japanese local street at night with warm streetlights",
    "雨": "a quiet rainy day in a Japanese town, wet stone pavement reflecting light",
}


def load_style_hint() -> str:
    f = REFERENCE_DIR / "style_summary.txt"
    if f.exists():
        text = f.read_text(encoding="utf-8").strip()
        if text:
            return text
    return DEFAULT_STYLE


def extract_scene_from_article(article_md: str) -> str:
    """記事タイトル+冒頭から、視覚化しやすいシーン描写を組み立てる。"""
    title = ""
    body_lines: list[str] = []
    for line in article_md.splitlines():
        if not title and line.startswith("# "):
            title = line[2:].strip()
        elif line.strip() and not line.startswith("#"):
            body_lines.append(line.strip())

    intro = " ".join(body_lines[:5])
    combined = title + " " + intro

    matched_scenes: list[str] = []
    for kw, scene in KEYWORD_TO_SCENE.items():
        if kw in combined and scene not in matched_scenes:
            matched_scenes.append(scene)
        if len(matched_scenes) >= 2:
            break

    if not matched_scenes:
        matched_scenes = ["a quiet everyday scene in Takaoka, Toyama, Japan"]

    scene = ", ".join(matched_scenes)
    return scene


def build_prompt(article_md: str) -> str:
    scene = extract_scene_from_article(article_md)
    style = load_style_hint()
    prompt = f"{scene}. {style}. 16:9 widescreen composition."
    # 短すぎず長すぎず（Pollinationsの推奨は500字以内）
    return prompt[:480]


def call_pollinations(prompt: str, out_path: Path) -> None:
    encoded = urllib.parse.quote(prompt, safe="")
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        "?width=1280&height=720&model=flux&nologo=true&private=true&enhance=true"
    )
    print(f"[INFO] Pollinations URL: {url[:150]}...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = resp.read()
    out_path.write_bytes(data)
    print(f"[OK] saved: {out_path} ({len(data)} bytes)")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: generate_thumbnail.py <article_path>")
        return 1
    article_path = Path(argv[1]).resolve()
    if not article_path.exists():
        print(f"[ERROR] not found: {article_path}")
        return 2

    article_md = article_path.read_text(encoding="utf-8")
    prompt = build_prompt(article_md)
    print(f"[INFO] prompt: {prompt}")

    stem = article_path.stem.replace("_note記事", "")
    out_path = article_path.with_name(f"{stem}_thumb.jpg")
    call_pollinations(prompt, out_path)

    # post_to_note.py が article_path から自動で thumb path を解決できるよう、
    # 同じディレクトリに固定名で出力（_thumb.jpg）
    print(str(out_path.relative_to(REPO_ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
