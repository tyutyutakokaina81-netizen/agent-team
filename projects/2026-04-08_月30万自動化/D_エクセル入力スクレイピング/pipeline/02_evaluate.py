"""
02_evaluate.py — 案件評価・選別
Claude API で案件文を読み、実行可能・採算合うか判定する。
"""

import json
import os
import urllib.request
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

EVAL_PROMPT = """
あなたはクラウドソーシングの案件を評価するAIです。
以下の案件情報を読み、JSON形式で評価結果を返してください。

# 案件情報
タイトル: {title}
URL: {url}
プラットフォーム: {platform}

# 評価基準
1. executable (bool): Claudeと Pythonで自動実行できるか
2. score (1-10): 採算・難易度・リスクの総合スコア
3. category: "excel_input" / "scraping" / "data_processing" / "other"
4. estimated_price_jpy: 想定単価（円）
5. reason: 採点理由（1文）
6. recommend (bool): 応募推奨か

# 出力形式（JSONのみ、説明不要）
{{"executable": true, "score": 7, "category": "excel_input",
  "estimated_price_jpy": 3000, "reason": "...", "recommend": true}}
"""


def call_claude(prompt: str) -> str:
    """Claude API を直接呼び出す"""
    if not ANTHROPIC_API_KEY:
        raise EnvironmentError("ANTHROPIC_API_KEY が設定されていません")

    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 256,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        body = json.loads(res.read().decode("utf-8"))
    return body["content"][0]["text"]


def evaluate_job(job: dict) -> dict:
    prompt = EVAL_PROMPT.format(
        title=job.get("title", ""),
        url=job.get("url", ""),
        platform=job.get("platform", ""),
    )
    try:
        raw = call_claude(prompt)
        # JSONブロックを抽出
        start = raw.find("{")
        end = raw.rfind("}") + 1
        result = json.loads(raw[start:end])
        return {**job, **result}
    except Exception as e:
        print(f"[WARN] evaluate_job failed: {e}")
        return {**job, "executable": False, "score": 0, "recommend": False}


def run(jobs: list[dict] | None = None):
    if jobs is None:
        # 最新の検索結果ファイルを読み込む
        files = sorted(OUTPUT_DIR.glob("*_jobs.json"))
        if not files:
            print("[ERROR] 案件ファイルが見つかりません。01_search.py を先に実行してください")
            return []
        jobs = json.loads(files[-1].read_text(encoding="utf-8"))

    print(f"[評価開始] {len(jobs)}件")
    evaluated = [evaluate_job(j) for j in jobs]

    # 推奨案件のみ抽出・スコア降順
    recommended = sorted(
        [j for j in evaluated if j.get("recommend")],
        key=lambda x: x.get("score", 0),
        reverse=True,
    )

    from datetime import datetime
    out_path = OUTPUT_DIR / f"{datetime.now().strftime('%Y-%m-%d_%H%M')}_evaluated.json"
    out_path.write_text(
        json.dumps(evaluated, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[完了] 推奨: {len(recommended)}件 / 全{len(evaluated)}件 → {out_path}")
    return recommended


if __name__ == "__main__":
    run()
