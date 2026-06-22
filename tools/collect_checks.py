#!/usr/bin/env python3
"""
collect_checks.py — 誌面の [要確認] / [to verify] を全部集めて検証チェックリストを出力する。

code(私)は外部ネット不可(A1)なので事実検証ができない。代わりに「何を確認すべきか」を
自動で1枚に集約し、ネットが使えるcowork(またはオーナー)が潰せるようにする。依存ゼロ。

使い方:
  python3 tools/collect_checks.py <file1.md> [file2.md ...] > 検証チェックリスト.md

出力: ファイル別に、要確認箇所を チェックボックス + 行番号 + 該当テキスト で列挙。
"""
import re, sys, os

MARKERS = ("[要確認", "[to verify", "[要確認]", "[to verify]")

def collect(path):
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except OSError as e:
        return [], f"(読めない: {e})"
    hits = []
    for i, ln in enumerate(lines, 1):
        if any(m in ln for m in MARKERS):
            hits.append((i, ln.strip()))
    return hits, None

def main(argv):
    files = [a for a in argv if not a.startswith("--")]
    if not files:
        print(__doc__); return 2
    total = 0
    out = ["# 事実検証チェックリスト（自動集約）",
           "",
           "> `tools/collect_checks.py` が誌面の [要確認]/[to verify] を自動抽出。",
           "> ネットが使える担当（cowork/オーナー）が各項目を確認し、チェックを入れて本文を確定する。",
           "> 確認できないものは「諸説あり」と本文に明記、誤りは修正、確実なものはマーカーを外す。",
           ""]
    for f in files:
        hits, err = collect(f)
        out.append(f"\n## {os.path.basename(f)}")
        if err:
            out.append(f"- {err}")
            continue
        if not hits:
            out.append("- （要確認なし ✅）")
            continue
        for i, txt in hits:
            total += 1
            out.append(f"- [ ] L{i}: {txt[:160]}")
    out.insert(5, f"**未確認の総数: {total} 件**\n")
    print("\n".join(out))
    sys.stderr.write(f"[collect_checks] {total} 件の要確認を {len(files)} ファイルから抽出\n")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except BrokenPipeError:
        sys.exit(0)
