"""
run_pipeline.py — パイプライン一括実行
① 検索 → ② 評価 → ③ 応募文生成（確認待ち） まで自動実行する。
④ 実行・⑤ 念査・⑥ 納品は受注後に手動トリガーで実行する。
"""

import sys
from pathlib import Path

# パイプラインモジュールを同ディレクトリから読み込む
sys.path.insert(0, str(Path(__file__).parent))

from importlib import import_module

search   = import_module("01_search")
evaluate = import_module("02_evaluate")
apply    = import_module("03_apply")


def run_search_to_apply():
    """検索 → 評価 → 応募文生成（確認待ち）"""
    print("\n=== STEP 1: 案件検索 ===")
    jobs = search.run()

    if not jobs:
        print("[中断] 案件が見つかりませんでした")
        return

    print(f"\n=== STEP 2: 案件評価（{len(jobs)}件） ===")
    recommended = evaluate.run(jobs)

    if not recommended:
        print("[中断] 推奨案件がありませんでした")
        return

    print(f"\n=== STEP 3: 応募文生成（{len(recommended)}件） ===")
    apply.run(recommended)

    print("\n=== 完了 ===")
    print("上記の応募文を確認し、各プラットフォームから手動で送信してください。")
    print("受注後は 04_execute.py → 05_review.py → 06_deliver.py を実行してください。")


def run_execute_to_deliver(job: dict, **kwargs):
    """受注後：実行 → 念査 → 納品準備"""
    execute  = import_module("04_execute")
    review   = import_module("05_review")
    deliver  = import_module("06_deliver")

    print("\n=== STEP 4: 作業実行 ===")
    output_file = execute.run(job, **kwargs)
    if not output_file:
        print("[中断] 作業実行に失敗しました")
        return

    print("\n=== STEP 5: 念査 ===")
    review_result = review.run(output_file)

    if not review_result.get("passed"):
        print("[警告] 念査でNGが検出されました。内容を確認してください。")
        issues = review_result.get("issues", [])
        high = [i for i in issues if i.get("severity") == "high"]
        if high:
            print("[中断] 重大な問題があるため納品を停止します。手動修正後に再実行してください。")
            return

    print("\n=== STEP 6: 納品準備 ===")
    deliver.run(job, output_file, review_result)


if __name__ == "__main__":
    # デフォルトは検索〜応募文生成
    run_search_to_apply()
