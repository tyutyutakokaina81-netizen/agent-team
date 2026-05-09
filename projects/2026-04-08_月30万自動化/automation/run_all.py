"""
run_all.py — Vol.2/3 を note 公開し、X に 3 つのツイートを順次投稿する。

実行方法:
  python3 run_all.py

前提:
  - 00_session_setup.py で note と X のセッション保存済み
  - publish_note.py / post_x.py が動作確認済み

順序:
  1. Vol.2 公開
  2. Vol.3 公開
  3. ツイート 1（Vol.2 告知）
  4. 30 秒待機
  5. ツイート 2（Vol.3 告知）
  6. 30 秒待機
  7. ツイート 3（シリーズ告知）
"""

import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from _browser import _check_chrome_not_running  # noqa: E402


def run(cmd: list[str], label: str):
    print(f"\n{'═' * 60}")
    print(f"  ▶ {label}")
    print(f"  command: {' '.join(cmd)}")
    print("═" * 60)
    result = subprocess.run(cmd, cwd=str(HERE))
    if result.returncode != 0:
        print(f"\n[ERROR] {label} 失敗（returncode={result.returncode}）")
        print("以降のステップも同じ原因で失敗する可能性が高いため、中止します。")
        sys.exit(1)


def main():
    print("─" * 60)
    print("  全自動公開シーケンス")
    print("  Vol.2/3 note 公開 → X 告知 3 ツイート")
    print("─" * 60)

    # 起動チェックを最初に1回だけ行う
    _check_chrome_not_running()

    py = sys.executable

    run([py, "publish_note.py", "vol2"], "STEP 1/5: Vol.2 を note 公開")
    run([py, "publish_note.py", "vol3"], "STEP 2/5: Vol.3 を note 公開")
    for i in range(1, 4):
        run([py, "post_x.py", str(i)], f"STEP {2 + i}/5: X ツイート {i}")
        if i < 3:
            print("  → 30 秒待機（連投回避）")
            time.sleep(30)

    print("\n" + "═" * 60)
    print("  ✅ 全シーケンス完了")
    print("═" * 60)


if __name__ == "__main__":
    main()
