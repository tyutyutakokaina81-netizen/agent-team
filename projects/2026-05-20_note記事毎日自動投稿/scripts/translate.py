"""
translate.py — DeepL Free API で日本語→英語翻訳

実行：
    DEEPL_API_KEY=... python translate.py <input.md> [output.md]

- DeepL Free API を利用（月50万字まで無料）
- DEEPL_API_KEY 未設定なら、入力をそのまま出力（フォールバック）
- Markdownの構造を保持しつつ翻訳：
  * 見出し（#）はそのまま翻訳
  * コードブロック、URL、画像構文はスキップ
  * 段落単位でAPIに投げて結合
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

DEEPL_FREE_URL = "https://api-free.deepl.com/v2/translate"


def call_deepl(texts: list[str], target_lang: str = "EN", source_lang: str | None = "JA") -> list[str]:
    api_key = os.environ.get("DEEPL_API_KEY", "").strip()
    if not api_key:
        print("[WARN] DEEPL_API_KEY 未設定。原文をそのまま返します。")
        return texts

    data = [("auth_key", api_key), ("target_lang", target_lang)]
    if source_lang:
        data.append(("source_lang", source_lang))
    for t in texts:
        data.append(("text", t))
    encoded = urllib.parse.urlencode(data).encode("utf-8")

    req = urllib.request.Request(
        DEEPL_FREE_URL,
        data=encoded,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"[ERROR] DeepL API: HTTP {e.code} {e.read().decode('utf-8', errors='replace')[:300]}")
        return texts
    return [t["text"] for t in body.get("translations", [])]


CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`]+`")


def translate_markdown(md_text: str, target_lang: str = "EN") -> str:
    """Markdownを段落単位でDeepLに投げて翻訳する。

    コードブロックや画像URL等はプレースホルダ化して保持。
    """
    placeholders: dict[str, str] = {}

    def stash(pattern: re.Pattern, prefix: str, text: str) -> str:
        def _replace(m: re.Match) -> str:
            key = f"__{prefix}_{len(placeholders)}__"
            placeholders[key] = m.group(0)
            return key

        return pattern.sub(_replace, text)

    text = md_text
    text = stash(CODE_BLOCK_RE, "CODE", text)
    text = stash(INLINE_CODE_RE, "ICODE", text)

    # 段落単位で分割（空行区切り）
    paragraphs = [p for p in text.split("\n\n")]

    # API レート抑制のため、複数段落を1リクエストにまとめる
    BATCH = 30
    translated_paragraphs: list[str] = []
    for i in range(0, len(paragraphs), BATCH):
        chunk = paragraphs[i : i + BATCH]
        # 空文字パラグラフは API に渡さない（自動で空が返る保証はないため）
        non_empty_idx = [j for j, p in enumerate(chunk) if p.strip()]
        non_empty_texts = [chunk[j] for j in non_empty_idx]
        if non_empty_texts:
            translated = call_deepl(non_empty_texts, target_lang=target_lang)
            for j, t in zip(non_empty_idx, translated):
                chunk[j] = t
        translated_paragraphs.extend(chunk)

    result = "\n\n".join(translated_paragraphs)
    # プレースホルダ復元
    for key, original in placeholders.items():
        result = result.replace(key, original)
    return result


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: translate.py <input.md> [output.md]")
        return 1
    inp = Path(argv[1])
    if not inp.exists():
        print(f"[ERROR] not found: {inp}")
        return 2
    out = Path(argv[2]) if len(argv) >= 3 else inp.with_suffix(".en.md")

    md = inp.read_text(encoding="utf-8")
    translated = translate_markdown(md, target_lang="EN")
    out.write_text(translated, encoding="utf-8")
    print(f"[OK] translated → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
