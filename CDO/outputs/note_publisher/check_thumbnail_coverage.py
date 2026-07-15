#!/usr/bin/env python3
"""サムネ充足率チェッカー（読み取り専用・依存ゼロ・ネット不要）。

目的：note記事に対してサムネ画像(thumbnails/*.jpg)が取れているかを突き合わせ、
未取得の記事一覧と充足率を標準出力する。取りこぼし監視の定例化に使う。

判定ロジックは fetch_thumbnails_wikimedia.py に合わせる：
- 対象記事 = CMO/outputs/*note記事*.md（"サムネ生成プロンプト" を含む補助ファイルは除外）
- 「取れている」= thumbnails/{stem}.jpg が存在し、かつ _provenance.json の
  backend が GOOD_BACKENDS（wikimedia/pexels/openai/gemini/pollinations）である
- 上記を満たさない記事＝「未取得」= 次のワークフロー実行で自己修復される対象

集計のみ。ファイルの作成/変更/削除・ネットアクセスは一切しない。

使い方:
  python3 check_thumbnail_coverage.py                 # 全記事の充足率＋未取得一覧
  python3 check_thumbnail_coverage.py --filter 2026-06 # 日付など部分一致で絞る
  python3 check_thumbnail_coverage.py --quiet          # 未取得一覧を省き要約のみ
  python3 check_thumbnail_coverage.py --json           # 機械可読なJSONで出力

終了コード: 未取得が0なら0、1件以上あれば1（CI/監視での判定に使える）。
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parents[2]
ARTICLES_DIR = REPO / "CMO" / "outputs"
THUMB_DIR = SCRIPT_DIR / "thumbnails"
PROV_FILE = THUMB_DIR / "_provenance.json"
# fetch_thumbnails_wikimedia.py / generate_thumbnails.py と同じ「素性の良い」backend集合。
GOOD_BACKENDS = {"openai", "gemini", "pollinations", "wikimedia", "pexels"}


def load_prov() -> dict:
    try:
        return json.loads(PROV_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def list_articles(flt: str) -> list[Path]:
    """fetch_thumbnails_wikimedia.py の対象選定と同じ条件で記事を列挙する。"""
    files = sorted(glob.glob(str(ARTICLES_DIR / "*note記事*.md")))
    out = []
    for f in files:
        p = Path(f)
        if "サムネ生成プロンプト" in p.name:  # サムネ用プロンプトの補助mdは記事本体でない
            continue
        if flt and flt not in p.name:
            continue
        out.append(p)
    return out


def classify(articles: list[Path], prov: dict) -> dict:
    """各記事を covered / missing_file / bad_backend に分類する。"""
    covered, missing_file, bad_backend = [], [], []
    for p in articles:
        stem = p.stem
        jpg = THUMB_DIR / f"{stem}.jpg"
        backend = prov.get(stem)
        if not jpg.exists():
            missing_file.append((stem, backend))
        elif backend not in GOOD_BACKENDS:
            # jpgはあるが provenance が無い/不明 = 素性不明 → 再取得対象
            bad_backend.append((stem, backend))
        else:
            covered.append((stem, backend))
    return {"covered": covered, "missing_file": missing_file, "bad_backend": bad_backend}


def main() -> int:
    ap = argparse.ArgumentParser(description="note記事のサムネ充足率をチェック（読み取り専用）")
    ap.add_argument("--filter", default="", help="ファイル名部分一致で対象を絞る (例 2026-06)")
    ap.add_argument("--quiet", action="store_true", help="未取得一覧を省き要約のみ表示")
    ap.add_argument("--json", action="store_true", dest="as_json", help="JSONで出力")
    args = ap.parse_args()

    if not ARTICLES_DIR.exists():
        print(f"記事ディレクトリが見つかりません: {ARTICLES_DIR}", file=sys.stderr)
        return 2

    prov = load_prov()
    articles = list_articles(args.filter)
    res = classify(articles, prov)

    total = len(articles)
    covered = len(res["covered"])
    missing = res["missing_file"] + res["bad_backend"]
    rate = (covered / total * 100.0) if total else 100.0

    if args.as_json:
        print(json.dumps({
            "total": total,
            "covered": covered,
            "missing": len(missing),
            "coverage_rate": round(rate, 1),
            "missing_file": [s for s, _ in res["missing_file"]],
            "bad_backend": [{"stem": s, "backend": b} for s, b in res["bad_backend"]],
        }, ensure_ascii=False, indent=2))
        return 0 if not missing else 1

    print("=== サムネ充足率チェック（読み取り専用・集計のみ） ===")
    if args.filter:
        print(f"フィルタ: {args.filter!r}")
    print(f"記事数        : {total}")
    print(f"サムネ取得済み: {covered}")
    print(f"未取得        : {len(missing)}"
          f"（ファイル無し {len(res['missing_file'])} / 素性不明 {len(res['bad_backend'])}）")
    print(f"充足率        : {rate:.1f}%")

    if missing and not args.quiet:
        print("\n--- 未取得の記事（次回 note-thumbnails.yml 実行で自己修復対象） ---")
        for stem, backend in res["missing_file"]:
            print(f"  [ファイル無し] {stem}")
        for stem, backend in res["bad_backend"]:
            print(f"  [素性不明 backend={backend!r}] {stem}")
        print("\n→ 対処: Actions > 'Generate note thumbnails' を workflow_dispatch で再実行"
              "（不足分のみ取得＝自己修復）。運用手順は 2026-07-01_サムネ監視_運用手順.md 参照。")
    elif not missing:
        print("\n✓ 未取得なし。全記事にサムネが揃っています。")

    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
