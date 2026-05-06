"""README.md の KPI セクションを最新値で書き換える。

`<!-- KPI:START -->` ... `<!-- KPI:END -->` で囲まれた範囲を置換。
マーカーが無ければ末尾に追加する。

GitHub Actions の最後のステップで実行してリポジトリに自動コミットする。
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
README = REPO / "README.md"
DAILY = REPO / "daily"

START = "<!-- KPI:START -->"
END = "<!-- KPI:END -->"


def _draft_summary() -> tuple[int, str | None, list[str]]:
    if not DAILY.exists():
        return 0, None, []
    days = sorted([d.name for d in DAILY.iterdir() if d.is_dir() and d.name[:4].isdigit()])
    latest = days[-1] if days else None
    files = []
    if latest:
        latest_dir = DAILY / latest
        files = sorted(p.name for p in latest_dir.iterdir() if p.is_file() and p.name != "README.md")
    return len(days), latest, files


def build_section() -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    days_count, latest, files = _draft_summary()
    latest_link = f"[`daily/{latest}/`](daily/{latest}/)" if latest else "（未生成）"
    files_md = "\n".join(f"  - `{f}`" for f in files) if files else "  - （ファイルなし）"

    return f"""{START}
## ai-auto 自動運用ステータス（{now} 時点）

毎朝 07:00 (JST) に GitHub Actions が当日のドラフトを自動生成・自動コミットします。
mac セットアップ不要。iPhone の GitHub アプリで開いて1分以内に公開可能。

| 指標 | 値 |
|------|---|
| 自動生成日数 | **{days_count} 日** |
| 最新ドラフト | {latest_link} |
| ドラフト本日分 | {len(files)} ファイル |

### 最新ドラフト一覧
{files_md}

### 公開フロー（iPhone・1分）
1. GitHub アプリで上の最新ドラフトを開く
2. `note_draft.md` を Raw 表示 → コピー
3. note アプリで貼り付け → 公開ボタン
4. 完了

詳細：
- 全体設計：[`projects/2026-05-05_AI自動収益化引き継ぎ/outputs/claude_code_handover.docx`](projects/2026-05-05_AI自動収益化引き継ぎ/outputs/claude_code_handover.docx)
- iPhone 1分運用ガイド：[`COO/outputs/2026-05-05_iPhone1分運用ガイド.md`](COO/outputs/2026-05-05_iPhone1分運用ガイド.md)
- mac 全自動 Plan B：[`projects/2026-05-05_AI自動収益化引き継ぎ/deploy/SETUP_PROMPT.md`](projects/2026-05-05_AI自動収益化引き継ぎ/deploy/SETUP_PROMPT.md)
{END}"""


def main() -> int:
    section = build_section()
    if not README.exists():
        README.write_text(section + "\n", encoding="utf-8")
        print(f"created: {README}")
        return 0

    text = README.read_text(encoding="utf-8")
    if START in text and END in text:
        new = re.sub(re.escape(START) + r".*?" + re.escape(END), section,
                     text, count=1, flags=re.DOTALL)
    else:
        new = text.rstrip() + "\n\n" + section + "\n"

    if new == text:
        print("no change")
        return 0

    README.write_text(new, encoding="utf-8")
    print(f"updated: {README}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
