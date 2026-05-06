"""YouTube Shorts 台本生成（API不要）。

タイトル・台本・概要欄・ハッシュタグ・サムネ文言・映像生成プロンプトを一括出力。
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

BASE = Path.home() / "ai-auto"
OUT = BASE / "outputs"
OUT.mkdir(parents=True, exist_ok=True)


def build(theme: str) -> str:
    return f"""# YouTube Shorts 台本

## タイトル
{theme}

## 30〜60秒台本
都会の速さから少し離れると、
見えてくるものがあります。

朝の空気。
静かな道。
季節の匂い。

富山や高岡の暮らしは、
派手ではありません。

でも、
心が整う時間があります。

何もないようで、
実は一番ぜいたくなのかもしれません。

## 概要欄
富山・高岡の静かな暮らしを切り取った1分。
派手さではなく、整う時間を。
チャンネル登録で、地方の小さな景色をお届けします。

## ハッシュタグ
#富山 #高岡 #地方暮らし #日本の暮らし #shorts #slowlife #japan

## サムネイル文言
「派手じゃない、でも整う」

## 映像生成プロンプト（Kling AI / Sora / HeyGen 共通）
cinematic, realistic, Japanese local atmosphere,
Toyama / Takaoka city, quiet streets in early morning,
soft natural light, gentle pacing, short vertical 9:16 video,
no fake text signs, no unreadable captions, no logos.
"""


def main() -> None:
    theme = sys.argv[1] if len(sys.argv) > 1 else "地方都市で暮らすという贅沢"
    today = datetime.now().strftime("%Y-%m-%d_%H%M")
    path = OUT / f"{today}_youtube_short.md"
    path.write_text(build(theme), encoding="utf-8")
    print(f"生成完了: {path}")


if __name__ == "__main__":
    main()
