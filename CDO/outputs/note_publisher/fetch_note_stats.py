#!/usr/bin/env python3
"""note のダッシュボードから **記事ごとの閲覧数** を取って TSV に落とす（cowork 側で実行）。

なぜ作ったか（2026-10-06）:
  237本公開して、**閲覧数を一度も見ていなかった**。
  だから「フォロワーがつく記事」を毎回**仮説のまま**書いていた。
  オーナーに「もうすこしフォロワーつきそうな記事書けないの？」と言われて、
  それに答えるための数字が社内に1件も無いことに気づいた。
  `CAO/outputs/2026-06-29_note施策_効果検証シート.md` は枠だけあって**データが入ったことがない**。

設計:
  - **読み取りのみ**。note 側を一切変更しない（公開・下書き・スキ・フォローに触らない）。
  - 取れた分だけ `ops/note_stats.tsv` に書く。取れなかったら**画面の実物を dump** する
    （A1 で code から DOM を見られないため。pin_article.py と同じ型）。
  - 期間は note 側の既定（全期間）を使う。並び替えもしない＝画面に出た順で取る。
  - 1回の実行で**スクロールして最後まで**読む（note は無限スクロール）。

使い方:
  python3 fetch_note_stats.py            # DRY: 取れた件数と上位20本を表示するだけ
  python3 fetch_note_stats.py --go       # ops/note_stats.tsv に書き出す
  python3 fetch_note_stats.py --go --all # ページ送りを打ち切らず最後まで（既定は60回スクロール上限）
"""

from __future__ import annotations  # macOS 既定の Python 3.9 では `str | None` が
                                    # TypeError になる。日次ログで実際に落ちていた
                                    # （2026-10-08 check_public_all / 2026-10-09 これ）。
import sys, re, json, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import publish_to_note as P
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "ops" / "note_stats.tsv"
DUMP = ROOT / "ops" / "logs" / "note_stats_dump.json"
GO = "--go" in sys.argv
ALL = "--all" in sys.argv
STATS_URLS = [
    "https://note.com/sitesettings/stats",
    "https://note.com/dashboard/stats",
]


def _num(s: str) -> int | None:
    """「1,234」「1.2万」「—」から数を作る。読めなければ None（0 と区別する）。"""
    s = (s or "").strip().replace(",", "").replace("，", "")
    if not s or s in {"-", "—", "–", "ー"}:
        return None
    m = re.match(r"^(\d+(?:\.\d+)?)\s*万$", s)
    if m:
        return int(float(m.group(1)) * 10000)
    m = re.match(r"^(\d+)$", s)
    return int(m.group(1)) if m else None


def _dump(page, why: str):
    """掴めなかった画面の実物を残す。次の実行でセレクタを直すための唯一の材料。"""
    try:
        DUMP.parent.mkdir(parents=True, exist_ok=True)
        info = {
            "why": why,
            "url": page.url,
            "title": page.title(),
            "text_head": (page.inner_text("body") or "")[:4000],
            "rows_probe": page.eval_on_selector_all(
                "[class*='stats'], [class*='Stats'], table tr, li",
                """els => els.slice(0, 40).map(e => ({
                     tag: e.tagName.toLowerCase(),
                     cls: (e.getAttribute('class') || '').slice(0, 80),
                     txt: (e.innerText || '').replace(/\\s+/g, ' ').trim().slice(0, 120)
                   }))"""),
        }
        DUMP.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"DUMP: 画面の実物を {DUMP} に保存した（これを読んでセレクタを直す）")
    except Exception as e:  # dump 自体で落ちても本体の失敗理由を消さない
        print(f"DUMP_FAILED: {type(e).__name__} {e}")


def _rows_from_page(page) -> list[dict]:
    """ダッシュボードの行から (note_id, title, view, like, comment) を拾う。

    note の DOM は変わるので、**クラス名に依存しない**で取る:
      行の中に /n/nXXXXXXXX へのリンクが1つあり、同じ行のテキストに数が並ぶ、という形だけを使う。
    """
    return page.evaluate(r"""() => {
      const out = [];
      const seen = new Set();
      for (const a of document.querySelectorAll("a[href*='/n/n']")) {
        const m = (a.getAttribute('href') || '').match(/\/n\/(n[0-9a-f]{12})/);
        if (!m) continue;
        const id = m[1];
        if (seen.has(id)) continue;
        // 数が載っている一番近い祖先まで登る（最大6段）
        let row = a, nums = [];
        for (let i = 0; i < 6 && row; i++) {
          row = row.parentElement;
          if (!row) break;
          const t = (row.innerText || '').replace(/\s+/g, ' ');
          nums = t.match(/(?:\d[\d,]*(?:\.\d+)?万?)/g) || [];
          if (nums.length >= 2) break;
        }
        seen.add(id);
        out.push({
          id,
          title: (a.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 120),
          nums: nums.slice(0, 6),
          row: row ? (row.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 200) : '',
        });
      }
      return out;
    }""")


