#!/usr/bin/env python3
"""
note 掃除 一括ツール（自己完結・1コマンド）— オーナーのMacで実行。

これ1本で再開条件①②の準備を全部やる：
  1) ログイン済みChromeで note 記事一覧を自動取得（スクロール総ざらい）
  2) note側の重複タイトルを検出（非公開化の候補）
  3) note 実態 ↔ ソース記事(CMO/outputs) を突合（公開済 / 未公開 / 出所不明）
  4) レポート(reconcile_report.md) と 正タイトル一覧(published_titles_manifest.txt) を出力

実行（どのディレクトリからでもOK・パスは自動解決）:
  python3 CDO/outputs/note_publisher/note_cleanup_all.py

オプション:
  --note-export FILE   スクレイプせず既存の一覧ファイルを使う（取得が失敗した時の手動フォールバック）
                       形式: TSV(note_id<TAB>title) でも 1行1タイトル でも可
  --no-manifest        manifest を書き出さない（レポートだけ見たい時）
  --max-scroll N       取りこぼす時に増やす（既定60）

前提（スクレイプ時のみ）:
  - publish_to_note.py --login 済み（~/.note_publisher_profile がある）
  - Playwright 導入済み（setup.sh）
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path
from collections import defaultdict, Counter

HERE = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[3]      # .../CDO/outputs/note_publisher/file → repo root
ARTICLES_DIR = REPO_ROOT / "CMO" / "outputs"
PROFILE_DIR = Path.home() / ".note_publisher_profile"
EXPORT_TSV = HERE / "note_published_export.tsv"
REPORT_MD = HERE / "reconcile_report.md"
TITLE_MANIFEST = HERE / "published_titles_manifest.txt"

LIST_URLS = ["https://note.com/notes", "https://note.com/"]
NOTE_ID_RE = re.compile(r"/(n[0-9a-f]{8,})")


# ---------- 共通 ----------

def normalize_title(t: str) -> str:
    """前後空白除去＋全空白除去＋末尾「。」除去（publish_to_note.py と同一規則）。"""
    t = t.strip().rstrip("。")
    return re.sub(r"\s+", "", t)


# ---------- 1) note一覧の取得（スクレイプ or 既存ファイル） ----------

def scrape_note_list(max_scroll: int) -> list[tuple[str, str]]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("✗ Playwright未インストール。setup.sh を先に実行してください。"
                 "（または --note-export で手動一覧を渡してください）")
    if not PROFILE_DIR.exists() or not any(PROFILE_DIR.iterdir()):
        sys.exit("✗ 初回ログイン未了。 `python3 publish_to_note.py --login` を先に。"
                 "（または --note-export で手動一覧を渡してください）")

    found: dict[str, str] = {}
    with sync_playwright() as p:
        ctx = None
        for kw in ({"channel": "chrome"}, {}):
            try:
                ctx = p.chromium.launch_persistent_context(
                    str(PROFILE_DIR), headless=False,
                    viewport={"width": 1280, "height": 900},
                    args=["--disable-blink-features=AutomationControlled"], **kw)
                break
            except Exception:
                continue
        if ctx is None:
            sys.exit("✗ ブラウザ起動に失敗しました。")
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        for url in LIST_URLS:
            try:
                page.goto(url, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=20000)
            except Exception as e:
                print(f"⚠️ {url} 取得失敗: {e}")
                continue
            if "login" in page.url or "accounts.google.com" in page.url:
                ctx.close()
                sys.exit("✗ 未ログイン状態です。 `python3 publish_to_note.py --login` を再実行してください。")
            stable = 0
            for _ in range(max_scroll):
                anchors = page.eval_on_selector_all(
                    "a",
                    "els => els.map(e => ({h: e.getAttribute('href')||'', t:(e.innerText||'').trim()}))",
                )
                before = len(found)
                for a in anchors:
                    m = NOTE_ID_RE.search(a["h"])
                    if not m:
                        continue
                    nid = m.group(1)
                    title = a["t"].splitlines()[0].strip() if a["t"] else ""
                    if title and (nid not in found or len(found[nid]) < len(title)):
                        found[nid] = title
                    else:
                        found.setdefault(nid, "")
                page.mouse.wheel(0, 4000)
                page.wait_for_timeout(700)
                stable = stable + 1 if len(found) == before else 0
                if stable >= 4:
                    break
            print(f"  {url} → 記事リンク {len(found)} 件（累計）")
        ctx.close()
    return list(found.items())


def load_export_file(path: Path) -> list[tuple[str, str]]:
    rows = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if "\t" in line:
            cols = [c.strip() for c in line.split("\t")]
            if cols and cols[-1].lower() == "title":
                continue
            nid = cols[0] if len(cols) >= 2 else ""
            title = cols[-1]
        else:
            nid, title = "", line.strip()
        if title or nid:
            rows.append((nid, title))
    return rows


# ---------- 2-3) 突合 ----------

def source_titles() -> dict[str, list[tuple[str, str]]]:
    out = defaultdict(list)
    for p in sorted(ARTICLES_DIR.glob("*_note記事_*.md")):
        text = p.read_text(encoding="utf-8")
        m = (re.search(r"メイン.*?\n```\n(.+?)\n```", text, re.S)
             or re.search(r"##\s*タイトル.*?\n```\n(.+?)\n```", text, re.S))
        if not m:
            continue
        title = m.group(1).strip().splitlines()[0].strip()
        out[normalize_title(title)].append((title, p.name))
    return out


def build_report(note_rows: list[tuple[str, str]]) -> tuple[str, dict]:
    by_norm = defaultdict(list)
    for nid, t in note_rows:
        by_norm[normalize_title(t)].append((nid, t))
    counts = Counter(normalize_title(t) for _, t in note_rows)
    dups = {k: v for k, v in by_norm.items() if len(v) > 1}

    src = source_titles()
    note_set, src_set = set(counts), set(src)
    matched = sorted(note_set & src_set)
    note_only = sorted(note_set - src_set)
    src_only = sorted(src_set - note_set)

    L = ["# note 掃除レポート（重複検出＋台帳突合）", ""]
    L.append(f"- note 取得タイトル: **{len(note_rows)}** / ユニーク **{len(note_set)}**")
    L.append(f"- ソース記事(CMO/outputs): **{sum(len(v) for v in src.values())}** / ユニーク **{len(src_set)}**")
    L.append("")
    L.append("## 1. note側の重複（各1本残して他を非公開化）")
    if not dups:
        L.append("- 重複なし 🎉")
    else:
        L.append(f"- **{len(dups)}種 / 余剰 {sum(len(v)-1 for v in dups.values())}本**")
        L.append("")
        for k, v in sorted(dups.items(), key=lambda x: -len(x[1])):
            ids = ", ".join(nid for nid, _ in v if nid) or "(note_id不明)"
            L.append(f"  - 「{v[0][1]}」× {len(v)} → {ids}")
    L.append("")
    L.append("## 2. 突合")
    L.append(f"- ✅ 公開済み（note↔ソース一致）: **{len(matched)}**")
    L.append(f"- ⚠️ note のみ（ソース無し＝出所不明/旧記事）: **{len(note_only)}**")
    L.append(f"- 📝 未公開（ソースにあるが note に無い）: **{len(src_only)}**")
    L.append("")
    if note_only:
        L.append("### ⚠️ note のみ（残す価値/重複か要確認）")
        for k in note_only:
            ids = ", ".join(nid for nid, _ in by_norm[k] if nid) or "(不明)"
            L.append(f"  - 「{by_norm[k][0][1]}」 {ids}")
        L.append("")
    if src_only:
        L.append("### 📝 未公開（公開候補のストック）")
        for k in src_only:
            disp, fname = src[k][0]
            L.append(f"  - 「{disp}」 ← {fname}")
        L.append("")
    return "\n".join(L), by_norm


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description="note掃除 一括ツール")
    ap.add_argument("--note-export", default=None, help="スクレイプせず既存一覧ファイルを使う")
    ap.add_argument("--no-manifest", action="store_true")
    ap.add_argument("--max-scroll", type=int, default=60)
    args = ap.parse_args()

    # 1) 一覧取得
    if args.note_export:
        path = Path(args.note_export)
        if not path.exists():
            sys.exit(f"✗ ファイルが見つかりません: {path}")
        note_rows = load_export_file(path)
        print(f"📥 既存一覧を読み込み: {len(note_rows)} 件 ({path})")
    else:
        print("🌐 note 記事一覧を取得します（Chromeが開きます）…")
        note_rows = scrape_note_list(args.max_scroll)
        if not note_rows:
            sys.exit("✗ 記事リンクを1件も取得できませんでした。"
                     "inspect_note_list.py の出力を貼ってください（セレクタ調整します）。")
        lines = ["note_id\ttitle"] + [f"{nid}\t{t}" for nid, t in sorted(note_rows, key=lambda x: x[1])]
        EXPORT_TSV.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"📄 生一覧を保存: {EXPORT_TSV}（{len(note_rows)}件）")

    # 2-3) レポート
    report, by_norm = build_report(note_rows)
    REPORT_MD.write_text(report + "\n", encoding="utf-8")
    print("\n" + report)
    print(f"\n📄 レポート: {REPORT_MD}")

    # 4) manifest
    if not args.no_manifest:
        header = ("# published_titles_manifest.txt （note_cleanup_all.py が自動生成）\n"
                  "# note 実態の公開タイトル（重複除去後）。publish_to_note.py の重複ガード照合元。\n")
        titles = [by_norm[k][0][1] for k in sorted(by_norm)]
        TITLE_MANIFEST.write_text(header + "\n".join(titles) + "\n", encoding="utf-8")
        print(f"🗂️  manifest: {TITLE_MANIFEST}（{len(titles)}件）")

    print("\n次：レポートを確認 →（掃除後）STATE.md にホールド解除を明記 → 公開再開")


if __name__ == "__main__":
    main()
