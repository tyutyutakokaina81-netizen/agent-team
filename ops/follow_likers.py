#!/usr/bin/env python3
"""**自分の記事にスキを付けた人をフォローする**（cowork 側で実行）。

なぜ（2026-10-08）:
  これまでの集客は「ハッシュタグで見つけた知らない人」を追うだけだった。
  けれど**すでにこちらの記事にスキを付けた人**がいる。関心を示している相手で、
  フォローバックの見込みはタグ検索より明らかに高い。そこを一度も見ていなかった。
  実ページで確認済み: 記事に `aria-label="17スキ この記事にスキをつけたユーザーを見る"`
  というボタンがあり、そこから付けた人の一覧が開ける。1本で17人いた記事もある。

安全:
  - **フォローだけ**。スキもコメントもしない。
  - 1回の上限は既定10人（bot 判定を避ける）。人ごとに間を置く。
  - 済んだ相手は `ops/followed_likers.tsv` に記録して二度行かない。
  - フォロー判定は `_cowork_growth.do_follow` を使う（実装を2つ持たない）。
  - 掴めなければ**画面のボタンを保存**して止まる（A1 で DOM を見られないため）。

使い方:
  python3 ops/follow_likers.py              # 誰がいるか見るだけ
  python3 ops/follow_likers.py --go         # 実際にフォローする
  python3 ops/follow_likers.py --go --articles 5 --limit 10
"""
import csv
import datetime
import importlib.util
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBDIR = os.path.join(ROOT, "CDO/outputs/note_publisher")
REG = os.path.join(PUBDIR, "published_registry.json")
DONE = os.path.join(ROOT, "ops/followed_likers.tsv")
LOGDIR = os.path.join(ROOT, "ops/logs")
MY = "safe_canna441"
GO = "--go" in sys.argv


def _arg(name, default):
    if name in sys.argv:
        try:
            return int(sys.argv[sys.argv.index(name) + 1])
        except Exception:
            pass
    return default


ARTICLES = _arg("--articles", 6)
LIMIT = _arg("--limit", 10)

# 一覧を開くボタン。**クラス名を使わない**（note の作り替えで黙って壊れないように）
LIKERS_BTN = "[aria-label*='スキをつけたユーザー']"


def recent_published(n):
    """新しい記事から n 本。新しいほどスキが付いたばかりの人がいる。"""
    try:
        reg = json.load(open(REG, encoding="utf-8"))
    except Exception as e:
        sys.exit(f"✗ published_registry.json を読めない: {e}")
    out = []
    for r in reversed(reg):
        if r.get("unpublished"):
            continue
        m = re.search(r"/n/(n[0-9a-f]{12})", r.get("url", "") or "")
        if m:
            out.append((m.group(1), (r.get("title") or "")[:40]))
        if len(out) >= n:
            break
    return out


def load_done():
    done = set()
    if os.path.exists(DONE):
        for line in open(DONE, encoding="utf-8"):
            if line.startswith("#") or line.startswith("handle"):
                continue
            p = line.split("\t")
            if p:
                done.add(p[0].strip())
    return done


def dump_buttons(page, why):
    try:
        os.makedirs(LOGDIR, exist_ok=True)
        els = page.eval_on_selector_all(
            "button, [role='button'], a",
            "els => els.slice(0,100).map(e => ({tag:e.tagName.toLowerCase(),"
            "txt:(e.innerText||'').trim().slice(0,24),"
            "aria:e.getAttribute('aria-label')||'',href:e.getAttribute('href')||''}))")
        f = os.path.join(LOGDIR, "likers_buttons.json")
        with open(f, "w", encoding="utf-8") as fh:
            json.dump({"why": why, "url": page.url, "buttons": els}, fh,
                      ensure_ascii=False, indent=1)
        print(f"DUMP: {why} → {f}")
    except Exception as e:
        print(f"DUMP_FAILED: {type(e).__name__} {e}")


