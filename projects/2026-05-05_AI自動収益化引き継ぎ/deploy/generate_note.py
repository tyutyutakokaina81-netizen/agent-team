"""note記事生成。

ANTHROPIC_API_KEY または OPENAI_API_KEY があればAPIで生成、無ければテンプレフォールバック。
日次コスト上限（既定 ¥100、AI_DAILY_BUDGET_JPY で上書き可）を超えるとフォールバック。

例:
    python3 generate_note.py "AI時代の地方暮らし"
    THEME="50代からの副業" python3 generate_note.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ai import call_llm  # noqa: E402

OUT = Path.home() / "ai-auto" / "outputs"

PROMPT_TEMPLATE = """あなたは日本語の発信者向けに、note記事を書くプロの編集者です。
テーマ「{theme}」について、以下の制約で本文を書いてください。

- 800〜1200字程度
- 導入／本文／まとめの3節
- 派手な煽りではなく、静かで誠実なトーン
- 富山・高岡などの地方都市、地方副業、AI時代の働き方の文脈を尊重
- マークダウン記法で見出し（##）を使う
- タイトル行は `# {theme}` で始める

本文のみを出力してください。
"""


def template(theme: str) -> str:
    return f"""# {theme}

## 導入
{theme} という言葉から、今あなたは何を思い浮かべるだろうか。
派手な成功談ではなく、もう少し静かな話をしたい。

## 本文
派手ではないが、確かに心を整えてくれる時間がある。
朝の空気、近所の道、季節の変化。
そういった『当たり前』こそが、これからの時代に強い武器になる。

地方都市の暮らしと、AI時代の働き方。
この二つを重ね合わせると、新しい『個人の収益化』が見えてくる。

## まとめ
- 派手さより継続
- 大きな計画より小さな公開
- 不安より一歩

今日も、ひとつ公開してみよう。
"""


def build(theme: str) -> str:
    text = call_llm(PROMPT_TEMPLATE.format(theme=theme))
    return text or template(theme)


def main() -> None:
    theme = sys.argv[1] if len(sys.argv) > 1 else os.environ.get(
        "THEME", "静かな地方都市で暮らすという贅沢"
    )
    OUT.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d_%H%M")
    safe_theme = theme.replace("/", "_").replace(" ", "_")
    path = OUT / f"{today}_note_{safe_theme}.md"
    path.write_text(build(theme), encoding="utf-8")
    print(f"生成完了: {path}")


if __name__ == "__main__":
    main()
