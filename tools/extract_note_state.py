"""note の storageState を mac でローカル取得して base64 化するスクリプト。

GitHub Actions の Secret `NOTE_STORAGE_STATE` に登録するための前準備。
mac でブラウザを起動 → 手動ログイン → Cookie/localStorage を JSON にエクスポート →
base64 化して `note_state.b64` を出力。

使い方（mac で1回・失効時は再実行）:
    pip install playwright
    playwright install chromium
    python3 tools/extract_note_state.py
    # → 表示された base64 文字列を GitHub Settings → Secrets で
    #   NOTE_STORAGE_STATE に登録
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path

OUT_JSON = Path("note_state.json")
OUT_B64 = Path("note_state.b64")


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright 未インストール")
        print("  pip install playwright && playwright install chromium")
        return 1

    print("=" * 60)
    print("  note storageState 取得")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="ja-JP",
        )
        page = ctx.new_page()
        page.goto("https://note.com/login")

        print("\n→ ブラウザで note にログインしてください")
        print("  ログイン完了したらこのターミナルで Enter を押す:")
        input()

        ctx.storage_state(path=str(OUT_JSON))
        browser.close()

    raw = OUT_JSON.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    OUT_B64.write_text(b64)

    print()
    print("=" * 60)
    print(f"  ✓ 保存完了")
    print("=" * 60)
    print(f"\nファイル:")
    print(f"  - {OUT_JSON.resolve()}（参考・gitignore推奨）")
    print(f"  - {OUT_B64.resolve()}（GitHub Secret 用）")
    print()
    print("次の手順:")
    print(f"  1. {OUT_B64.name} の中身を全選択コピー")
    print(f"     cat {OUT_B64} | pbcopy   # mac の場合")
    print(f"  2. GitHub → Settings → Secrets and variables → Actions")
    print(f"  3. New repository secret")
    print(f"     Name:   NOTE_STORAGE_STATE")
    print(f"     Secret: クリップボードからペースト")
    print(f"  4. 注意: ローカルの note_state.json と note_state.b64 は")
    print(f"     コミットせず、登録後に削除してください")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
