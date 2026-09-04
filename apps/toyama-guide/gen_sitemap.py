#!/usr/bin/env python3
"""sitemap.xml を最新の toyama-guide ページで再生成する（依存ゼロ）。

なぜ必要か：sitemap は手書きで更新が漏れやすく、実際に 2026-08-25→09-04 の間に
新規英語ページ(en-tsukimi/en-compact-city/en-pears 等)が sitemap から抜けていた。
＝検索エンジンが新記事を見つけにくい。新記事を足したらこれを1回走らせる。

やること：
  - 既存 sitemap の **非 /toyama/ URL（ai-agency, blog, tools 等）はそのまま保持**。
  - /toyama/ の URL 一式を、apps/toyama-guide/*.html の現状から作り直す。
    lastmod は各ファイルの git 最終コミット日（無ければ today）。
  - en-*.html は priority 0.7、その他 0.6、en.html 0.9、index(=/toyama/) 0.8。

使い方：
  python3 apps/toyama-guide/gen_sitemap.py            # 反映（sitemap.xml を書き換え）
  python3 apps/toyama-guide/gen_sitemap.py --check     # 差分だけ表示（書き換えない）
"""
import os, re, sys, glob, subprocess, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SITEMAP = os.path.join(ROOT, "apps/ai-agency-hp/sitemap.xml")   # deploy で _site/sitemap.xml になる正本
GUIDE = os.path.join(ROOT, "apps/toyama-guide")
BASE = "https://tyutyutakokaina81-netizen.github.io/agent-team"
TODAY = datetime.date.today().isoformat()


def gitdate(path):
    try:
        d = subprocess.check_output(["git", "log", "-1", "--format=%cs", "--", path],
                                    text=True, cwd=ROOT).strip()
        return d or TODAY
    except Exception:
        return TODAY


def build_toyama_entries():
    entries = []
    for f in sorted(glob.glob(os.path.join(GUIDE, "*.html"))):
        base = os.path.basename(f)
        if base == "index.html":
            loc, pri = f"{BASE}/toyama/", "0.8"
        elif base == "en.html":
            loc, pri = f"{BASE}/toyama/en.html", "0.9"
        else:
            loc = f"{BASE}/toyama/{base}"
            pri = "0.7" if base.startswith("en-") else "0.6"
        entries.append(f'  <url><loc>{loc}</loc><lastmod>{gitdate(f)}</lastmod><priority>{pri}</priority></url>')
    return entries


def main():
    check = "--check" in sys.argv
    src = open(SITEMAP, encoding="utf-8").read()
    blocks = re.findall(r'<url>.*?</url>', src, re.S)
    non_toyama = [b for b in blocks if "/toyama/" not in b]
    toyama = build_toyama_entries()

    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    out += ["  " + b.strip() for b in non_toyama]
    out += toyama
    out.append("</urlset>")
    new = "\n".join(out) + "\n"

    old_toyama = sum(1 for b in blocks if "/toyama/" in b)
    print(f"非toyama {len(non_toyama)}件保持 ／ toyama {old_toyama}→{len(toyama)}件 ／ 総計 {len(non_toyama)+len(toyama)}")
    if check:
        if new != src:
            print("差分あり（--check なので書き換えていない）。反映するには引数なしで実行。")
        else:
            print("差分なし（sitemap は最新）。")
        return
    open(SITEMAP, "w", encoding="utf-8").write(new)
    print(f"書き換え完了: {SITEMAP}")


if __name__ == "__main__":
    main()
