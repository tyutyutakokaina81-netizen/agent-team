"""
06_deliver.py — 納品準備・サマリ生成
念査済み成果物の納品用パッケージを作成し、納品文を生成する。
実際の送信は人手で行う（規約対応のため半自動運用）。
"""

import json
import os
import shutil
import urllib.request
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

DELIVERY_PROMPT = """
以下の作業完了情報をもとに、クラウドソーシングの納品メッセージを作成してください。

# 案件情報
タイトル: {title}
カテゴリ: {category}

# 作業結果
総件数: {total_rows}件
念査結果: {review_status}
ファイル名: {filename}

# 納品メッセージの条件
- 150〜200文字
- 作業完了の報告・件数・確認依頼を含む
- 丁寧かつ簡潔な日本語

納品メッセージのみ出力してください。
"""


def call_claude(prompt: str) -> str:
    if not ANTHROPIC_API_KEY:
        raise EnvironmentError("ANTHROPIC_API_KEY が設定されていません")

    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 512,
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


def run(job: dict, output_file: Path, review_result: dict) -> dict:
    # 納品パッケージフォルダを作成
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    pkg_dir = OUTPUT_DIR / f"{timestamp}_delivery_{job.get('platform', 'job')}"
    pkg_dir.mkdir(exist_ok=True)

    # 成果物をパッケージにコピー
    dest = pkg_dir / output_file.name
    shutil.copy2(output_file, dest)

    # 納品メッセージを生成
    review_status = "問題なし（全チェック通過）" if review_result.get("passed") else "要確認あり"
    prompt = DELIVERY_PROMPT.format(
        title=job.get("title", ""),
        category=job.get("category", ""),
        total_rows=review_result.get("total_rows", "?"),
        review_status=review_status,
        filename=output_file.name,
    )
    delivery_message = call_claude(prompt)

    # サマリをJSONで保存
    summary = {
        "job": job,
        "output_file": str(dest),
        "review_result": review_result,
        "delivery_message": delivery_message,
        "created_at": datetime.now().isoformat(),
    }
    (pkg_dir / "delivery_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 人間確認用表示
    print("\n" + "=" * 60)
    print("【納品準備完了】以下の内容で納品してください")
    print("=" * 60)
    print(f"案件: {job.get('title', '')}")
    print(f"URL: {job.get('url', '')}")
    print(f"添付ファイル: {dest}")
    print(f"\n納品メッセージ:\n{delivery_message}")
    print("=" * 60)
    print(f"[次のステップ] {job.get('platform', '')} にログインして手動納品してください")

    return summary


if __name__ == "__main__":
    print("使用方法: パイプラインから呼び出してください")
    print("  from pipeline.06_deliver import run")
    print("  run(job, output_file, review_result)")
