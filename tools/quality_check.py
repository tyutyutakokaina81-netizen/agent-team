#!/usr/bin/env python3
"""
quality_check.py — note記事/フリーペーパー誌面の規則(A4/A5)自動チェック。

毎回手でgrepしていた「禁止語・混入物・PII」を自動化する。依存ゼロ(標準ライブラリのみ)。
コンテナはネット不要・ゼロ予算で動く。CIやコミット前ゲートに使える(違反があれば終了コード1)。

使い方:
  python3 tools/quality_check.py <file1.md> [file2.md ...]
  python3 tools/quality_check.py --reader <誌面.md>   # 読者に出す原稿(混入物も厳格に検査)
  python3 tools/quality_check.py CMO/outputs/*.md      # まとめて
  python3 tools/quality_check.py --quiet ...           # 違反のみ表示

カテゴリ:
  [A5-HARD] 誇張・断定(必ず是正)            : 世界唯一/日本一/最高級 等
  [A5-SOFT] 誇張になりやすい語(要確認)       : 必ず/絶対/最高
  [MIX]     読者に出してはいけない混入物      : 社内向け/サムネ生成プロンプト/```/¥980 等(--reader時のみHARD)
  [PII]     実在店名の疑い(CAO監査18より)     : 既知の要伏字リスト
終了コード: HARD違反が1件でもあれば 1、無ければ 0。
"""
import re, sys

A5_HARD = ["世界唯一", "日本唯一", "世界一", "日本一", "世界初", "日本初", "最高級"]
A5_SOFT = ["必ず", "絶対", "最高", "一番", "随一"]
# 読者に出す誌面に混ざってはいけない、社内/note運用の痕跡
MIX = ["社内向け", "サムネ", "ハッシュタグ", "```", "note記事：", "¥980", "有料マガジン", "実写生成プロンプト"]
# CAO監査(research/18)で高確度PIIとして挙がった実在店名/固有名(要伏字)
PII_NAMES = ["レストランほりい", "御清水庵", "五郎丸屋"]

def scan(path, reader=False, quiet=False):
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except OSError as e:
        print(f"  ! 読めない: {e}")
        return 1
    hard = []   # (cat, term, lineno, text)
    soft = []
    for i, ln in enumerate(lines, 1):
        for t in A5_HARD:
            if t in ln: hard.append(("A5-HARD", t, i, ln.strip()))
        for t in A5_SOFT:
            if t in ln: soft.append(("A5-SOFT", t, i, ln.strip()))
        for t in PII_NAMES:
            if t in ln: hard.append(("PII", t, i, ln.strip()))
        for t in MIX:
            if t in ln:
                (hard if reader else soft).append(("MIX", t, i, ln.strip()))
    hard_n = len(hard)
    status = "NG" if hard_n else "ok"
    if not (quiet and not hard_n):
        print(f"[{status}] {path}  (HARD={hard_n} / SOFT={len(soft)})")
    for cat, t, i, txt in hard:
        print(f"    ✗ {cat:8} L{i}: 「{t}」  {txt[:70]}")
    if not quiet:
        for cat, t, i, txt in soft:
            print(f"    · {cat:8} L{i}: 「{t}」  {txt[:70]}")
    return 1 if hard_n else 0

def main(argv):
    reader = "--reader" in argv
    quiet = "--quiet" in argv
    files = [a for a in argv if not a.startswith("--")]
    if not files:
        print(__doc__); return 2
    rc = 0
    for f in files:
        rc |= scan(f, reader=reader, quiet=quiet)
    print(f"\n=== 結果: {'違反あり(要是正)' if rc else 'すべて合格'} ===")
    return rc

if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except BrokenPipeError:
        # head等でパイプが閉じられた場合に静かに終了
        try: sys.stdout.close()
        except Exception: pass
        sys.exit(0)
