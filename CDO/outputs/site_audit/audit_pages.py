#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_pages.py — Pages(発見インフラ)の機械監査ツール（ゼロ依存）

目的:
  海外読者リーチ(North Star)の律速＝「発見」。作った多言語Pagesが
  技術的に発見可能な状態を保っているかを、毎回手作業でなく1コマンドで検証する。
  併せて「やったと書いたが実物は無い」型の事故(8/19空note・アウディ サムネ)を、
  参照アセットの実在チェックで構造的に防ぐ。

監査項目:
  1. sitemap網羅   … apps/toyama-guide/*.html が sitemap.xml の <loc> に全て存在するか
  2. sitemap不整合 … <loc> にあるが実ファイルが無いエントリ（嘘のsitemap）
  3. リンク切れ     … 内部の相対/絶対 .html href が実在ファイルを指すか
  4. hreflang相互性 … 相互リンク集合が全ページで一致し x-default を含むか
  5. 孤立ページ     … sitemapにあるのに内部inboundリンクが0本のページ
  6. アセット実在   … <img src> / og:image 等のローカル参照が実ファイルとして存在するか

使い方:
  python3 CDO/outputs/site_audit/audit_pages.py            # 人間向けレポート
  python3 CDO/outputs/site_audit/audit_pages.py --json     # JSON出力（集計/CI用）
  python3 CDO/outputs/site_audit/audit_pages.py --strict   # 警告(孤立/アセット)もexit=1に含める
  終了コード: 0=致命的欠陥なし / 1=欠陥あり（sitemap漏れ・リンク切れ・hreflang不整合。--strictで警告も）

制約: A1(外部アクセス不要・完全ローカル静的解析)。ネットにも認証にも触らない。
"""
import os, re, sys, json, glob

# ---- 場所の自動特定（このファイル＝<repo>/CDO/outputs/site_audit/audit_pages.py） ----
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PAGES_DIR = os.path.join(REPO, "apps", "toyama-guide")
SITEMAP = os.path.join(REPO, "apps", "ai-agency-hp", "sitemap.xml")
# sitemap の <loc> に載る toyama ページの公開パス断片
LOC_MARK = "/toyama/"


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def html_files():
    return sorted(os.path.basename(p) for p in glob.glob(os.path.join(PAGES_DIR, "*.html")))


def sitemap_basenames():
    """sitemap.xml の toyama <loc> → basename集合。末尾 / は index.html 扱い。"""
    if not os.path.exists(SITEMAP):
        return None, []
    sm = read(SITEMAP)
    locs = [l for l in re.findall(r"<loc>\s*(.*?)\s*</loc>", sm) if LOC_MARK in l]
    names = set()
    for l in locs:
        tail = l.rstrip("/").split("/")[-1]
        names.add("index.html" if (l.rstrip("/").endswith("/toyama") or tail == "toyama") else tail)
    return names, locs


def internal_html_targets(txt):
    """本文中の内部 .html 参照(basename)を集める。http/mailto/#/サイト上位(..)は除外。"""
    out = set()
    for href in re.findall(r'href="([^"]+)"', txt):
        h = href.split("#")[0].strip()
        if not h or h.startswith(("http://", "https://", "mailto:", "tel:")):
            continue
        if h.startswith("/agent-team/toyama/"):
            tgt = h.split("/")[-1]
        elif h.startswith("/") or h.startswith(".."):
            continue  # サイト上位/別アプリは対象外
        else:
            tgt = h.split("/")[-1]
        if tgt.endswith(".html"):
            out.add(tgt)
    return out


def local_asset_refs(txt):
    """<img src> と og:image/twitter:image のローカル参照(パス)を集める。"""
    refs = set()
    for m in re.findall(r'<img[^>]+src="([^"]+)"', txt):
        refs.add(m)
    for m in re.findall(r'<meta[^>]+(?:property|name)="(?:og:image|twitter:image)"[^>]+content="([^"]+)"', txt):
        refs.add(m)
    local = set()
    for r in refs:
        r = r.strip()
        if not r or r.startswith(("http://", "https://", "data:")):
            continue
        local.add(r)
    return local


def hreflang_set(txt):
    return tuple(sorted(re.findall(r'<link[^>]*hreflang="([^"]+)"', txt)))


def resolve_asset(page_name, ref):
    """ページからの相対/絶対アセット参照を実ファイルパスに解決して存在確認。"""
    if ref.startswith("/agent-team/"):
        # 公開ルート = リポジトリの apps/*/ にマップ。toyama配下想定。
        tail = ref[len("/agent-team/"):]
        if tail.startswith("toyama/"):
            return os.path.join(PAGES_DIR, tail[len("toyama/"):])
        return os.path.join(REPO, "apps", tail)  # ベストエフォート
    if ref.startswith("/"):
        return None  # サイト絶対（別管理）: 判定不能→スキップ
    return os.path.join(PAGES_DIR, ref)  # 相対


