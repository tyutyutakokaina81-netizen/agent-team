"""LLM呼び出しの薄いラッパ。

- ANTHROPIC_API_KEY があれば anthropic SDK を、無ければ OPENAI_API_KEY + openai SDK を使う
- どちらも無い／SDK未インストール／日次コスト上限超過 の場合は None を返す
- 呼び出し成功時は概算コストを cost_log.json に追記

呼び出し側は `result = call_llm(prompt) or fallback_template(...)` の形で使う。
"""
from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

BASE = Path.home() / "ai-auto"
COST_LOG = BASE / ".cost_log.json"

DAILY_BUDGET_JPY = int(os.environ.get("AI_DAILY_BUDGET_JPY", "100"))
USD_TO_JPY = 150
ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
ANTHROPIC_INPUT_USD_PER_MTOK = 1.00
ANTHROPIC_OUTPUT_USD_PER_MTOK = 5.00
OPENAI_MODEL = "gpt-4o-mini"
OPENAI_INPUT_USD_PER_MTOK = 0.15
OPENAI_OUTPUT_USD_PER_MTOK = 0.60


def _today_spent_jpy() -> int:
    if not COST_LOG.exists():
        return 0
    try:
        log = json.loads(COST_LOG.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 0
    return int(log.get(str(date.today()), 0))


def _record_jpy(amount: int) -> None:
    log = {}
    if COST_LOG.exists():
        try:
            log = json.loads(COST_LOG.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            log = {}
    key = str(date.today())
    log[key] = int(log.get(key, 0)) + int(amount)
    COST_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")


def _budget_remaining() -> int:
    return max(0, DAILY_BUDGET_JPY - _today_spent_jpy())


def _call_anthropic(prompt: str, max_tokens: int) -> tuple[str, int] | None:
    try:
        from anthropic import Anthropic
    except ImportError:
        return None
    client = Anthropic()
    msg = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
    in_tok = msg.usage.input_tokens
    out_tok = msg.usage.output_tokens
    usd = (in_tok * ANTHROPIC_INPUT_USD_PER_MTOK + out_tok * ANTHROPIC_OUTPUT_USD_PER_MTOK) / 1_000_000
    return text, int(usd * USD_TO_JPY) + 1


def _call_openai(prompt: str, max_tokens: int) -> tuple[str, int] | None:
    try:
        from openai import OpenAI
    except ImportError:
        return None
    client = OpenAI()
    rsp = client.chat.completions.create(
        model=OPENAI_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    text = rsp.choices[0].message.content or ""
    in_tok = rsp.usage.prompt_tokens
    out_tok = rsp.usage.completion_tokens
    usd = (in_tok * OPENAI_INPUT_USD_PER_MTOK + out_tok * OPENAI_OUTPUT_USD_PER_MTOK) / 1_000_000
    return text, int(usd * USD_TO_JPY) + 1


def call_llm(prompt: str, *, max_tokens: int = 1500) -> str | None:
    if _budget_remaining() <= 0:
        return None
    if os.environ.get("ANTHROPIC_API_KEY"):
        result = _call_anthropic(prompt, max_tokens)
    elif os.environ.get("OPENAI_API_KEY"):
        result = _call_openai(prompt, max_tokens)
    else:
        return None
    if result is None:
        return None
    text, cost_jpy = result
    _record_jpy(cost_jpy)
    return text