def main() -> int:
    with sync_playwright() as pw:
        ctx = P.load_context(pw)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        opened = None
        for u in STATS_URLS:
            try:
                page.goto(u, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(2500)
                if "/n/n" in (page.content() or "") or "ビュー" in (page.inner_text("body") or ""):
                    opened = u
                    break
            except Exception as e:
                print(f"OPEN_FAILED {u}: {type(e).__name__} {e}")
        if not opened:
            _dump(page, "ダッシュボードを開けなかった（URL が変わった／ログインが切れている）")
            print("NG: ダッシュボードが開けない。`python3 publish_to_note.py --login` を先に実行する")
            return 1
        print(f"OPEN: {opened}")

        # ★2026-10-08: **描画される前に読み取っていた。**
        #   保存した画面（ops/logs/note_stats_dump.json）を見ると、
        #   インプレッション・ページビューが全部「-」のまま、記事の表も0行だった。
        #   拾えた2行は「あなたへの提案」カードの『くわしくみる』で、記事ではない。
        #   数字が入るまで待ってから読む。
        for _ in range(30):
            body = page.inner_text("body")
            if re.search(r"ページビュー\s*\n\s*[\d,]", body):
                break
            page.wait_for_timeout(1000)
        else:
            print("WARN: 数字が入らないまま先へ進みます（ログインや集計の遅れの可能性）")

        # ★期間を「全期間」にする。既定は過去28日で、記事どうしを比べるには短い。
        for label in ("全期間", "過去365日間"):
            try:
                el = page.get_by_text(label, exact=True).first
                if el and el.is_visible():
                    el.click()
                    page.wait_for_timeout(3500)
                    print(f"PERIOD: {label} に切り替えた")
                    break
            except Exception:
                continue

        # 記事ごとの表は下のほうにあるので、そこまで送ってから読む
        for _ in range(6):
            page.mouse.wheel(0, 2500)
            page.wait_for_timeout(800)

        # 無限スクロール: 行数が増えなくなるまで下げる
        limit = 400 if ALL else 60
        rows, last = [], -1
        for i in range(limit):
            rows = _rows_from_page(page)
            if len(rows) == last:
                break
            last = len(rows)
            page.mouse.wheel(0, 4000)
            page.wait_for_timeout(900)
        print(f"ROWS: {len(rows)} 行を読んだ（スクロール {i + 1} 回）")

        if not rows:
            _dump(page, "行が1件も取れなかった（DOM が変わった）")
            return 1

        # ★2026-10-08: 「あなたへの提案」カードも /n/n へのリンクを持つので、記事と混ざる。
        #   数が1つも無い行・案内文だけの行は落とす。**0件を記事0件と読み違えない**ため。
        _before = len(rows)
        rows = [r for r in rows
                if not any(w in (r.get("row") or "") for w in ("くわしくみる", "あなたへの提案"))]
        if len(rows) != _before:
            print(f"SKIP: 記事でない行を {_before - len(rows)} 行外した（提案カード）")

        recs = []
        for r in rows:
            ns = [_num(x) for x in r["nums"]]
            ns = [n for n in ns if n is not None]
            # note のダッシュボードは「ビュー / コメント / スキ」の順で並ぶことが多いが、
            # 並びは画面で変わる。**先頭の数をビューとしてだけ使い、残りは生のまま残す**
            # （解釈を固定して間違えるより、生データを持っておくほうが直せる）。
            recs.append({
                "id": r["id"],
                "title": r["title"],
                "view": ns[0] if ns else None,
                "nums": ",".join(str(n) for n in ns),
                "raw": r["row"],
            })

        got = [x for x in recs if x["view"] is not None]
        print(f"VIEW_OK: {len(got)} / {len(recs)} 本で数が読めた")
        for x in sorted(got, key=lambda y: -y["view"])[:20]:
            print(f"  {x['view']:>7}  {x['id']}  {x['title'][:46]}")

        if not GO:
            print("\nDRY: 書き出していない。`--go` を付けると ops/note_stats.tsv に保存する")
            return 0

        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("w", encoding="utf-8") as f:
            f.write("# note 記事ごとの閲覧数（fetch_note_stats.py が書く・読み取りのみ）\n")
            f.write(f"# 取得: {time.strftime('%Y-%m-%d %H:%M')}  元ページ: {opened}\n")
            f.write("# view は画面の先頭の数。並びが違う可能性があるので nums に生の数列も残す\n")
            f.write("note_id\tview\tnums\ttitle\n")
            for x in sorted(recs, key=lambda y: -(y["view"] or -1)):
                f.write(f"{x['id']}\t{x['view'] if x['view'] is not None else ''}\t{x['nums']}\t{x['title']}\n")
        print(f"WROTE: {OUT}（{len(recs)} 行）")
        if len(got) < len(recs):
            _dump(page, f"数が読めない行が {len(recs) - len(got)} 本あった")
        return 0


if __name__ == "__main__":
    try:
        P._require_playwright()
    except Exception:
        pass
    raise SystemExit(main())
