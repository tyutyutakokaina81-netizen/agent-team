#!/usr/bin/env python3
"""published_registry.json の種を再構築する（CMO/_index.md の公開URL行から）。

- 台帳セルがファイル名(.md)の場合は、その md から実タイトル（メイン/タイトルブロック）を引く
- 「下書き」行は除外（未公開のため）
- 既存 registry がある場合はマージ（URL重複は既存優先＝publish時の自動追記を上書きしない）

注意: これは第1層（ローカル台帳）の種でしかない。note上の全公開記事はカバーしない。
      最終ゲートは publish_to_note.py の note検索チェック（第2層）。
"""
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
LEDGER = REPO / "CMO" / "_index.md"
OUT = Path(__file__).resolve().parent / "published_registry.json"
URL_RE = re.compile(r"https://note\.com/safe_canna441/n/[a-z0-9]+")


def title_from_md(md_path: Path):
    try:
        text = md_path.read_text(encoding="utf-8")
    except Exception:
        return None
    m = re.search(r"メイン.*?\n```\n(.+?)\n```", text, re.S) or \
        re.search(r"##\s*タイトル.*?\n```\n(.+?)\n```", text, re.S)
    if m:
        return m.group(1).strip().splitlines()[0].strip()
    return None


def clean_cell_title(cell: str):
    t = cell.strip()
    q = re.search(r"「(.+?)」", t)
    if q:  # 「題名」引用があればそれを採用
        return q.group(1).strip()
    t = re.sub(r"[★※].*$", "", t)          # 注記を落とす
    t = re.sub(r"[（(].*?[)）]", "", t)     # 括弧注記を落とす
    t = re.sub(r"¥\S+", "", t)             # 価格表記を落とす
    return t.strip()


def main():
    entries = {}
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        m = URL_RE.search(line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        if any("下書き" in c for c in cells[:2]) or "下書き" in (cells[2] if len(cells) > 2 else ""):
            continue  # 未公開の下書きは登録しない
        url = m.group(0)
        raw = cells[1]
        if raw.endswith(".md"):
            fallback = re.sub(r"^\d{4}-\d{2}-\d{2}_note記事_", "", raw[:-3]).replace("_", " ")
            title = title_from_md(REPO / "CMO" / "outputs" / raw) or fallback
        else:
            title = clean_cell_title(raw)
        if title:
            entries[url] = {"title": title, "url": url, "source": "CMO/_index.md"}

    merged = {}
    if OUT.exists():
        try:
            for e in json.loads(OUT.read_text(encoding="utf-8")):
                if e.get("url"):
                    merged[e["url"]] = e
        except Exception:
            pass
    for url, e in entries.items():
        merged.setdefault(url, e)

    out = sorted(merged.values(), key=lambda e: e.get("url", ""))
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"registry: {len(out)}件を書き出し → {OUT}")


if __name__ == "__main__":
    main()
