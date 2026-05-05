"""有料note記事生成（テンプレート版）。

無料パート＋有料パート＋導入文＋英語版＋SNS導線文をまとめて生成する。
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

BASE = Path.home() / "ai-auto"
OUT = BASE / "outputs"
OUT.mkdir(parents=True, exist_ok=True)


def build(theme: str, price: int = 2980) -> str:
    return f"""# 有料note：{theme}（¥{price}）

## 無料パート（流入用）
{theme} について、まず誰でも実践できる前提を共有します。
派手な裏技はありません。地味で、しかし効きます。

ここまでは無料公開です。続きは有料パートでまとめてお渡しします。

----

## 有料パート（ここから¥{price}）

### 1. 結論
{theme} のコアは『毎日小さく出す』ことに尽きます。

### 2. 手順
1. テーマを1つに絞る
2. 30分以内に書き切る
3. 公開前に1回だけ読み直す
4. 公開
5. 翌日また書く

### 3. テンプレート
- 導入：「あなたは今こう感じていないか？」
- 本文：体験＋気づき＋一般化
- 結び：行動を1つだけ提案

### 4. よくある失敗
- 完璧主義で公開しない
- 毎日テーマを変える
- 反応に振り回される

### 5. 30日チェックリスト
- 毎日1本公開できたか
- 有料記事を週1本作れたか
- SNSへ導線を貼ったか

----

## 購入したくなる導入文（X / Threads 用）
{theme} について、無料部分だけでも今日の一歩は踏み出せます。
本気で30日続けたい方向けに、有料パートでテンプレと失敗例まで全部公開しました。

## 英語版（要約）
{theme}: A 30-day quiet method for steady output.
No tricks, just a small daily publish.

## SNS導線文（X）
今日のnoteを公開しました。
{theme}について、毎日続けるための型を書いています。
よければ覗いてみてください。
"""


def main() -> None:
    theme = sys.argv[1] if len(sys.argv) > 1 else "AI時代の地方副業を続ける小さな型"
    price = int(sys.argv[2]) if len(sys.argv) > 2 else 2980
    today = datetime.now().strftime("%Y-%m-%d_%H%M")
    safe_theme = theme.replace("/", "_").replace(" ", "_")
    path = OUT / f"{today}_paid_note_{safe_theme}.md"
    path.write_text(build(theme, price), encoding="utf-8")
    print(f"生成完了: {path}")


if __name__ == "__main__":
    main()