_HANDLES_JS = """(me) => {
  const out = [];
  for (const a of document.querySelectorAll("a[href^='/']")) {
    // クエリや # が付くことがあるので落としてから見る（/handle 以外は拾わない）
    const raw = (a.getAttribute('href') || '').split('?')[0].split('#')[0];
    const m = raw.match(/^\\/([A-Za-z0-9_]{3,30})\\/?$/);
    if (!m) continue;
    if (m[1] === me) continue;
    if (!out.includes(m[1])) out.push(m[1]);
  }
  return out;
}"""


def collect_likers(page, nid, title):
    """記事を開いて、スキを付けた人の handle を集める。"""
    url = f"https://note.com/{MY}/n/{nid}"
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(3000)
    except Exception as e:
        print(f"  ✗ 開けない {nid}: {type(e).__name__}")
        return []
    try:
        btn = page.query_selector(LIKERS_BTN)
    except Exception:
        btn = None
    if not btn:
        print(f"  - {title[:28]}: スキ0件か、ボタンが無い")
        return []
    label = btn.get_attribute("aria-label") or ""
    n = re.match(r"\s*(\d+)", label)
    print(f"  ● {title[:28]}: {label[:30]}")
    if n and int(n.group(1)) == 0:
        return []
    # 一覧を開く前の handle を控えて、開いたあとの差分だけを採る
    try:
        before = set(page.evaluate(_HANDLES_JS, MY))
    except Exception:
        before = set()
    try:
        btn.click()
        page.wait_for_timeout(2500)
        for _ in range(4):
            page.mouse.wheel(0, 1200)
            page.wait_for_timeout(600)
        after = page.evaluate(_HANDLES_JS, MY)
    except Exception as e:
        dump_buttons(page, f"一覧を開けない: {type(e).__name__}")
        return []
    new = [h for h in after if h not in before]
    if not new:
        dump_buttons(page, "一覧は開いたが handle が増えなかった")
    print(f"      → {len(new)}人")
    return new


def main():
    arts = recent_published(ARTICLES)
    done = load_done()
    print(f"直近の公開記事 {len(arts)}本から、スキを付けた人を探します"
          f"（すでに行った {len(done)}人は飛ばします）")
    if not GO:
        for nid, t in arts:
            print(f"  {nid}  {t}")
        print("\nDRY: `--go` で実際に開いてフォローします")
        return 0

    sys.path.insert(0, PUBDIR)
    spec = importlib.util.spec_from_file_location("growth", os.path.join(PUBDIR, "_cowork_growth.py"))
    G = importlib.util.module_from_spec(spec)
    sys.modules["growth"] = G
    try:
        spec.loader.exec_module(G)
    except SystemExit:
        pass
    from playwright.sync_api import sync_playwright
    import publish_to_note as P

    handles, rows, ok = [], [], 0
    now = datetime.datetime.now().isoformat(timespec="seconds")
    with sync_playwright() as pw:
        ctx = P.load_context(pw)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        for nid, t in arts:
            for h in collect_likers(page, nid, t):
                if h not in done and h not in handles:
                    handles.append(h)
            if len(handles) >= LIMIT:
                break
        handles = handles[:LIMIT]
        print(f"\nフォローしに行く: {len(handles)}人")
        for h in handles:
            try:
                page.goto(f"https://note.com/{h}", wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(2500)
                r = G.do_follow(page, h)
            except Exception as e:
                r = f"err:{type(e).__name__}"
            print(f"  @{h}: {r}")
            rows.append([h, r, now])
            if r in ("followed", "clicked", "already-following"):
                ok += 1
            page.wait_for_timeout(7000)
        ctx.close()

    if rows:
        head = not os.path.exists(DONE) or os.path.getsize(DONE) == 0
        with open(DONE, "a", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, delimiter="\t")
            if head:
                w.writerow(["handle", "result", "at"])
            w.writerows(rows)
    print(f"\n== スキをくれた人を {ok}人フォロー（試した {len(rows)}人）==")
    if rows and ok == 0:
        print("⚠️ 1人も増えていません。ops/logs/follow_buttons.json を push してください")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
