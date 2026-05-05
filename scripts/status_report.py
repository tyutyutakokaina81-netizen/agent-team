"""半自動化の稼働状況レポート（過去2日：2026-05-03 以降）。

報告内容:
  1. applications.csv からの応募件数集計
  2. logs/ 配下の最新エラーの有無
  3. launchctl list | grep agent-team での稼働確認

使い方:
  python3 scripts/status_report.py
"""
import csv
import datetime as dt
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
CSV_FILE = REPO / "scripts/applications.csv"
LOGS_DIR = REPO / "logs"
SINCE = dt.date(2026, 5, 3)


def count_applications():
    """SINCE 以降の応募行を集計する。"""
    if not CSV_FILE.exists():
        return []
    rows = []
    try:
        with CSV_FILE.open(encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                d_raw = (row.get("date") or "").strip()
                try:
                    d = dt.date.fromisoformat(d_raw)
                except ValueError:
                    continue
                if d >= SINCE:
                    rows.append(row)
    except Exception as e:
        print(f"⚠️  applications.csv 読み込み失敗: {e}", file=sys.stderr)
    return rows


def find_recent_errors():
    """logs/ 配下の *err*.log で SINCE 以降に更新かつ非空のものを返す。"""
    if not LOGS_DIR.exists():
        return []
    findings = []
    try:
        err_files = sorted(
            list(LOGS_DIR.glob("*err*.log")) + list(LOGS_DIR.glob("*error*.log")),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    except Exception:
        return []
    for f in err_files:
        try:
            mtime = dt.datetime.fromtimestamp(f.stat().st_mtime).date()
            if mtime < SINCE:
                continue
            text = f.read_text(encoding="utf-8", errors="ignore").strip()
            if not text:
                continue
            tail = "\n".join(text.splitlines()[-3:])
            findings.append((f.name, mtime, tail))
        except Exception:
            continue
    return findings


def check_launchctl():
    """launchctl list の中で agent-team を含む行を返す。"""
    try:
        result = subprocess.run(
            ["launchctl", "list"],
            capture_output=True, text=True, check=False, timeout=10,
        )
    except FileNotFoundError:
        return None  # launchctl が無い環境
    except Exception:
        return None
    if result.returncode != 0:
        return None
    return [l for l in result.stdout.splitlines() if "agent-team" in l]


def main():
    today = dt.date.today()
    print("=" * 50)
    print(f"📊 半自動化 稼働レポート")
    print(f"   期間: {SINCE} 〜 {today}")
    print("=" * 50)

    # 1. 応募件数
    rows = count_applications()
    print(f"\n【1. 応募件数】 {len(rows)} 件")
    if rows:
        for r in rows:
            name = (r.get("job_name") or "")[:40]
            site = r.get("site") or ""
            status = r.get("status") or ""
            print(f"  - {r.get('date','')}  [{site}]  {name}  ({status})")
    else:
        print("  （該当期間の応募記録なし）")

    # 2. 最新エラー
    errors = find_recent_errors()
    print(f"\n【2. 最新エラー】 {len(errors)} 件")
    if errors:
        for name, mtime, tail in errors:
            print(f"  ▼ {name}  (更新: {mtime})")
            for line in tail.splitlines():
                print(f"      {line}")
    else:
        print("  ✓ 期間内のエラーログなし（または空）")

    # 3. launchctl 稼働確認
    lines = check_launchctl()
    print(f"\n【3. launchd 稼働確認】")
    if lines is None:
        print("  ⚠️  launchctl コマンドが利用できません（macOS外？）")
    elif lines:
        for l in lines:
            print(f"  ✓ {l}")
    else:
        print("  ❌ agent-team 関連の launchd ジョブが登録されていません")

    print("\n" + "=" * 50)


if __name__ == "__main__":
    main()
