"""
06_deliver.py — 納品準備・サマリ生成
念査済み成果物の納品用パッケージを作成し、納品文を生成する。
実際の送信は人手で行う（規約対応のため半自動運用）。

注: 有料 API は使用しない。完全テンプレートで動作する。
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "outputs"


def _template_delivery_message(job: dict, total_rows, filename: str, passed: bool) -> str:
    """テンプレート納品メッセージ（評価★4獲得を狙う構成）"""
    title_short = job.get("title", "")[:30]
    rows_label = f"{total_rows}件" if isinstance(total_rows, int) else "ご指定件数"
    quality_line = (
        "全項目チェック済みで問題は確認されておりません。"
        if passed else
        "念査時に軽微な確認点がございましたので、ご一読いただけますと幸いです。"
    )
    return (
        f"お世話になっております。「{title_short}」の作業が完了しましたので、"
        f"成果物（{filename}）を添付して納品いたします。\n\n"
        f"作業件数：{rows_label}。{quality_line}"
        f"内容ご確認のうえ、ご不明点・修正のご要望がございましたらお気軽にお知らせください。"
        "次回以降のご依頼にも継続して対応可能ですので、よろしくお願いいたします。"
    )


def run(job: dict, output_file: Path, review_result: dict) -> dict:
    # 納品パッケージフォルダを作成
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    pkg_dir = OUTPUT_DIR / f"{timestamp}_delivery_{job.get('platform', 'job')}"
    pkg_dir.mkdir(exist_ok=True)

    # 成果物をパッケージにコピー
    dest = pkg_dir / output_file.name
    shutil.copy2(output_file, dest)

    # 納品メッセージを生成（テンプレート）
    delivery_message = _template_delivery_message(
        job,
        review_result.get("total_rows", "?"),
        output_file.name,
        bool(review_result.get("passed")),
    )

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
