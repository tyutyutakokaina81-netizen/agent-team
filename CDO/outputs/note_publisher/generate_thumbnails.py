#!/usr/bin/env python3
"""
generate_thumbnails.py — 各記事の「## サムネ用プロンプト」を画像APIに投げて
thumbnails/{記事stem}.jpg として保存する。

対応API（環境変数で自動切替）:
- OPENAI_API_KEY → OpenAI gpt-image-1 (高品質・要課金)
- GEMINI_API_KEY → Google Imagen 3 (Google AI Studio)

使い方:
  export OPENAI_API_KEY=sk-...
  python3 generate_thumbnails.py                 # まだ生成していない全件
  python3 generate_thumbnails.py --filter 2026-06-01  # 指定日のみ
  python3 generate_thumbnails.py --force         # 既存ファイルも上書き
"""
from __future__ import annotations
import argparse
import base64
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parents[2]
ARTICLES_DIR = REPO / "CMO" / "outputs"
THUMB_DIR = SCRIPT_DIR / "thumbnails"


def extract_thumb_prompt(text: str) -> str | None:
    m = re.search(
        r"^##\s*サムネ.*?\n\n?```\s*\n(.+?)\n```",
        text, re.MULTILINE | re.DOTALL,
    )
    if m:
        return m.group(1).strip()
    for blk in re.findall(r"```\s*\n([^`]*?Photorealistic[^`]*?)\n```", text, re.DOTALL):
        return blk.strip()
    return None


def http_post_json(url: str, headers: dict, payload: dict, timeout: int = 120) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={**headers, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def generate_with_openai(prompt: str, api_key: str) -> bytes:
    res = http_post_json(
        "https://api.openai.com/v1/images/generations",
        {"Authorization": f"Bearer {api_key}"},
        {
            "model": "gpt-image-1",
            "prompt": prompt,
            "size": "1536x1024",  # 16:9 近似
            "quality": "high",
            "n": 1,
        },
    )
    b64 = res["data"][0]["b64_json"]
    return base64.b64decode(b64)


def generate_with_gemini(prompt: str, api_key: str) -> bytes:
    # Google AI Studio: Imagen 3 predict endpoint
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "imagen-3.0-generate-002:predict?key=" + api_key
    )
    res = http_post_json(
        url,
        {},
        {
            "instances": [{"prompt": prompt}],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": "16:9",
                "personGeneration": "DONT_ALLOW",
            },
        },
    )
    b64 = res["predictions"][0]["bytesBase64Encoded"]
    return base64.b64decode(b64)


def generate_with_pollinations(prompt: str, api_key: str = "") -> bytes:
    """Pollinations.ai: APIキー不要・無料の画像生成サービス。"""
    import urllib.parse
    # FLUX.1ベースのモデル。16:9近似（width=1280, height=720）
    encoded = urllib.parse.quote(prompt[:1900])  # URL長制限の安全圏
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=1280&height=720&nologo=true&model=flux&enhance=true"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        return resp.read()


def pick_backend():
    if os.environ.get("OPENAI_API_KEY"):
        return "openai", os.environ["OPENAI_API_KEY"]
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini", os.environ["GEMINI_API_KEY"]
    # キー無しでも動く Pollinations をデフォルトに
    return "pollinations", ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--filter", default="", help="ファイル名部分一致フィルタ")
    ap.add_argument("--force", action="store_true", help="既存画像も上書き")
    ap.add_argument("--max", type=int, default=0, help="最大何本まで")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    backend, key = pick_backend()
    print(f"backend: {backend}")

    articles = sorted(ARTICLES_DIR.glob("2026-*_note記事_*.md"))
    if args.filter:
        articles = [a for a in articles if args.filter in a.name]

    queue = []
    for a in articles:
        out = THUMB_DIR / f"{a.stem}.jpg"
        if out.exists() and not args.force:
            continue
        prompt = extract_thumb_prompt(a.read_text(encoding="utf-8"))
        if not prompt:
            continue
        queue.append((a, prompt, out))

    if args.max > 0:
        queue = queue[: args.max]

    print(f"対象: {len(queue)}本\n")
    if args.dry_run:
        for a, _, out in queue:
            print(f"  + {a.stem}  →  {out.name}")
        return

    ok = fail = 0
    for a, prompt, out in queue:
        print(f"→ {a.stem}")
        try:
            if backend == "openai":
                data = generate_with_openai(prompt, key)
            elif backend == "gemini":
                data = generate_with_gemini(prompt, key)
            else:
                data = generate_with_pollinations(prompt)
            out.write_bytes(data)
            print(f"  ✓ {out.name}  ({len(data)//1024} KB)")
            ok += 1
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")[:300]
            print(f"  ✗ HTTP {e.code}: {err_body}")
            fail += 1
        except Exception as e:
            print(f"  ✗ {type(e).__name__}: {e}")
            fail += 1

    print(f"\n成功: {ok} / 失敗: {fail}")


if __name__ == "__main__":
    main()
