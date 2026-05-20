"""
generate_thumbnail.py — DALL-E 3でサムネ画像を自動生成

実行：
    OPENAI_API_KEY=... python generate_thumbnail.py <article_path>

入力：
- 記事Markdown（タイトル+本文）

出力：
- 記事と同じディレクトリに <stem>_thumb.png を保存

ロジック：
- 記事タイトル+冒頭500字をClaudeに渡して、画像プロンプトを生成
- そのプロンプトをDALL-E 3に投げて画像生成
- 過去サムネ参照ファイル (assets/thumbnail_reference/) があればスタイルを寄せる
"""

from __future__ import annotations

import base64
import os
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PROJECT_DIR = Path(__file__).resolve().parents[1]
REFERENCE_DIR = PROJECT_DIR / "assets" / "thumbnail_reference"

DEFAULT_STYLE_HINT = (
    "natural light, photorealistic, slightly desaturated, Fuji film color tones, "
    "no people in close shot, no text overlay, casual everyday Japanese local scene"
)


def derive_prompt_from_article(article_md: str) -> str:
    """記事冒頭の情景描写を元に画像プロンプトを組み立てる。

    本来はClaudeに要約させる方が品質が高いが、依存を減らすため
    記事の最初の段落を抜き出して英訳テンプレートに埋め込む簡易版。
    APIキーが余れば claude_summarize() に差し替え可能。
    """
    lines = [ln.strip() for ln in article_md.splitlines() if ln.strip() and not ln.startswith("#")]
    intro = " ".join(lines[:3])[:300]

    style_hint = DEFAULT_STYLE_HINT
    style_file = REFERENCE_DIR / "style_summary.txt"
    if style_file.exists():
        style_hint = style_file.read_text(encoding="utf-8").strip() or DEFAULT_STYLE_HINT

    prompt = (
        "A daily-life photograph from Takaoka, Toyama, Japan, depicting the following scene: "
        f"{intro}. "
        f"Style: {style_hint}. "
        "Composition: wide angle, the scene speaks for itself. "
        "No text, no logo, no watermark. Aspect ratio 16:9."
    )
    return prompt


def call_dalle(prompt: str) -> bytes:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY が未設定")

    import json
    import urllib.request

    req = urllib.request.Request(
        "https://api.openai.com/v1/images/generations",
        data=json.dumps(
            {
                "model": "dall-e-3",
                "prompt": prompt,
                "n": 1,
                "size": "1792x1024",
                "quality": "hd",
                "response_format": "b64_json",
            }
        ).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    b64 = body["data"][0]["b64_json"]
    return base64.b64decode(b64)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: generate_thumbnail.py <article_path>")
        return 1
    article_path = Path(argv[1]).resolve()
    if not article_path.exists():
        print(f"[ERROR] 記事が見つかりません: {article_path}")
        return 2

    article_md = article_path.read_text(encoding="utf-8")
    prompt = derive_prompt_from_article(article_md)
    print(f"[INFO] 生成プロンプト:\n{prompt}\n")

    image_bytes = call_dalle(prompt)
    out_path = article_path.with_name(article_path.stem.replace("_note記事", "") + "_thumb.png")
    out_path.write_bytes(image_bytes)
    print(f"[OK] サムネを保存: {out_path.relative_to(REPO_ROOT)}")
    print(str(out_path.relative_to(REPO_ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
