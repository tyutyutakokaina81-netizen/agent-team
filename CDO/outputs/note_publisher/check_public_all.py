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
  - **ログインしない**（ログアウトAPI `api/v3/notes/<key>`）。読者と同じ条件で見る。
    ※2026-10-31 にブラウザから切り替えた（chromium はログイン画面へ飛ばされていた）。
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
import os
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


def _payload_status(html: str, nid: str):
    """埋め込みデータから**その記事自身の** status を取る。取れなければ None。

    ★2026-10-28: **fetch_note_comments.py で 10-22 に直したのと同じバグが、ここにも残っていた。**
      `DRAFT_MARKS` は画面の文字列を丸ごと見るので、**本文に「公開前の下書き」と書いてある記事**を
      下書きと誤判定する。実例＝`na0c047034e1c`（公開の仕組みそのものを書いた記事・22,259字）。
      **片方のツールだけ直して、もう片方を見ていなかった。**
      同じ判定を2か所で別々に書いているのが原因なので、**実装を1つに寄せる**。
    """
    if not html or not nid:
        return None
    try:
        import importlib.util as _ilu
        _p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fetch_note_comments.py")
        _sp = _ilu.spec_from_file_location("_fnc_for_check", _p)
        _m = _ilu.module_from_spec(_sp)
        _sp.loader.exec_module(_m)
        st, _ = _m.read_state_from_payload(html, nid)
        return st
    except Exception:
        return None


def classify(body: str, status: int | None, final_url: str,
             html: str = "", nid: str = "") -> tuple[str, str]:
    """(判定, 理由) を返す。判定は PUBLIC / DRAFT / GONE / UNKNOWN。"""
    # 埋め込みデータで自記事の status が取れたら、**画面の文字より先にそちらを信じる**。
    _st = _payload_status(html, nid)
    if _st == "published":
        return "PUBLIC", ""
    if _st == "draft":
        return "DRAFT", "埋め込みデータの status が draft＝読者には見えない"
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


def check_api(nid: str) -> tuple[str, str]:
    """ログアウトAPIで (判定, 理由) を返す（2026-10-31・ブラウザ方式の置き換え）。

    取得は curl で行う。macOS 既定の Python は証明書ストアが空で urllib が
    CERTIFICATE_VERIFY_FAILED になる（2026-10-31 に実際に全件で落ちた）。
    cowork の他の照合（backfill_follow.sh 等）も curl で動いている。
    """
    import subprocess
    url = f"https://note.com/api/v3/notes/{nid}"
    for attempt in range(3):
        try:
            r = subprocess.run(
                ["curl", "-s", "--max-time", "25", "-A", "Mozilla/5.0",
                 "-H", "Accept: application/json", "-w", "\n%{http_code}", url],
                capture_output=True, text=True, timeout=40)
            body, _, code = r.stdout.rpartition("\n")
            code = int(code) if code.strip().isdigit() else 0
        except Exception as e:
            code, body = 0, f"{type(e).__name__} {str(e)[:60]}"
        if code == 200:
            try:
                x = (json.loads(body).get("data") or {})
            except Exception:
                return "UNKNOWN", "API の応答が JSON でない"
            st = x.get("status")
            owner = (x.get("user") or {}).get("urlname")
            if owner and owner != AUTHOR:
                return "UNKNOWN", f"API が別の作者の記事を返した（{owner}）"
            if st == "published":
                return "PUBLIC", ""
            if st == "draft":
                return "DRAFT", "API の status が draft＝読者には見えない"
            return "UNKNOWN", f"API の status が想定外（{st}）"
        if code == 404:
            # ログアウトでは下書き・削除・非公開の区別はつかない（どれも読者には見えない）
            return "GONE", "API が 404（下書き・削除・非公開のいずれか＝読者には見えない）"
        if attempt < 2:
            time.sleep(5 * (attempt + 1))
            continue
        return "UNKNOWN", f"API が HTTP {code or '応答なし'}"
    return "UNKNOWN", "API 取得失敗（再試行切れ）"


