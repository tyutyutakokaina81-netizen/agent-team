#!/usr/bin/env python3
"""公開台帳の全記事が、**ログアウトした読者に本当に見えるか**を1本ずつ確かめる（cowork 側で実行）。

なぜ作ったか（2026-10-06）:
  「コメントに返信して」と言われてコメントを探したら 0 件だった。
  取得そのものが壊れていないかを確かめるため、取得に失敗した 7 ページの保存 HTML を読んだら、
  **3本が『これは公開前の下書きです。』だった**——台帳では公開済みになっているのに、
  読者には1文字も見えていない（ひまわり／きのどくな／冷やしトマト）。
  氷見牛の2本でも同じことが起きていて、そのときは「1本だけの事故」として処理していた。
  **公開した"つもり"の記事が読まれていない**のは、海外読者に届けるという目標の根本が抜ける。
  ログアウト状態なら誰でも機械的に確かめられるので、全件を定期的に見る。

設計:
  - **読み取りのみ**。note 側を一切変更しない。
  - **ログインしない**（素の chromium）。読者とまったく同じ条件で見る。
  - 途中で止まっても続きから再開できる（結果がある ID は飛ばす。`--recheck` で全部やり直す）。
  - 判定は本文が見えるかどうか。見えなければ **理由も残す**（下書き／404／非公開／読み込み失敗）。

使い方:
  python3 check_public_all.py                 # 未判定ぶんを確認して ops/public_status.tsv に追記
  python3 check_public_all.py --limit 30      # 30本だけ（細切れに回したいとき）
  python3 check_public_all.py --recheck       # 全件やり直す
  python3 check_public_all.py --ids nXXXX,nYYYY  # 指定した記事だけ
"""

from __future__ import annotations  # macOS 既定の Python 3.9 で `int | None` が
                                    # TypeError になる。2026-10-08 の日次ログで実際に落ちていた。
import argparse
import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REGISTRY = HERE / "published_registry.json"
OUT = ROOT / "ops" / "public_status.tsv"
AUTHOR = "safe_canna441"

# 本文が見えていないことを示す文字列。note の画面にそのまま出る言葉で判定する
# （DOM の構造に頼ると note 側の変更で黙って壊れるため）。
DRAFT_MARKS = ("公開前の下書き", "これは下書き")
GONE_MARKS = ("見つかりません", "ページが存在", "削除された", "非公開", "Not Found", "お探しのページ")


def load_targets() -> list[tuple[str, str]]:
    """公開台帳から (note_id, title) を取る。下書き化済みと分かっているものも含める
    （含めないと『直したはずなのに直っていない』が見えないため）。"""
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    out, seen = [], set()
    for r in reg:
        m = re.search(r"/n/(n[0-9a-f]{12})", r.get("url", "") or "")
        if not m or m.group(1) in seen:
            continue
        seen.add(m.group(1))
        out.append((m.group(1), (r.get("title") or "").strip()))
    return out


def load_done() -> dict[str, str]:
    if not OUT.exists():
        return {}
    done = {}
    for line in OUT.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or line.startswith("note_id\t"):
            continue
        p = line.split("\t")
        if len(p) >= 2:
            done[p[0]] = p[1]
    return done


def classify(body: str, status: int | None, final_url: str) -> tuple[str, str]:
    """(判定, 理由) を返す。判定は PUBLIC / DRAFT / GONE / UNKNOWN。"""
    if any(k in body for k in DRAFT_MARKS):
        return "DRAFT", "画面に『公開前の下書きです』と出ている＝読者には見えない"
    if any(k in body for k in GONE_MARKS):
        return "GONE", "ページが無い/非公開の表示"
    if status is not None and status >= 400:
        return "GONE", f"HTTP {status}"
    if "/login" in final_url or "ログイン" in body[:120]:
        return "UNKNOWN", "ログイン画面に飛ばされた（読者には見えない可能性）"
    if len(body.strip()) < 200:
        return "UNKNOWN", f"本文が短すぎる（{len(body.strip())}字）＝読み込み失敗の可能性"
    return "PUBLIC", ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="この本数だけ見る（0=全部）")
    ap.add_argument("--recheck", action="store_true", help="判定済みも含めてやり直す")
    ap.add_argument("--ids", default="", help="この記事だけ見る（カンマ区切り）")
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print("NG: playwright が入っていない。cowork 側（owner の Mac）で実行する")
        return 1

    targets = load_targets()
    if args.ids:
        want = {x.strip() for x in args.ids.split(",") if x.strip()}
        targets = [t for t in targets if t[0] in want]
    done = {} if args.recheck else load_done()
    todo = [t for t in targets if t[0] not in done]
    if args.limit:
        todo = todo[:args.limit]

    print(f"台帳 {len(targets)}本 / 判定済み {len(done)}本 / これから {len(todo)}本")
    if not todo:
        print("新しく見るものは無い（--recheck で全部やり直せる）")
        return 0

    rows = []
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        ctx = b.new_context()          # ログインしない＝読者と同じ条件
        page = ctx.new_page()
        for i, (nid, title) in enumerate(todo, 1):
            url = f"https://note.com/{AUTHOR}/n/{nid}"
            try:
                r = page.goto(url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(2500)
                body = page.evaluate("()=>document.body.innerText")
                verdict, why = classify(body, r.status if r else None, page.url)
            except Exception as e:
                verdict, why = "UNKNOWN", f"読み込み失敗: {type(e).__name__} {str(e)[:60]}"
            rows.append((nid, verdict, why, title))
            mark = {"PUBLIC": "  ", "DRAFT": "❌", "GONE": "❌", "UNKNOWN": "⚠️ "}[verdict]
            print(f"{mark} [{i}/{len(todo)}] {nid} {verdict:<7} {title[:36]} {why}")
        ctx.close()
        b.close()

    new = not OUT.exists() or args.recheck
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w" if new else "a", encoding="utf-8") as f:
        if new:
            f.write("# 記事が読者に見えているか（check_public_all.py が書く・読み取りのみ・ログアウト状態）\n")
            f.write("# PUBLIC=見える / DRAFT=下書きのまま / GONE=無い・非公開 / UNKNOWN=判定できず\n")
            f.write("note_id\tverdict\treason\ttitle\n")
        for nid, verdict, why, title in rows:
            f.write(f"{nid}\t{verdict}\t{why}\t{title}\n")

    bad = [r for r in rows if r[1] in ("DRAFT", "GONE")]
    print(f"\n書き出し: {OUT}")
    print(f"読者に見えていない記事: {len(bad)}本" if bad else "今回見たぶんは全部読者に見えている")
    for nid, verdict, why, title in bad:
        print(f"  {verdict} {nid} {title[:40]}")
    if bad:
        print("\n直し方: note で下書きを開いて公開する（code からはできない＝A1）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
