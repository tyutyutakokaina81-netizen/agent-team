#!/usr/bin/env python3
"""既存サムネの出典（Commonsファイル名・ライセンス・作者）を後から埋め戻す。

背景（CQO指摘・重大1 / 2026-09-11）:
`_provenance.json` は長らく backend 名（"wikimedia"）しか記録しておらず、**採用済み113件のうち109件で
ライセンスが不明**だった。Commons は CC BY / CC BY-SA の比率が高く、表示義務のある画像が
混じっている可能性がある。R16 はそれを「素性不明＝対象外」として静かに落としていた。

## やり方
記事タイトルから当時と同じ検索語を作り、Commons の候補画像を順にダウンロードして
**手元のjpgとバイト一致（md5）するもの**を探す。一致したらそのファイルの
ファイル名・ライセンス・作者・説明ページを `_provenance.json` に書き戻す。
（手元のjpgは1280px縮小版なので、Commons側も同じ 1280px サムネURLで取得すれば一致する。）

## 実行環境
**ネットが要るので code では動かない(A1)**。GitHub Actions（note-thumbnails ワークフロー）で回す。
1回あたりの件数を --max で絞り、複数回のrunで収束させる（1回のジョブを長くしない）。

  python3 CDO/outputs/note_publisher/backfill_provenance.py --max 25
  python3 CDO/outputs/note_publisher/backfill_provenance.py --max 25 --dry-run
"""
import argparse
import hashlib
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_thumbnails_wikimedia as W  # noqa: E402
from fetch_note_thumbnails import extract_title, query_for  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
ARTICLES = ROOT / "CMO/outputs"
THUMBS = ROOT / "CDO/outputs/note_publisher/thumbnails"


def md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=25, help="1回で処理する件数（0=全部）")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    prov = W.load_prov()
    targets = []
    for f in sorted(ARTICLES.glob("*note記事*.md")) + sorted(ARTICLES.glob("*有料note*.md")):
        stem = f.stem
        jpg = THUMBS / f"{stem}.jpg"
        if not jpg.exists():
            continue
        v = prov.get(stem)
        if isinstance(v, dict) and v.get("license"):
            continue                      # 既に埋まっている
        if isinstance(v, str) and v == "owner":
            continue                      # owner実写＝Commons由来ではない
        targets.append((stem, f, jpg))
    if args.max > 0:
        targets = targets[: args.max]

    print(f"埋め戻し対象: {len(targets)}件")
    filled = miss = 0
    for stem, art, jpg in targets:
        local = md5(jpg.read_bytes())
        title = extract_title(art.read_text(encoding="utf-8"), stem)
        jp = W.jp_query_for(title, stem)
        queries = (list(jp) if isinstance(jp, (list, tuple)) else [jp]) if jp else []
        en = query_for(title, stem)
        if en:
            queries.append(en)
        hit = None
        for q in queries:
            if hit:
                break
            for qq in W._shorten(q):
                try:
                    urls, _ = W._search_candidates(qq)
                except Exception:
                    continue
                for turl, meta in urls[:6]:
                    try:
                        if md5(W._get(turl)) == local:
                            hit = {"backend": "wikimedia", "query": qq, "src": turl, **meta}
                            break
                    except Exception:
                        pass
                    time.sleep(0.2)
                if hit:
                    break
        if hit:
            filled += 1
            print(f"  ✓ {stem[:38]} … {hit.get('license')} / {hit.get('file')}")
            if not args.dry_run:
                prov[stem] = hit
                W.save_prov(prov)
        else:
            miss += 1
            print(f"  ✗ {stem[:38]} … 一致する候補が見つからず（検索語: {queries}）")
        time.sleep(0.5)

    # 結果行は必ず出す（対象0でも出す＝「結果行なし」を失敗と誤認しないため）
    print(f"=== 結果: 埋め戻し {filled} / 不一致 {miss} / 対象 {len(targets)} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