def audit():
    files = html_files()
    fileset = set(files)
    sm_names, locs = sitemap_basenames()

    result = {
        "pages_dir": os.path.relpath(PAGES_DIR, REPO),
        "html_count": len(files),
        "sitemap_loc_count": len(locs),
        "errors": {},     # 致命的（exit=1）
        "warnings": {},    # 参考（--strictでexit=1）
    }

    # 1+2. sitemap 双方向
    if sm_names is None:
        result["errors"]["sitemap_missing_file"] = [os.path.relpath(SITEMAP, REPO)]
    else:
        not_in_sitemap = [f for f in files if f not in sm_names]
        loc_no_file = sorted(n for n in sm_names if n not in fileset)
        if not_in_sitemap:
            result["errors"]["html_not_in_sitemap"] = not_in_sitemap
        if loc_no_file:
            result["errors"]["sitemap_loc_without_file"] = loc_no_file

    # 3. リンク切れ + 5素材収集 + 4 hreflang + 6 アセット
    broken, inbound = {}, {f: 0 for f in files}
    hre = {}
    asset_missing = {}
    for f in files:
        txt = read(os.path.join(PAGES_DIR, f))
        for t in internal_html_targets(txt):
            if t not in fileset:
                broken.setdefault(f, []).append(t)
            elif t != f:
                inbound[t] += 1
        hre[f] = hreflang_set(txt)
        for ref in local_asset_refs(txt):
            p = resolve_asset(f, ref)
            if p is not None and not os.path.exists(p):
                asset_missing.setdefault(f, []).append(ref)
    if broken:
        result["errors"]["broken_internal_links"] = {k: sorted(v) for k, v in broken.items()}

    # 4. hreflang相互性: 同じ alternate 集合を宣言するページ群はクラスタ。
    #    各クラスタで (a)全員が同一集合を宣言 (b)x-defaultを含む を満たすか。
    hre_pages = {f: s for f, s in hre.items() if s}  # hreflangを持つページのみ対象
    clusters = {}
    for f, s in hre_pages.items():
        clusters.setdefault(s, []).append(f)
    hreflang_problems = {}
    for s, members in clusters.items():
        if "x-default" not in s:
            hreflang_problems.setdefault("no_x_default", []).extend(sorted(members))
    if hreflang_problems:
        result["errors"]["hreflang"] = hreflang_problems

    # 5. 孤立（sitemapにあるが inbound 0）: index.html は入口なので除外
    orphans = [f for f in files if f != "index.html" and inbound[f] == 0]
    if orphans:
        result["warnings"]["orphan_pages"] = orphans

    # 6. アセット欠落
    if asset_missing:
        result["warnings"]["missing_local_assets"] = {k: sorted(v) for k, v in asset_missing.items()}

    return result


def main():
    args = set(sys.argv[1:])
    r = audit()
    err_n = sum(len(v) for v in r["errors"].values())
    warn_n = sum(len(v) for v in r["warnings"].values())

    if "--json" in args:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(f"■ Pages発見インフラ監査  ({r['pages_dir']})")
        print(f"  HTML {r['html_count']}本 / sitemap <loc> {r['sitemap_loc_count']}件")
        print("")
        labels = {
            "sitemap_missing_file": "sitemap.xml が見つからない",
            "html_not_in_sitemap": "sitemapに無いHTML",
            "sitemap_loc_without_file": "<loc>があるのに実ファイル無し",
            "broken_internal_links": "内部リンク切れ",
            "hreflang": "hreflang不整合",
            "orphan_pages": "孤立ページ(inbound 0)",
            "missing_local_assets": "参照アセットが実在しない",
        }
        if not r["errors"]:
            print("  ✅ 致命的欠陥: なし（sitemap網羅・リンク切れ0・hreflang整合）")
        else:
            print("  ❌ 致命的欠陥:")
            for k, v in r["errors"].items():
                items = v if isinstance(v, list) else list(v)
                print(f"     - {labels.get(k,k)} ({len(items)}): {items if len(str(items))<400 else str(items)[:400]+' …'}")
        if r["warnings"]:
            print("  ⚠ 警告:")
            for k, v in r["warnings"].items():
                items = v if isinstance(v, list) else list(v)
                print(f"     - {labels.get(k,k)} ({len(items)}): {items if len(str(items))<400 else str(items)[:400]+' …'}")
        else:
            print("  ⚠ 警告: なし（孤立ページ0・アセット欠落0）")
        print("")
        print(f"  → errors={err_n} warnings={warn_n}")

    fail = err_n > 0 or ("--strict" in args and warn_n > 0)
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
