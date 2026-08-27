#!/usr/bin/env python3
"""公開note URLを一括で「配布素材」へ差し込むツール（CDO・依存ゼロ）。

背景: 記事はauto-publishで公開されるが、note URLはowner/cowork側でしか取れない(A1)。
URLが届いた瞬間に、クロスポスト素材とCAO反響シートへ一括反映して配布準備を完了させる。

使い方:
  1) ops/note_urls.tsv を用意（1行=  key<TAB>url ）。key例: コロッケ 氷見 高岡 田んぼ 2日ガイド 8月 水道水 避暑
  2) DRY-RUN（既定・書き込まない）:  python3 ops/insert_note_urls.py
  3) 実行（書き込む）:              python3 ops/insert_note_urls.py --go

やること:
  - CMO/outputs/note_published_urls.tsv（正本URL台帳）へ追記・更新
  - クロスポスト素材に <!-- URLS:START -->…<!-- URLS:END --> ブロックを冪等に再構築
    （Reddit安全ルール順守＝本文直貼りせず「投稿者の参照/プロフィール/コメント用」一覧として置く）
  - CAO比較Dへ貼るURL対応表を stdout に出力
安全: URLは note.com の実URL形式のみ受理（誤リンク混入を防ぐ）。
"""
import re, sys, os, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URLS_TSV   = os.path.join(ROOT, "ops", "note_urls.tsv")
REGISTRY   = os.path.join(ROOT, "CMO", "outputs", "note_published_urls.tsv")
CROSSPOST  = os.path.join(ROOT, "CMO", "outputs", "2026-08-25_crosspost_Reddit_X_templates.md")

# key(部分一致) → (表示ラベル, 記事ファイル名の識別語)
KEY_MAP = {
    "コロッケ":  ("高岡コロッケ強化版",       "高岡コロッケ_地元民"),
    "氷見":      ("氷見_港町の朝5時",          "氷見_港町の朝5時"),
    "高岡":      ("高岡_江戸から昭和",          "高岡_江戸から昭和"),
    "2日":       ("富山2日完璧ガイド",          "富山2日完璧ガイド"),
    "ガイド":    ("富山2日完璧ガイド",          "富山2日完璧ガイド"),
    "8月":       ("富山の8月",                  "富山の8月"),
    "田んぼ":    ("富山の田んぼ",              "富山の田んぼ"),
    "水道水":    ("富山の水道水",              "水道水"),
    "避暑":      ("標高で変わる涼しさ",        "富山の夏_標高"),
    "標高":      ("標高で変わる涼しさ",        "富山の夏_標高"),
}
NOTE_URL_RE = re.compile(r"^https://note\.com/[^/]+/n/n[0-9a-z]{6,}(?:\?.*)?$")

def resolve(key):
    for k, v in KEY_MAP.items():
        if k in key:
            return v
    return (key, key)

def load_urls(path):
    rows = []
    if not os.path.exists(path):
        return rows, [f"入力なし: {path} を作成してください（key<TAB>url）"]
    warn = []
    for i, line in enumerate(open(path, encoding="utf-8"), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "\t" not in line:
            warn.append(f"{i}行目: TAB区切りでない → skip: {line[:40]}")
            continue
        key, url = line.split("\t", 1)
        key, url = key.strip(), url.strip()
        if not NOTE_URL_RE.match(url):
            warn.append(f"{i}行目: note実URL形式でない → skip: {url[:50]}")
            continue
        label, ident = resolve(key)
        rows.append({"key": key, "label": label, "ident": ident, "url": url})
    return rows, warn

def build_block(rows):
    lines = ["<!-- URLS:START -->",
             "## 公開URL一覧（配布用・投稿者の参照/プロフィール/コメント用）",
             "",
             "> ⚠️ Reddit本文にはリンクを直貼りしない。プロフィール欄・コメントで使う。",
             ""]
    for r in rows:
        lines.append(f"- **{r['label']}**: {r['url']}")
    lines += ["", "<!-- URLS:END -->"]
    return "\n".join(lines)

def upsert_block(text, block):
    pat = re.compile(r"<!-- URLS:START -->.*?<!-- URLS:END -->", re.S)
    if pat.search(text):
        return pat.sub(block, text)
    return text.rstrip() + "\n\n---\n\n" + block + "\n"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--go", action="store_true", help="実際に書き込む（既定はDRY-RUN）")
    ap.add_argument("--urls", default=URLS_TSV)
    args = ap.parse_args()

    rows, warn = load_urls(args.urls)
    for w in warn:
        print("  [warn]", w)
    if not rows:
        print("有効なURLが0件。ops/note_urls.tsv を確認してください（key<TAB>https://note.com/.../n/nXXXXXX）。")
        return
    print(f"受理 {len(rows)} 件:")
    for r in rows:
        print(f"  {r['label']:<18} <- {r['url']}")

    block = build_block(rows)
    print("\n--- クロスポストへ挿入するブロック ---")
    print(block)

    print("\n--- CAO比較Dへ貼るURL対応表 ---")
    for r in rows:
        print(f"  {r['label']}\t{r['url']}")

    if not args.go:
        print("\n[DRY-RUN] 書き込みません。反映するには --go を付けて再実行。")
        return

    # registry 追記/更新
    seen = {}
    if os.path.exists(REGISTRY):
        for line in open(REGISTRY, encoding="utf-8"):
            if "\t" in line:
                lbl = line.split("\t")[0]
                seen[lbl] = line.rstrip("\n")
    for r in rows:
        seen[r["label"]] = f"{r['label']}\t{r['url']}"
    with open(REGISTRY, "w", encoding="utf-8") as f:
        f.write("# label\turl\n")
        for lbl in sorted(seen):
            if not seen[lbl].startswith("# "):
                f.write(seen[lbl] + "\n")

    # crosspost へブロック反映
    t = open(CROSSPOST, encoding="utf-8").read()
    open(CROSSPOST, "w", encoding="utf-8").write(upsert_block(t, block))
    print(f"\n[書込] {REGISTRY}")
    print(f"[書込] {CROSSPOST}（URLブロック冪等更新）")

if __name__ == "__main__":
    main()
