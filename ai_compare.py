#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI比較実行スクリプト
- 事業採算性プロンプトを OpenAI / Claude に送る
- 回答を markdown で保存する
- 後で比較しやすいようにタイムスタンプ付きで出力する

事前準備:
1) pip install requests
2) 環境変数を設定
   export OPENAI_API_KEY="..."
   export ANTHROPIC_API_KEY="..."

実行:
   python3 ai_compare.py
"""

from __future__ import annotations

import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

import requests


# =========================
# 設定
# =========================

OUTPUT_DIR = Path(__file__).parent / "ai_outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

OPENAI_MODEL = "gpt-4o"          # gpt-5.4は未存在のためgpt-4oを使用
CLAUDE_MODEL = "claude-opus-4-6"

TIMEOUT_SECONDS = 180


PROMPT = """あなたは「事業投資の最終審査官兼、実務設計コンサルタント」です。
理想論は禁止、必ず現実ベース・数値ベースで回答してください。

私は現在、クラウドワークス等のプラットフォームを活用し、AI（Claude / ChatGPT / Python）による自動化を前提とした収益モデルを検討しています。

ただし、以下の制約があります。

【前提条件】
・初期投資：最大20万円（厳守）
・在庫は持たない
・地方在住（営業リソースほぼゼロ）
・使用デバイス：iPhone / Mac
・目標：6ヶ月以内に月30万円の安定収益
・最終目標：できる限り「全自動」に近づける（ただし規約違反は避ける）

【重要前提】
私は「完全自動化」を目指していますが、
現実的に不可能であれば「どこまで自動化できるか」を正直に提示してください。

【評価・提案タスク】
① この条件で「月30万円＋高い自動化率」は現実的か？
→ Yes / Noで即答し、その理由を明確に説明

② 成立する場合：
・最も成功確率の高いビジネスモデルを3つ提示
・それぞれの「自動化可能領域」と「人間がやるべき領域」を明確に分解
・実際の作業フロー（案件取得〜納品まで）を詳細に説明

③ 各モデルについて：
・初期費用の具体内訳（20万円以内で厳密に）
・月30万円到達までのロードマップ（1ヶ月目〜6ヶ月目）
・案件単価・件数・作業時間のリアルな数値試算

④ 「全自動」に最も近づける構成を1つ選び、
・システム構成（Claude / ChatGPT / Python / 外注などの役割分担）
・自動化フロー図（文章でOK）
・どこがボトルネックになるか

⑤ リスク分析（必須）：
・規約違反やアカウント停止の具体トリガー
・AI自動化が検知されるパターン
・収益が崩壊するシナリオ

⑥ 最重要：
「勝てる人の特徴」と「確実に失敗する人の特徴」を明確に分ける

⑦ 最終判断：
この条件に対して「Go / No-Go」を必ず断定し、
その理由を一言でまとめる

【禁止事項】
・抽象論
・精神論
・根拠のない楽観論

必ず「実務レベルでそのまま使える内容」で回答してください。
"""


# =========================
# 共通ユーティリティ
# =========================

def now_str() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def save_markdown(name: str, content: str) -> Path:
    path = OUTPUT_DIR / f"{now_str()}_{name}.md"
    path.write_text(content, encoding="utf-8")
    return path


def extract_openai_text(data: dict) -> str:
    if isinstance(data.get("output_text"), str):
        return data["output_text"]
    output = data.get("output", [])
    parts: list[str] = []
    for item in output:
        content = item.get("content", [])
        for c in content:
            if c.get("type") in ("output_text", "text"):
                text = c.get("text")
                if isinstance(text, str):
                    parts.append(text)
    if parts:
        return "\n".join(parts).strip()
    # Chat Completions API フォールバック
    choices = data.get("choices", [])
    if choices:
        return choices[0].get("message", {}).get("content", "")
    return json.dumps(data, ensure_ascii=False, indent=2)


def extract_claude_text(data: dict) -> str:
    content = data.get("content", [])
    parts: list[str] = []
    for item in content:
        if item.get("type") == "text":
            text = item.get("text")
            if isinstance(text, str):
                parts.append(text)
    if parts:
        return "\n".join(parts).strip()
    return json.dumps(data, ensure_ascii=False, indent=2)


# =========================
# API呼び出し
# =========================

def call_openai(prompt: str, model: str = OPENAI_MODEL) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY が設定されていません")

    # Chat Completions API（互換性が高い）
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4000,
    }
    response = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    return extract_openai_text(response.json())


def call_claude(prompt: str, model: str = CLAUDE_MODEL) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY が設定されていません")

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": 4000,
        "messages": [{"role": "user", "content": prompt}],
    }
    response = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    return extract_claude_text(response.json())


# =========================
# 実行
# =========================

def main() -> None:
    print("AI比較を開始します...\n")
    results: list[tuple[str, Optional[str], Optional[str]]] = []

    # OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            print(f"OpenAI（{OPENAI_MODEL}）に送信中...")
            text = call_openai(PROMPT)
            path = save_markdown("openai", text)
            results.append(("OpenAI", str(path), None))
            print(f"✅ 保存完了: {path}\n")
        except Exception as e:
            results.append(("OpenAI", None, str(e)))
            print(f"❌ OpenAI エラー: {e}\n")
    else:
        print("⚠️  OPENAI_API_KEY 未設定 — スキップ\n")

    time.sleep(1)

    # Claude
    claude_key = os.getenv("ANTHROPIC_API_KEY")
    if claude_key:
        try:
            print(f"Claude（{CLAUDE_MODEL}）に送信中...")
            text = call_claude(PROMPT)
            path = save_markdown("claude", text)
            results.append(("Claude", str(path), None))
            print(f"✅ 保存完了: {path}\n")
        except Exception as e:
            results.append(("Claude", None, str(e)))
            print(f"❌ Claude エラー: {e}\n")
    else:
        print("⚠️  ANTHROPIC_API_KEY 未設定 — スキップ\n")

    # サマリー
    summary_lines = ["# AI比較実行結果", "", f"実行日時: {datetime.now().isoformat()}", ""]
    for name, path, error in results:
        summary_lines.append(f"## {name}")
        if path:
            summary_lines.append(f"- 保存先: `{path}`")
        if error:
            summary_lines.append(f"- エラー: `{error}`")
        summary_lines.append("")

    summary_path = save_markdown("summary", "\n".join(summary_lines))
    print(f"サマリー: {summary_path}")
    print("完了")


if __name__ == "__main__":
    main()
