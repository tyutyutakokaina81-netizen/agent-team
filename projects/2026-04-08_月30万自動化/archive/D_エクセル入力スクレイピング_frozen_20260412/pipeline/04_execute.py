"""
04_execute.py — 作業実行
エクセルデータ入力 または Webスクレイピングをカテゴリに応じて実行する。
"""

import csv
import json
import os
import urllib.request
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


# ─────────────────────────────────────────────
# Excel入力系
# ─────────────────────────────────────────────

def execute_excel_input(job: dict, source_data: list[dict], template_path: str) -> Path:
    """
    source_data: 入力するデータのリスト（[{"col_a": "val", ...}, ...]）
    template_path: ベースとなるExcelファイルのパス
    """
    try:
        import openpyxl
    except ImportError:
        raise ImportError("pip install openpyxl が必要です")

    wb = openpyxl.load_workbook(template_path)
    ws = wb.active

    # ヘッダー行を1行目と仮定してデータを書き込む
    headers = [cell.value for cell in ws[1]]
    for row_idx, record in enumerate(source_data, start=2):
        for col_idx, header in enumerate(headers, start=1):
            ws.cell(row=row_idx, column=col_idx, value=record.get(header, ""))

    out_path = OUTPUT_DIR / f"{datetime.now().strftime('%Y-%m-%d_%H%M')}_result.xlsx"
    wb.save(out_path)
    print(f"[Excel入力完了] {len(source_data)}行 → {out_path}")
    return out_path


# ─────────────────────────────────────────────
# Webスクレイピング系
# ─────────────────────────────────────────────

def generate_scraping_script(job: dict) -> str:
    """Claude に案件情報を渡してスクレイピングスクリプトを生成させる"""
    if not ANTHROPIC_API_KEY:
        raise EnvironmentError("ANTHROPIC_API_KEY が設定されていません")

    prompt = f"""
以下のクラウドソーシング案件の要件に合わせたPythonスクレイピングスクリプトを生成してください。

# 案件タイトル
{job.get("title", "")}

# 要件
- urllib と html.parser のみ使用（外部ライブラリ不使用）
- 結果をCSV（utf-8-sig）で output.csv に保存
- エラーハンドリング含む
- main() 関数を定義してスクリプト末尾で呼び出す

Pythonコードのみ出力してください（説明不要）。
"""
    payload = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 2048,
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
    with urllib.request.urlopen(req, timeout=60) as res:
        body = json.loads(res.read().decode("utf-8"))
    return body["content"][0]["text"]


def execute_scraping(job: dict) -> Path:
    """スクレイピングスクリプトを生成して実行する"""
    import subprocess
    import tempfile

    script_code = generate_scraping_script(job)

    # コードブロック除去
    if "```python" in script_code:
        script_code = script_code.split("```python")[1].split("```")[0].strip()
    elif "```" in script_code:
        script_code = script_code.split("```")[1].split("```")[0].strip()

    # 一時ファイルに保存して実行
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(script_code)
        tmp_path = f.name

    out_csv = OUTPUT_DIR / f"{datetime.now().strftime('%Y-%m-%d_%H%M')}_scraping.csv"
    result = subprocess.run(
        ["python3", tmp_path],
        capture_output=True, text=True, timeout=120,
        cwd=str(OUTPUT_DIR),
    )
    Path(tmp_path).unlink(missing_ok=True)

    if result.returncode != 0:
        raise RuntimeError(f"スクレイピング失敗:\n{result.stderr}")

    # output.csv を最終ファイル名にリネーム
    tmp_csv = OUTPUT_DIR / "output.csv"
    if tmp_csv.exists():
        tmp_csv.rename(out_csv)

    print(f"[スクレイピング完了] → {out_csv}")
    return out_csv


def run(job: dict, **kwargs):
    category = job.get("category", "")
    if category == "excel_input":
        source_data = kwargs.get("source_data", [])
        template_path = kwargs.get("template_path", "")
        return execute_excel_input(job, source_data, template_path)
    elif category == "scraping":
        return execute_scraping(job)
    else:
        print(f"[SKIP] 未対応カテゴリ: {category}")
        return None


if __name__ == "__main__":
    # テスト用サンプル
    sample_job = {
        "title": "テスト：サンプルサイトから商品名と価格を収集",
        "category": "scraping",
        "url": "",
    }
    run(sample_job)
