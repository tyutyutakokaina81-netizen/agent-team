#!/usr/bin/env python3
"""
台帳再同期 ＆ 重複検出ツール（再開条件①②の支援・2026-06-20）

note は外部ネット遮断のためコンテナから取得できない。そこで
**オーナー/cowork が note ダッシュボードから書き出した「公開済み一覧」** を入力に、
1. note 側の重複タイトルを検出（どれを非公開化すべきか）
2. note 実態 ↔ ソース記事(CMO/outputs) の突合（公開済 / 未公開 / ソース無し）
3. 掃除後の正タイトル一覧を published_titles_manifest.txt として書き出し（任意）
を行う。コンテナ/Macどちらでも動く（依存ゼロ・標準ライブラリのみ）。

使い方:
  # note公開一覧（TSV: note_id<TAB>category<TAB>title、または 1行1タイトル）を渡す
  python3 reconcile_ledger.py --note-export note_published.tsv
  python3 reconcile_ledger.py --note-export titles.txt --format titles

  # 突合レポートをファイルにも保存
  python3 reconcile_ledger.py --note-export note_published.tsv --out reconcile_report.md

  # 掃除後の正一覧を manifest に書き出す（重複ガードの照合元になる）
  python3 reconcile_ledger.py --note-export note_published.tsv --write-manifest

入力フォーマット:
  - tsv    : 1列目 note_id, 最終列 title（published_registry.tsv 形式）。# とヘッダ行は無視。
  - titles : 1行1タイトル。# 始まりは無視。
  - auto   : タブを含めば tsv、なければ titles（既定）
"""

import argparse
import re
import sys
from pathlib import Path
from collections import defaultdict, Counter

HERE = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[3]   # .../CDO/outputs/note_publisher/file → repo root
ARTICLES_DIR = REPO_ROOT / "CMO" / "outputs"
TITLE_MANIFEST = HERE / "published_titles_manifest.txt"


def normalize_title(t: str) -> str:
    """publish_to_note.py の _normalize_title と同一規則：前後空白除去＋全空白除去＋末尾「。」除去。"""
    t = t.strip().rstrip("。")
    return re.sub(r"\s+", "", t)


def parse_note_export(path: Path, fmt: str):
    """note公開一覧を [(note_id|"", title)] で返す。"""
    rows = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        use_tsv = ("\t" in line) if fmt == "auto" else (fmt == "tsv")
        if use_tsv:
            cols = [c.strip() for c in line.split("\t")]
            # ヘッダ行（title という語を含む）はスキップ
            if cols and cols[-1].lower() == "title":
                continue
            note_id = cols[0] if len(cols) >= 2 else ""
            title = cols[-1]
        else:
            note_id, title = "", line.strip()
        if title:
            rows.append((note_id, title))
    return rows


def source_titles():
    """CMO/outputs の note記事 md からタイトルを抽出 → {normalized: [ファイル名,...]}"""
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


def main():
    ap = argparse.ArgumentParser(description="台帳再同期＆重複検出ツール")
    ap.add_argument("--note-export", required=True, help="note公開一覧ファイル")
    ap.add_argument("--format", choices=["auto", "tsv", "titles"], default="auto")
    ap.add_argument("--out", default=None, help="レポート出力先（省略時は標準出力のみ）")
    ap.add_argument("--write-manifest", action="store_true",
                    help="重複除去後の正タイトルを published_titles_manifest.txt に書き出す")
    args = ap.parse_args()

    exp_path = Path(args.note_export)
    if not exp_path.exists():
        sys.exit(f"✗ ファイルが見つかりません: {exp_path}")

    note_rows = parse_note_export(exp_path, args.format)
    if not note_rows:
        sys.exit("✗ note公開一覧からタイトルを1件も読めませんでした。フォーマットを確認してください。")

    # 1) note側の重複検出（正規化タイトル単位）
    norm_counts = Counter(normalize_title(t) for _, t in note_rows)
    by_norm = defaultdict(list)
    for nid, t in note_rows:
        by_norm[normalize_title(t)].append((nid, t))
    dups = {k: v for k, v in by_norm.items() if len(v) > 1}

    # 2) ソース突合
    src = source_titles()
    note_norm_set = set(norm_counts)
    src_norm_set = set(src)
    matched = sorted(note_norm_set & src_norm_set)
    note_only = sorted(note_norm_set - src_norm_set)   # noteにあるがソース記事が無い
    src_only = sorted(src_norm_set - note_norm_set)     # ソースにあるがnote未公開

    # ---- レポート生成 ----
    L = []
    L.append("# note 台帳再同期 ＆ 重複検出レポート")
    L.append("")
    L.append(f"- note公開一覧 行数（タイトル）: **{len(note_rows)}**")
    L.append(f"- うちユニークタイトル（正規化）: **{len(note_norm_set)}**")
    L.append(f"- ソース記事（CMO/outputs）: **{sum(len(v) for v in src.values())}** / ユニーク {len(src_norm_set)}")
    L.append("")
    L.append("## 1. note側の重複タイトル（非公開化の候補）")
    if not dups:
        L.append("- 重複なし 🎉")
    else:
        L.append(f"- 重複タイトル **{len(dups)}種 / 余剰 {sum(len(v)-1 for v in dups.values())}本**（各1本残して他を非公開化）")
        L.append("")
        for k, v in sorted(dups.items(), key=lambda x: -len(x[1])):
            title = v[0][1]
            ids = ", ".join(nid for nid, _ in v if nid) or "(note_id不明)"
            L.append(f"  - 「{title}」× {len(v)} → note_id: {ids}")
    L.append("")
    L.append("## 2. 突合結果")
    L.append(f"- ✅ 公開済み（note↔ソース一致）: **{len(matched)}**")
    L.append(f"- ⚠️ note のみ（ソース記事なし＝出所不明 or 旧記事）: **{len(note_only)}**")
    L.append(f"- 📝 未公開（ソースにあるが note に無い）: **{len(src_only)}**")
    L.append("")
    if note_only:
        L.append("### ⚠️ note のみ（要確認：残す価値があるか／重複でないか）")
        id_by_norm = {k: ", ".join(nid for nid, _ in v if nid) for k, v in by_norm.items()}
        for k in note_only:
            disp = by_norm[k][0][1]
            L.append(f"  - 「{disp}」 note_id: {id_by_norm.get(k) or '(不明)'}")
        L.append("")
    if src_only:
        L.append("### 📝 未公開（公開候補のストック）")
        for k in src_only:
            disp, fname = src[k][0]
            L.append(f"  - 「{disp}」 ← {fname}")
        L.append("")

    report = "\n".join(L)
    print(report)

    if args.out:
        Path(args.out).write_text(report + "\n", encoding="utf-8")
        print(f"\n📄 レポートを書き出しました: {args.out}")

    if args.write_manifest:
        # 重複除去後の正タイトル（note実態の代表タイトル）を manifest 化
        header = (
            "# published_titles_manifest.txt （reconcile_ledger.py が自動生成）\n"
            "# note 実態の公開タイトル（重複除去後・1行1タイトル）。publish_to_note.py の重複ガード照合元。\n"
        )
        lines = [by_norm[k][0][1] for k in sorted(by_norm)]
        TITLE_MANIFEST.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
        print(f"\n🗂️  manifest を書き出しました（{len(lines)}件）: {TITLE_MANIFEST}")


if __name__ == "__main__":
    main()