def _rewrite(all_ids: set, rows: list) -> int:
    """`public_status.tsv` を**毎回全文書き直す**。落とした行数を返す。

    ★2026-10-28: 追記しかしていなかったので、台帳から外れた記事の行が残り続けていた。
      実例＝冷やしトマトの旧ID `n1bbb920a0ee7`（10-26 に再公開して台帳から外したのに
      GONE の行が残り、R40 が鳴り続けた）。
    ★2026-10-29: その掃除を書き出しの中に置いたため、**見るものが無い回では走らなかった**。
      呼び出し側の早い return より前でも呼べるよう、関数に切り出した。
    ※ `--ids` で一部だけ見たときに他が消えないよう、残す判定には**絞る前の一覧**を使う。
    """
    merged = {}
    dropped = 0
    if OUT.exists():
        for _ln in OUT.read_text(encoding="utf-8").splitlines():
            if _ln.startswith("#") or _ln.startswith("note_id\t"):
                continue
            _p = _ln.split("\t")
            if len(_p) < 4:
                continue
            if _p[0] in all_ids:
                merged[_p[0]] = (_p[0], _p[1], _p[2], _p[3])
            else:
                dropped += 1
    for nid, verdict, why, title in rows:
        merged[nid] = (nid, verdict, why, title)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        f.write("# 記事が読者に見えているか（check_public_all.py が書く・読み取りのみ・ログアウト状態）\n")
        f.write("# PUBLIC=見える / DRAFT=下書きのまま / GONE=無い・非公開 / UNKNOWN=判定できず\n")
        f.write("# 毎回このファイルを書き直す。**公開台帳から外れた記事の行は落とす**（2026-10-28）\n")
        f.write("# PUBLIC 以外は毎回見直す（あとで変わる判定なので・2026-10-29）\n")
        f.write("note_id\tverdict\treason\ttitle\n")
        for row in merged.values():
            f.write("\t".join(row) + "\n")
    return dropped


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="この本数だけ見る（0=全部）")
    ap.add_argument("--recheck", action="store_true", help="判定済みも含めてやり直す")
    ap.add_argument("--ids", default="", help="この記事だけ見る（カンマ区切り）")
    args = ap.parse_args()

    targets = load_targets()
    # ★台帳にある記事の一覧は、--ids で絞る**前**に取っておく。
    #   あとで「台帳から外れた記事の行」を落とすのに使う（下の書き出しを参照）。
    all_ids = {t[0] for t in targets}
    if args.ids:
        want = {x.strip() for x in args.ids.split(",") if x.strip()}
        targets = [t for t in targets if t[0] in want]
    done = {} if args.recheck else load_done()
    # ★2026-10-29: **一度 PUBLIC 以外と判定した記事を、二度と見直していなかった。**
    #   DRAFT / GONE / UNKNOWN は**あとで変わる**判定で、実際に変わっている
    #   （ひまわり・きのどくなは公開された／冷やしトマトは再公開された）。
    #   それなのに `done` に入っているだけで飛ばしていたので、
    #   **直ったことにも、誤判定にも、誰も気づけなかった**。
    #   → PUBLIC 以外は毎回もう一度見る。安定している PUBLIC だけを飛ばす。
    _recheck_verdicts = {"DRAFT", "GONE", "UNKNOWN"}
    todo = [t for t in targets
            if t[0] not in done or done.get(t[0]) in _recheck_verdicts]
    if args.limit:
        todo = todo[:args.limit]

    print(f"台帳 {len(targets)}本 / 判定済み {len(done)}本 / これから {len(todo)}本")
    if not todo:
        # ★見るものが無くても、**台帳から外れた記事の行は落とす**。
        #   ここで return していたので、2026-10-28 に入れた掃除がそもそも走っていなかった
        #   （冷やしトマトの旧ID `n1bbb920a0ee7` の GONE 行が残り続けた理由）。
        _pruned = _rewrite(all_ids, [])
        print("新しく見るものは無い（--recheck で全部やり直せる）"
              + (f"／台帳から外れた {_pruned}行を落とした" if _pruned else ""))
        return 0

    # ★2026-10-31: **ブラウザをやめてログアウトAPIで見る**（inbox 2026-10-30_005）。
    #   Playwright の素の chromium は note にログイン画面へ飛ばされ、
    #   256本中230本が UNKNOWN になっていた＝R40 は26本だけを見て全体を語っていた。
    #   `api/v3/notes/<key>` はログアウトでも公開記事を返し、下書き/削除/非公開は 404 を返す。
    #   画面の文字列（DRAFT_MARKS）に頼らないので、本文に「公開前の下書き」と書いた記事
    #   （na0c047034e1c）も誤判定しない。
    rows = []
    for i, (nid, title) in enumerate(todo, 1):
        verdict, why = check_api(nid)
        rows.append((nid, verdict, why, title))
        mark = {"PUBLIC": "  ", "DRAFT": "❌", "GONE": "❌", "UNKNOWN": "⚠️ "}[verdict]
        print(f"{mark} [{i}/{len(todo)}] {nid} {verdict:<7} {title[:36]} {why}")
        time.sleep(0.7)

    _rewrite(all_ids, rows)

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
