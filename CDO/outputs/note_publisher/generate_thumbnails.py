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
import time
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parents[2]
ARTICLES_DIR = REPO / "CMO" / "outputs"
THUMB_DIR = SCRIPT_DIR / "thumbnails"
# 生成元の記録。記事プロンプトから作った関連サムネ(openai/gemini/pollinations)を「良」とみなす。
# ここに無い既存ファイル＝素性不明(過去のpicsumランダム等)＝1回だけ再生成して関連画像に置き換える。
PROV_FILE = THUMB_DIR / "_provenance.json"
GOOD_BACKENDS = {"openai", "gemini", "pollinations"}


def load_provenance() -> dict:
    try:
        return json.loads(PROV_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_provenance(prov: dict) -> None:
    try:
        PROV_FILE.write_text(json.dumps(prov, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
    except Exception:
        pass


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


MIN_IMAGE_BYTES = 5000  # これ未満はエラーページ等＝失敗扱い


def generate_with_pollinations(prompt: str, api_key: str = "") -> bytes:
    """Pollinations.ai: APIキー不要・無料の画像生成サービス。
    無料ゆえレート制限/タイムアウトが起きるので、リトライ＋画像サイズ検証で堅牢化する。
    """
    import time
    import urllib.parse
    # プロンプトを短くしないと URL 長で 404 になる。最初の300字程度に切る。
    short = prompt[:300].rsplit(" ", 1)[0]  # 単語途中で切らない
    encoded = urllib.parse.quote(short, safe="")
    # safe=""でスラッシュも%2Fに。FLUXモデル、16:9近似
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=1280&height=720&nologo=true&model=flux"
    )
    last_err: Exception | None = None
    for attempt in range(3):  # 最大3回（バックオフ 0/4/8秒）
        if attempt:
            time.sleep(attempt * 4)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = resp.read()
            if len(data) >= MIN_IMAGE_BYTES:
                return data
            last_err = ValueError(f"画像が小さすぎる({len(data)}B)＝失敗扱い")
        except Exception as e:  # noqa: BLE001  ネットワーク/HTTP全般を握ってリトライ
            last_err = e
    raise last_err or RuntimeError("pollinations 生成失敗")


def pick_backend():
    # owner方針(2026-06-30)：自前AI画像(Pollinations)は画質が荒いので既定で使わない。
    # note見出し画像は「みんなのフォトギャラリー（無料・実写）」を手動採用する運用に切替。
    # AI生成は ALLOW_AI_THUMBNAILS=1 を明示したときだけ（owner任意・既定OFF）。
    if os.environ.get("OPENAI_API_KEY"):
        return "openai", os.environ["OPENAI_API_KEY"]
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini", os.environ["GEMINI_API_KEY"]
    if os.environ.get("ALLOW_AI_THUMBNAILS") == "1":
        return "pollinations", ""
    return "none", ""   # 既定＝AI自動生成しない（荒いため）。みんフォト手動運用に委ねる


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
    if backend == "none":
        print("AI自動生成はOFF（owner方針：荒いため）。note見出し画像はみんなのフォトギャラリー(無料・実写)を手動採用。")
        print("AIを使う場合は環境変数 ALLOW_AI_THUMBNAILS=1。実写無料素材は PEXELS_API_KEY(無料)で。")
        return

    articles = sorted(ARTICLES_DIR.glob("2026-*_note記事_*.md"))
    if args.filter:
        articles = [a for a in articles if args.filter in a.name]

    prov = load_provenance()
    queue = []
    healed = 0
    for a in articles:
        out = THUMB_DIR / f"{a.stem}.jpg"
        # 既存をスキップする条件：--force でなく、かつ「素性が良い」と記録済みのときだけ。
        # 既存でも素性不明（過去のpicsumランダム等＝記録に無い）なら関連画像へ1回だけ再生成する。
        if out.exists() and not args.force:
            if prov.get(a.stem) in GOOD_BACKENDS:
                continue
            healed += 1  # 素性不明の既存を再生成対象に含める
        prompt = extract_thumb_prompt(a.read_text(encoding="utf-8"))
        if not prompt:
            continue
        queue.append((a, prompt, out))

    if args.max > 0:
        queue = queue[: args.max]

    print(f"対象: {len(queue)}本（うち素性不明の再生成: {healed}本）\n")
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
            prov[a.stem] = backend          # 素性を記録（次回からスキップ）
            save_provenance(prov)           # 都度保存＝途中失敗しても進捗が残る
            print(f"  ✓ {out.name}  ({len(data)//1024} KB)")
            ok += 1
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")[:300]
            print(f"  ✗ HTTP {e.code}: {err_body}")
            fail += 1
        except Exception as e:
            print(f"  ✗ {type(e).__name__}: {e}")
            fail += 1
        if backend == "pollinations":
            time.sleep(1.5)                 # 無料枠への配慮＝レート制限回避のペース調整

    print(f"\n成功: {ok} / 失敗: {fail}")


if __name__ == "__main__":
    main()
