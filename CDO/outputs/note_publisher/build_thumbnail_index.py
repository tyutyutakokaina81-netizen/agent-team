#!/usr/bin/env python3
"""
build_thumbnail_index.py — 全記事のサムネプロンプトを1ファイルに集約
"""
from __future__ import annotations
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ARTICLES_DIR = REPO / "CMO" / "outputs"
OUT = ARTICLES_DIR / "_thumbnail_prompts_index.md"

def extract_title(text: str) -> str:
    m = re.search(r"^## タイトル\s*\n```\s*\n(.+?)\n```", text, re.MULTILINE | re.DOTALL)
    if m:
        return m.group(1).strip().splitlines()[0]
    m = re.search(r"^#\s+note記事[:：]\s*(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else ""

def extract_thumb_prompt(text: str) -> str | None:
    # "## サムネ" を含む見出しの直後の ``` ブロック
    m = re.search(
        r"^##\s*サムネ.*?\n\n?```\s*\n(.+?)\n```",
        text, re.MULTILINE | re.DOTALL,
    )
    if m:
        return m.group(1).strip()
    # 既存記事で "Photorealistic" を含む ``` ブロックを拾うフォールバック
    for blk in re.findall(r"```\s*\n([^`]*?Photorealistic[^`]*?)\n```", text, re.DOTALL):
        return blk.strip()
    return None

def main():
    files = sorted(ARTICLES_DIR.glob("2026-*_note記事_*.md"))
    lines = [
        "# 全記事 サムネ用プロンプト一覧（iPhone用・コピペ用）",
        "",
        "各記事のサムネ生成プロンプトを集約。",
        "1. iPhone の ChatGPT/Gemini アプリで該当プロンプトを貼る → 画像生成",
        "2. 保存 → note アプリで該当記事を開く → ヘッダー画像差し替え → 更新",
        "",
        f"**収録数:** {len(files)}本（うちプロンプト同梱記事を抽出）",
        "",
        "---",
        "",
    ]
    n_with = 0
    for f in files:
        text = f.read_text(encoding="utf-8")
        title = extract_title(text)
        prompt = extract_thumb_prompt(text)
        if not prompt:
            continue
        n_with += 1
        date = f.name[:10]
        lines += [
            f"## [{date}] {title}",
            f"_ファイル: `{f.name}`_",
            "",
            "```",
            prompt,
            "```",
            "",
            "---",
            "",
        ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"書き出し: {OUT.relative_to(REPO)}")
    print(f"プロンプト収録: {n_with}本 / 全{len(files)}本")

if __name__ == "__main__":
    main()
