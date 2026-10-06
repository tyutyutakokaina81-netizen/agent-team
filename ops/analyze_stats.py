#!/usr/bin/env python3
"""`ops/note_stats.tsv` の閲覧数と、記事の**作り方**を突き合わせる。

なぜ: 237本書いて、どれが読まれたか一度も見ていなかった。
     「フォロワーがつく記事」を仮説だけで書き続けるのをここで止める。

見るもの（記事側の md から取れるものだけ）:
  カテゴリ／本文の字数／見出し画像の有無／タグ数／英語の有無／内部リンク数／曜日
出すもの:
  上位20本・下位20本と、各軸での**中央値の差**。
  ※相関があっても因果とは限らない。件数が少ない軸は「判断材料にしない」と明記する。
"""
import re, json, statistics as st
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
TSV = ROOT / "ops" / "note_stats.tsv"
OUT = ROOT / "CAO" / "outputs" / f"{date.today()}_note閲覧数_実測と作り方の突き合わせ.md"


def load_stats() -> dict[str, tuple[int, str]]:
    if not TSV.exists():
        raise SystemExit(f"NG: {TSV} が無い。先に `bash ops/stats.sh` を実行する")
    out = {}
    for line in TSV.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or line.startswith("note_id\t"):
            continue
        p = line.split("\t")
        if len(p) >= 4 and p[1].isdigit():
            out[p[0]] = (int(p[1]), p[3])
    return out


def article_facts() -> dict[str, dict]:
    """公開済み記事の md から、作り方の特徴を取る。note_id をキーにする。

    md には自分の公開 ID が書かれていない（本文中の URL は**他記事へのリンク**）。
    正本は published_registry.json の title→url なので、**md のタイトルで突き合わせる**。
    """
    reg = json.loads((ROOT / "CDO" / "outputs" / "note_publisher"
                      / "published_registry.json").read_text(encoding="utf-8"))

    def norm(x: str) -> str:
        return re.sub(r"[\s　。、．，！？!?：:；;「」『』（）()\[\]【】—–ー\-ｰ~〜|｜/／\.]+", "", x or "")

    by_title = {}
    for r in reg:
        m = re.search(r"/n/(n[0-9a-f]{12})", r.get("url", "") or "")
        if m and r.get("title"):
            by_title[norm(r["title"])] = m.group(1)

    facts = {}
    for md in sorted((ROOT / "CMO" / "outputs").glob("*.md")):
        t = md.read_text(encoding="utf-8", errors="replace")
        ti = re.search(r"##\s*タイトル\s*\n```\n(.+?)\n```", t, re.S)
        if not ti:
            continue
        key = norm(ti.group(1))
        nid = by_title.get(key)
        if not nid:  # 前方一致でも拾う（公開時にタイトルを詰めた記事がある）
            nid = next((v for k, v in by_title.items()
                        if key and (k.startswith(key[:18]) or key.startswith(k[:18]))), None)
        if not nid:
            continue
        body = re.search(r"##\s*本文\s*\n```\n(.+?)\n```", t, re.S)
        b = body.group(1) if body else ""
        tags = re.search(r"##\s*ハッシュタグ\s*\n```\n(.+?)\n```", t, re.S)
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", md.name)
        wd = date(*map(int, m.groups())).strftime("%a") if m else "?"
        facts[nid] = {
            "file": md.name,
            "chars": len(re.sub(r"\s", "", b)),
            "has_thumb": "見出し画像" in t,
            "tags": len(re.findall(r"#\S+", tags.group(1))) if tags else 0,
            "has_en": "【English】" in b,
            "links": len(re.findall(r"note\.com/\S+/n/n[0-9a-f]{12}", b)),
            "weekday": wd,
            "cat": (lambda m: m.group(1).strip().split("/")[0][:12] if m else "不明")(
                re.search(r"カテゴリ[:：]\s*(.+)", t)),
        }
    return facts


def med(xs):
    return int(st.median(xs)) if xs else 0


def main():
    stats, facts = load_stats(), article_facts()
    pairs = [(nid, v, title, facts.get(nid)) for nid, (v, title) in stats.items()]
    known = [p for p in pairs if p[3]]
    L = [f"# note 閲覧数の実測と、記事の作り方の突き合わせ（{date.today()}）", ""]
    L += [f"**取得できた記事: {len(pairs)}本**（うち md と結びついたのは {len(known)}本）", ""]
    if not pairs:
        L += ["取得0件。`ops/logs/note_stats_dump.json` を見てセレクタを直す。"]
        OUT.write_text("\n".join(L), encoding="utf-8")
        print("\n".join(L))
        return
    vs = [p[1] for p in pairs]
    L += [f"- 閲覧数の中央値: **{med(vs)}** / 最大 {max(vs)} / 最小 {min(vs)} / 合計 {sum(vs)}", ""]
    L += ["## 上位20本", "", "| 閲覧 | タイトル |", "|---:|---|"]
    for nid, v, t, f in sorted(pairs, key=lambda x: -x[1])[:20]:
        L.append(f"| {v} | {t[:54]} |")
    L += ["", "## 下位20本", "", "| 閲覧 | タイトル |", "|---:|---|"]
    for nid, v, t, f in sorted(pairs, key=lambda x: x[1])[:20]:
        L.append(f"| {v} | {t[:54]} |")

    L += ["", "## 作り方の軸ごとの中央値", "",
          "※**件数が10本未満の区分は判断材料にしない**（偶然で動く）。相関は因果ではない。", "",
          "| 軸 | 区分 | 本数 | 閲覧の中央値 |", "|---|---|---:|---:|"]

    def group(name, keyfn):
        g = {}
        for nid, v, t, f in known:
            g.setdefault(keyfn(f), []).append(v)
        for k, xs in sorted(g.items(), key=lambda x: -med(x[1])):
            flag = "" if len(xs) >= 10 else " ←件数不足"
            L.append(f"| {name} | {k}{flag} | {len(xs)} | {med(xs)} |")

    group("見出し画像", lambda f: "あり" if f["has_thumb"] else "なし")
    group("英語要約", lambda f: "本文に入っている" if f["has_en"] else "入っていない")
    group("タグ数", lambda f: "5個以上" if f["tags"] >= 5 else ("1〜4個" if f["tags"] else "0個"))
    group("本文の長さ", lambda f: ("10,000字以上" if f["chars"] >= 10000 else
                                "2,000〜9,999字" if f["chars"] >= 2000 else "2,000字未満"))
    group("他記事へのリンク", lambda f: "3本以上" if f["links"] >= 3 else ("1〜2本" if f["links"] else "なし"))
    group("曜日", lambda f: f["weekday"])
    group("カテゴリ", lambda f: f["cat"])

    L += ["", "## 読み方（やりがちな間違い）", "",
          "- **公開してからの日数が長い記事ほど閲覧は増える**。上位が古い記事ばかりなら、",
          "  それは中身ではなく時間の差。日数で割った数も見ないと判断を誤る。",
          "- タグや英語は**途中から付け始めた**ので、「付いている記事＝新しい記事」になっている。",
          "  だから上の表で差が出ても、タグの効果とは言い切れない。",
          "- それでも**下位20本に共通するもの**は手がかりになる（題材が内向き・リンクが無い等）。", ""]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L[:40]))
    print(f"\nWROTE: {OUT}")


if __name__ == "__main__":
    main()
