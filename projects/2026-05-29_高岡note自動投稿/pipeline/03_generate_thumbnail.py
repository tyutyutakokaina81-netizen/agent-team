"""
03_generate_thumbnail.py — 実写（フォトリアル）サムネを生成

記事フロントマターの thumbnail_prompt を画像生成APIに渡して
横長サムネ（推奨1280x670前後）を thumbnails/ に保存する。

プロバイダは config.json の "image_provider" で切替（openai / stability）。
必要な環境変数:
  - openai   : OPENAI_API_KEY
  - stability: STABILITY_API_KEY

note にはAPI投稿が無いので画像は file として保存し、04 で添付アップロードする。
"""

import os
import re
import json
import base64
from pathlib import Path
import urllib.request

BASE = Path(__file__).resolve().parent.parent
THUMB_DIR = BASE / "thumbnails"
CONFIG = Path(__file__).resolve().parent / "config.json"


def read_front_matter(article_path: Path) -> dict:
    text = article_path.read_text(encoding="utf-8")
    m = re.search(r"^---\n(.*?)\n---", text, re.DOTALL)
    fm = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                fm[k.strip()] = v.strip().strip('"')
    return fm


def load_config() -> dict:
    if CONFIG.exists():
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    return {"image_provider": "openai", "image_size": "1536x640"}


def _gen_openai(prompt: str, size: str) -> bytes:
    req = urllib.request.Request(
        "https://api.openai.com/v1/images/generations",
        data=json.dumps({
            "model": "gpt-image-1",
            "prompt": prompt,
            "size": size,
            "n": 1,
        }).encode(),
        headers={
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read())
    b64 = data["data"][0]["b64_json"]
    return base64.b64decode(b64)


def _gen_stability(prompt: str, size: str) -> bytes:
    # Stability の実装はアカウント/モデルにより異なるため雛形のみ
    raise NotImplementedError("stability プロバイダは利用環境に合わせて実装してください。")


def generate(article_path: Path) -> Path:
    cfg = load_config()
    fm = read_front_matter(article_path)
    prompt = fm.get("thumbnail_prompt")
    if not prompt:
        raise ValueError(f"thumbnail_prompt がありません: {article_path}")

    provider = cfg.get("image_provider", "openai")
    size = cfg.get("image_size", "1536x640")
    img = {"openai": _gen_openai, "stability": _gen_stability}[provider](prompt, size)

    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    out = THUMB_DIR / (article_path.stem + ".png")
    out.write_bytes(img)
    print(f"[thumbnail] saved: {out} (provider={provider})")
    return out


if __name__ == "__main__":
    import sys
    generate(Path(sys.argv[1]))
