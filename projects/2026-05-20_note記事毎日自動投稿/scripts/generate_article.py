"""
generate_article.py — Anthropic APIで「現在の高岡」をテーマにした日次note記事を自動生成

実行：
    ANTHROPIC_API_KEY=... python generate_article.py

出力：
    CMO/outputs/YYYY-MM-DD_<slug>_note記事.md

ロジック：
- 文体ガイド (assets/style_guide.md) を読み込んでシステムプロンプトに含める
- 過去の記事タイトル一覧を読み込んで重複テーマを避ける
- claude-sonnet-4-6 で生成（コスト最適化、必要に応じてopusに切替）
"""

from __future__ import annotations

import os
import re
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PROJECT_DIR = Path(__file__).resolve().parents[1]
CMO_OUTPUTS = REPO_ROOT / "CMO" / "outputs"
STYLE_GUIDE = PROJECT_DIR / "assets" / "style_guide.md"

DEFAULT_STYLE_GUIDE = """\
# 文体ガイド（暫定版）

参照元：note.com/safe_canna441（てつさん）

## トーン
- 一人称：私 / 「〜です・ます」と「〜なんですよね」の混在
- 問いかけ調を多用（〜だろうか／〜じゃないか）
- 短い段落、改行を多めに

## 構成
- 出だしは日常の一コマから（時刻・場所・身体感覚）
- 中盤で「気づき」や「考察」を1〜2点
- 結びは「また書きます」「今日も読んでくれてありがとう」など穏やかに

## NG
- 説教調・啓蒙調・煽り
- 数字や成果のアピール
- ハッシュタグの羅列
"""


THEMES_HINT = [
    "高岡の朝の風景",
    "雨晴海岸の天気の変化",
    "金屋町の鋳物工房の音",
    "瑞龍寺の早朝拝観",
    "山町筋の土蔵造り",
    "藤子・F・不二雄ミュージアムの帰り道",
    "氷見の魚屋さんとの会話",
    "高岡駅前のロータリーで見かけた風景",
    "ホタルイカの終わり、白エビの始まり",
    "新緑から夏色に変わる立山",
    "近所の喫茶店でぼんやりした午後",
    "車を持たない高岡生活の機微",
    "古本屋・本屋さんの平日",
    "田んぼに水が張られた季節",
    "風の強い日の富山湾",
]


def load_style_guide() -> str:
    if STYLE_GUIDE.exists():
        return STYLE_GUIDE.read_text(encoding="utf-8")
    return DEFAULT_STYLE_GUIDE


def list_past_titles() -> list[str]:
    titles: list[str] = []
    if not CMO_OUTPUTS.exists():
        return titles
    for p in sorted(CMO_OUTPUTS.glob("*_note記事.md")):
        text = p.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            if line.startswith("# "):
                titles.append(line[2:].strip())
                break
    return titles


def pick_theme(past_titles: list[str]) -> str:
    past_joined = " ".join(past_titles)
    for theme in THEMES_HINT:
        keyword = theme.split("の")[0]
        if keyword and keyword in past_joined:
            continue
        return theme
    return THEMES_HINT[date.today().toordinal() % len(THEMES_HINT)]


def slugify(title: str) -> str:
    s = re.sub(r"[\s　]+", "_", title.strip())
    s = re.sub(r"[、。！？!?,.「」『』\(\)（）]", "", s)
    return s[:30] or "記事"


def generate_with_claude(style_guide: str, past_titles: list[str], theme: str) -> str:
    try:
        from anthropic import Anthropic
    except ImportError:
        print("[ERROR] anthropic SDKが未インストール。`pip install anthropic`")
        sys.exit(3)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY が未設定")
        sys.exit(4)

    client = Anthropic(api_key=api_key)

    system = (
        "あなたは富山県高岡市在住の生活者エッセイスト「てつ」さんです。"
        "note.com/safe_canna441 に毎日1記事を投稿しています。"
        "以下の文体ガイドに厳密に従って、本日の記事を書いてください。\n\n"
        + style_guide
    )

    past_block = "\n".join(f"- {t}" for t in past_titles[-20:]) if past_titles else "（なし）"

    user_prompt = f"""\
今日のテーマ：**{theme}**

【遵守ルール】
1. タイトルは H1 (`# タイトル`) で1行だけ
2. 本文は 1500〜2500字
3. 「現在の高岡」の暮らしを、その場で観察したかのような具体性で書く
4. 数字・固有名詞は分かる範囲で（無理に作らない）
5. 結びは穏やかに（「また書きます」「今日も読んでくれてありがとう」等）
6. 過去のタイトルと重複しない題材を選ぶ

【過去のタイトル】
{past_block}

【出力形式】
Markdownのみ（前置きや解説は一切不要）。"""

    print(f"[INFO] テーマ: {theme}")
    print("[INFO] Claudeで記事を生成中...")

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text = ""
    for block in message.content:
        if getattr(block, "type", None) == "text":
            text += block.text
    return text.strip()


def main() -> int:
    style_guide = load_style_guide()
    past_titles = list_past_titles()
    theme = pick_theme(past_titles)

    article_md = generate_with_claude(style_guide, past_titles, theme)

    title = "記事"
    for line in article_md.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break

    today = date.today().strftime("%Y-%m-%d")
    out_path = CMO_OUTPUTS / f"{today}_{slugify(title)}_note記事.md"
    CMO_OUTPUTS.mkdir(parents=True, exist_ok=True)
    out_path.write_text(article_md + "\n", encoding="utf-8")

    print(f"[OK] 記事を生成: {out_path.relative_to(REPO_ROOT)}")
    print(f"[OK] タイトル: {title}")
    print(f"[OK] 文字数: {len(article_md)}")
    print(str(out_path.relative_to(REPO_ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
