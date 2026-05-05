"""import_sales.py — note / BOOTH の売上CSVを CFO台帳形式に正規化して取込

設計書: CDO/outputs/2026-05-05_完全自動化パイプライン設計.md（A2）
鉄則: scripts/deliver/RULES.md（安全第一・冪等性・透明性・下位互換）

使い方:
  python3 scripts/import_sales.py note <input.csv>
  python3 scripts/import_sales.py booth <input.csv>
  python3 scripts/import_sales.py auto <input.csv>      # ヘッダーから自動判定

出力:
  CFO/outputs/_export/sales_data.csv  ← update_dashboard.py が参照する正規化済み台帳
  バックアップ: sales_data.csv.bak
  ログ: logs/import_sales.log

スキーマ（出力CSV）:
  販売日, プラットフォーム, 商品, 販売価格, 振込日, メモ
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import pathlib
import re
import shutil
import sys
from typing import Iterable

REPO = pathlib.Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "CFO/outputs/_export"
OUT_CSV = OUT_DIR / "sales_data.csv"
LOG_FILE = REPO / "logs/import_sales.log"

CANONICAL_HEADER = ["販売日", "プラットフォーム", "商品", "販売価格", "振込日", "メモ"]

# プラットフォーム別のヘッダーマッピング（既知パターン）
NOTE_HEADERS = {
    "販売日": ["公開日", "販売日", "購入日", "日付", "売上日"],
    "商品": ["タイトル", "記事タイトル", "商品名"],
    "販売価格": ["売上額", "価格", "売上", "販売金額"],
    "振込日": ["振込日", "支払日", "送金日"],
}
BOOTH_HEADERS = {
    "販売日": ["注文日", "注文日時", "販売日", "日付"],
    "商品": ["商品名", "アイテム名", "商品"],
    "販売価格": ["価格", "売上", "金額", "販売金額"],
    "振込日": ["振込日", "支払日"],
}


def now() -> dt.datetime:
    return dt.datetime.now()


def log(msg: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"[{now().isoformat(timespec='seconds')}] {msg}\n")


def parse_date(s: str) -> str:
    """日付文字列を YYYY-MM-DD に正規化。失敗時は元の値を返す。"""
    s = (s or "").strip()
    if not s:
        return ""
    # 既に ISO 形式
    try:
        return dt.date.fromisoformat(s).isoformat()
    except ValueError:
        pass
    # 一般的な日本語日付パターン
    for fmt in ("%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M",
                "%Y年%m月%d日", "%Y.%m.%d", "%Y/%m/%d %H:%M:%S"):
        try:
            return dt.datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    log(f"WARN unparseable date: {s!r}")
    return s


def parse_price(s: str) -> int:
    """販売価格を整数に正規化（¥, カンマ, 全角を除去）。"""
    s = (s or "").strip()
    if not s:
        return 0
    # 全角→半角、記号除去
    s = s.replace("，", ",").replace("￥", "").replace("¥", "").replace(",", "").replace("円", "")
    # 数字のみ抽出
    m = re.search(r"-?\d+", s)
    if m is None:
        return 0
    try:
        return int(m.group(0))
    except ValueError:
        return 0


def detect_platform(headers: list[str]) -> str:
    """ヘッダーから note/booth を自動判定。"""
    joined = " ".join(headers).lower()
    if any(k in joined for k in ["タイトル", "公開日", "クリエイター"]):
        return "note"
    if any(k in joined for k in ["アイテム", "注文", "ショップ"]):
        return "booth"
    return "unknown"


def map_row(row: dict, mapping: dict[str, list[str]]) -> dict:
    """ヘッダーマッピングに従って正規化された行を返す。"""
    out = {}
    for canonical, candidates in mapping.items():
        value = ""
        for cand in candidates:
            if cand in row and row[cand]:
                value = row[cand].strip()
                break
        out[canonical] = value
    return out


def normalize(input_csv: pathlib.Path, platform: str) -> list[dict]:
    """入力CSVを正規化スキーマのレコード列に変換。"""
    if not input_csv.exists():
        raise FileNotFoundError(f"input CSV not found: {input_csv}")

    if platform == "note":
        mapping = NOTE_HEADERS
    elif platform == "booth":
        mapping = BOOTH_HEADERS
    else:
        with input_csv.open(encoding="utf-8-sig") as f:
            r = csv.reader(f)
            try:
                headers = next(r)
            except StopIteration:
                raise ValueError("input CSV is empty")
        platform = detect_platform(headers)
        if platform == "unknown":
            raise ValueError(f"プラットフォーム自動判定失敗: headers={headers}")
        mapping = NOTE_HEADERS if platform == "note" else BOOTH_HEADERS
        log(f"auto-detected platform: {platform}")

    records = []
    with input_csv.open(encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        for row in r:
            mapped = map_row(row, mapping)
            mapped["販売日"] = parse_date(mapped["販売日"])
            mapped["振込日"] = parse_date(mapped["振込日"])
            mapped["プラットフォーム"] = platform
            mapped["販売価格"] = str(parse_price(mapped["販売価格"]))
            mapped["メモ"] = f"import:{platform}:{now().date().isoformat()}"
            if not mapped["販売日"] or not mapped["商品"]:
                log(f"SKIP invalid row: {row}")
                continue
            records.append(mapped)
    return records


def load_existing(out_csv: pathlib.Path) -> list[dict]:
    if not out_csv.exists():
        return []
    with out_csv.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def dedupe_key(row: dict) -> tuple:
    return (row.get("販売日", ""), row.get("プラットフォーム", ""),
            row.get("商品", ""), row.get("販売価格", ""))


def merge_records(existing: list[dict], new: list[dict]) -> tuple[list[dict], int]:
    """既存と新規をマージし、(全レコード, 追加件数) を返す。重複はスキップ。"""
    existing_keys = {dedupe_key(r) for r in existing}
    added = 0
    for r in new:
        if dedupe_key(r) in existing_keys:
            continue
        existing.append(r)
        existing_keys.add(dedupe_key(r))
        added += 1
    # 販売日順にソート
    existing.sort(key=lambda r: r.get("販売日", ""))
    return existing, added


def write_csv(out_csv: pathlib.Path, records: list[dict]) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CANONICAL_HEADER)
        w.writeheader()
        for r in records:
            w.writerow({k: r.get(k, "") for k in CANONICAL_HEADER})


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    platform = argv[1].lower()
    input_csv = pathlib.Path(argv[2]).resolve()

    if platform not in ("note", "booth", "auto"):
        print(f"❌ プラットフォームは note/booth/auto のいずれか: {platform}", file=sys.stderr)
        return 2

    try:
        new_records = normalize(input_csv, platform)
    except Exception as e:
        log(f"FATAL normalize failed: {e}")
        print(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))
        return 1

    existing = load_existing(OUT_CSV)
    if OUT_CSV.exists():
        shutil.copy2(OUT_CSV, OUT_CSV.with_suffix(".csv.bak"))

    merged, added = merge_records(existing, new_records)
    write_csv(OUT_CSV, merged)
    log(f"OK imported {added} new records (total {len(merged)}) from {input_csv}")

    print(json.dumps({
        "status": "success",
        "platform": platform,
        "input": str(input_csv),
        "new_records_imported": added,
        "total_records": len(merged),
        "output": str(OUT_CSV),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
