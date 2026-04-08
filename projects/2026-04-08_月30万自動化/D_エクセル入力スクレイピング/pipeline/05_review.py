"""
05_review.py — 念査（品質チェック）
Claude が成果物を自己レビューし、問題があれば報告・自動修正する。
"""

import csv
import json
import os
import urllib.request
from pathlib import Path

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

REVIEW_PROMPT = """
あなたはデータ品質チェックの専門家です。
以下の成果物データをレビューして、問題点を報告してください。

# 成果物の種類
{file_type}

# データサンプル（先頭20件）
{sample}

# チェック項目
1. 空欄・nullが不自然に多い列はないか
2. 明らかなフォーマットエラー（日付・電話番号・メールなど）
3. 重複データの有無
4. 文字化け・エンコード問題

# 出力形式（JSONのみ）
{{
  "passed": true/false,
  "total_rows": 件数,
  "issues": [
    {{"type": "問題種別", "column": "列名", "detail": "詳細", "severity": "high/medium/low"}}
  ],
  "summary": "全体評価コメント"
}}
"""


def call_claude(prompt: str) -> str:
    if not ANTHROPIC_API_KEY:
        raise EnvironmentError("ANTHROPIC_API_KEY が設定されていません")

    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 1024,
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


def review_csv(file_path: Path) -> dict:
    rows = []
    with open(file_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            rows.append(row)

    sample = json.dumps(rows[:20], ensure_ascii=False, indent=2)
    prompt = REVIEW_PROMPT.format(file_type="CSV", sample=sample)

    try:
        raw = call_claude(prompt)
        start = raw.find("{")
        end = raw.rfind("}") + 1
        result = json.loads(raw[start:end])
        result["total_rows"] = len(rows)
        return result
    except Exception as e:
        return {"passed": False, "error": str(e), "total_rows": len(rows)}


def review_excel(file_path: Path) -> dict:
    try:
        import openpyxl
    except ImportError:
        raise ImportError("pip install openpyxl が必要です")

    wb = openpyxl.load_workbook(file_path)
    ws = wb.active
    headers = [cell.value for cell in ws[1]]
    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        rows.append(dict(zip(headers, row)))

    sample = json.dumps(rows[:20], ensure_ascii=False, indent=2, default=str)
    prompt = REVIEW_PROMPT.format(file_type="Excel", sample=sample)

    try:
        raw = call_claude(prompt)
        start = raw.find("{")
        end = raw.rfind("}") + 1
        result = json.loads(raw[start:end])
        result["total_rows"] = len(rows)
        return result
    except Exception as e:
        return {"passed": False, "error": str(e), "total_rows": len(rows)}


def run(file_path: str | Path) -> dict:
    file_path = Path(file_path)
    print(f"[念査開始] {file_path.name}")

    if file_path.suffix == ".csv":
        result = review_csv(file_path)
    elif file_path.suffix in (".xlsx", ".xls"):
        result = review_excel(file_path)
    else:
        result = {"passed": False, "error": f"未対応のファイル形式: {file_path.suffix}"}

    # 結果表示
    passed = result.get("passed", False)
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"[念査結果] {status} | {result.get('total_rows', '?')}行")

    issues = result.get("issues", [])
    if issues:
        print("[問題点]")
        for issue in issues:
            sev = issue.get("severity", "")
            print(f"  [{sev.upper()}] {issue.get('column', '')} - {issue.get('detail', '')}")

    print(f"[評価] {result.get('summary', '')}")
    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        run(sys.argv[1])
    else:
        print("使用方法: python 05_review.py <ファイルパス>")
