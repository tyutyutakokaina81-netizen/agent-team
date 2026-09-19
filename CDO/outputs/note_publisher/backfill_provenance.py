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


MAX_TRIES = 3                      # これ以上は毎runで試さない（照合不能として記録する）
ATTEMPTS = THUMBS / "_backfill_attempts.json"


def load_attempts() -> dict:
    try:
        import json
        return json.loads(ATTEMPTS.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_attempts(d: dict):
    import json
    ATTEMPTS.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


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
    # ★2026-09-22 修正: ここは long-standing なバグだった。
    # `targets[:max]` は**ファイル名順の先頭25件を毎回取る**ので、その25件が失敗し続ける限り
    # **残り75件は一度も試されない**。実際ログは何日も「埋め戻し 0 / 不一致 25 / 対象 25」で
    # 同じ25件を繰り返しており、R16 の「100件が未記録」はまったく減っていなかった。
    # ＝**毎回動いているのに何も進んでいない**。回数を記録して、試していないものから順に回す。
    att = load_attempts()
    targets.sort(key=lambda t: (att.get(t[0], {}).get("n", 0),
                                att.get(t[0], {}).get("last", "")))
    # 3回試して当たらないものは、当面の照合対象から外す（毎runの時間を食い潰さないため）。
    # ただし**捨てるのではなく「照合不能」として記録**し、R16 が別枠で数えられるようにする。
    fresh = [t for t in targets if att.get(t[0], {}).get("n", 0) < MAX_TRIES]
    if not fresh:
        print(f"（未照合 {len(targets)}件はすべて {MAX_TRIES}回試して不一致＝照合不能として記録済み）")
    targets = fresh
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
        # ★検索そのものに到達できたか。**ネットが無い環境で回すと全部「不一致」になり、
        # 試行回数だけが積み上がって「照合不能」に誤って落ちる**（code は A1 で外部遮断）。
        # 候補が1件も取れなかった run は「試した」に数えない。
        searched = 0
        for q in queries:
            if hit:
                break
            for qq in W._shorten(q):
                try:
                    urls, _ = W._search_candidates(qq)
                except Exception:
                    continue
                searched += len(urls)
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
            print(f"  \u2713 {stem[:38]} … {hit.get('license')} / {hit.get('file')}")
            if not args.dry_run:
                prov[stem] = hit
                W.save_prov(prov)
                att.pop(stem, None)
        elif not searched:
            miss += 1
            print(f"  ?  {stem[:38]} … **候補を1件も取得できなかった**（ネット遮断 or 検索語が空）"
                  f"＝試行回数には数えない（検索語: {queries}）")
        else:
            miss += 1
            rec = att.setdefault(stem, {"n": 0})
            rec["n"] = rec.get("n", 0) + 1
            rec["last"] = time.strftime("%Y-%m-%d")
            rec["queries"] = queries[:4]
            print(f"  \u2717 {stem[:38]} … 一致なし（{rec['n']}回目/{MAX_TRIES}・検索語: {queries}）")
            if rec["n"] >= MAX_TRIES and not args.dry_run:
                # **諦めたことも記録する**。ライセンスを勝手に埋めると R16 を偽の OK にしてしまうので、
                # license は入れず「照合不能」であることだけを残す。
                prov[stem] = {"backend": "unknown", "match": "failed",
                              "tried": rec["n"], "queries": queries[:4]}
                W.save_prov(prov)
                print(f"      → {MAX_TRIES}回不一致。**照合不能**として記録（licenseは埋めない）")
        time.sleep(0.5)

    if not args.dry_run:
        save_attempts(att)
    # 結果行は必ず出す（対象0でも出す＝「結果行なし」を失敗と誤認しないため）
    _giveup = sum(1 for v in att.values() if v.get("n", 0) >= MAX_TRIES)
    _pending = sum(1 for v in att.values() if 0 < v.get("n", 0) < MAX_TRIES)
    print(f"=== 結果: 埋め戻し {filled} / 不一致 {miss} / 対象 {len(targets)} "
          f"／ 再試行待ち {_pending} / 照合不能({MAX_TRIES}回試行) {_giveup} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
