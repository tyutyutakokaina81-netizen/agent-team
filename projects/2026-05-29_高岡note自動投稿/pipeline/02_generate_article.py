"""
02_generate_article.py — 体験記事を生成（Claude API）

article_generation_prompt.md をテンプレに、トピック/切り口/日付を差し込んで
Claude に体験記事（YAMLフロントマター付きMarkdown）を1本生成させる。

必要: 環境変数 ANTHROPIC_API_KEY
"""

import os
import re
import datetime
from pathlib import Path

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

BASE = Path(__file__).resolve().parent.parent
PROMPT_FILE = BASE / "prompts" / "article_generation_prompt.md"
TOPIC_POOL = BASE / "prompts" / "topic_pool.md"
ARTICLES_DIR = BASE / "articles"
MODEL = os.environ.get("ARTICLE_MODEL", "claude-opus-4-8")


def topic_title(topic_id: str) -> str:
    """topic_pool.md の表からトピック名を引く（| ID | トピック | …）。"""
    text = TOPIC_POOL.read_text(encoding="utf-8")
    for line in text.splitlines():
        m = re.match(rf"\|\s*{re.escape(topic_id)}\s*\|\s*([^|]+?)\s*\|", line)
        if m:
            return m.group(1).strip()
    return topic_id


def build_prompt(topic_id: str, angle: str, date: str) -> str:
    tmpl = PROMPT_FILE.read_text(encoding="utf-8")
    topic = topic_title(topic_id)
    return (tmpl
            .replace("{{TOPIC_ID}}", topic_id)
            .replace("{{TOPIC}}", topic)
            .replace("{{ANGLE}}", angle)
            .replace("{{DATE}}", date))


def generate(topic_id: str, angle: str = "一人旅", date: str | None = None) -> Path:
    date = date or datetime.date.today().isoformat()
    if Anthropic is None:
        raise RuntimeError("anthropic 未インストール。requirements.txt を参照。")
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    prompt = build_prompt(topic_id, angle, date)
    msg = client.messages.create(
        model=MODEL,
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )
    body = msg.content[0].text

    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    out = ARTICLES_DIR / f"{date}_{topic_id}.md"
    out.write_text(body, encoding="utf-8")
    print(f"[article] saved: {out}")
    return out


if __name__ == "__main__":
    import sys
    tid = sys.argv[1] if len(sys.argv) > 1 else "F01"
    ang = sys.argv[2] if len(sys.argv) > 2 else "一人旅"
    generate(tid, ang)
