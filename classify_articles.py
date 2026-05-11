#!/usr/bin/env python3
"""note 記事タイトルの三層分類器（High / Mid / Low）.

オーナー safe_canna441 の note 記事を以下の方針で分類する：

  High — 全文を三言語化（日 / 英 / 中など）する価値が高い
         エッセイ・ローカル文化・富山/高岡の風景や生活描写、
         伝統工芸、海外読者の興味を引きやすい普遍的テーマ
  Mid  — 冒頭サマリーのみ翻訳する価値がある
         AI / DX 系、副業ノウハウで日本特有の文脈があるもの
  Low  — 翻訳対象外
         国内向け実務、転職事情、車買い替えなどローカル消費材

Usage:
    python3 classify_articles.py --in urls.txt \
        --out-high urls_high.txt --out-mid urls_mid.txt --out-low urls_low.txt

入力フォーマット (urls.txt):
    <url>\t<title>     ← TSV（note_fetch.py --list の出力）
  または
    [ {"url": "...", "title": "...", ...}, ... ]  ← note_fetch.py --json の出力
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


# ───────────────────────────────────────────────────────────────
# Keyword sets. Weighted so a single strong hit dominates noise.
# ───────────────────────────────────────────────────────────────

HIGH_KEYWORDS: dict[str, int] = {
    # 地域固有（最強シグナル）
    "富山": 5, "高岡": 5, "氷見": 4, "砺波": 4, "南砺": 4, "立山": 4,
    "黒部": 4, "五箇山": 5, "雨晴": 4, "北陸": 3, "金沢": 2,
    # 伝統工芸・産業文化
    "伝統工芸": 5, "工芸": 3, "漆器": 4, "銅器": 4, "鋳物": 4,
    "高岡銅器": 5, "高岡漆器": 5, "井波彫刻": 5, "螺鈿": 4,
    "和紙": 3, "藍染": 3, "染物": 3, "陶器": 3, "焼物": 3, "焼き物": 3,
    # 文化・歴史
    "祭": 3, "祭り": 3, "神社": 3, "寺": 2, "御朱印": 3,
    "曳山": 4, "獅子舞": 4, "民謡": 3, "古民家": 3,
    # 生活・風景・自然
    "風景": 2, "暮らし": 2, "生活": 1, "田舎": 2, "移住": 3,
    "里山": 3, "雪景色": 3, "桜": 2, "紅葉": 2, "海": 1, "山": 1,
    "四季": 2, "季節": 1, "自然": 1, "棚田": 3, "ホタルイカ": 4,
    # 食文化
    "郷土料理": 4, "地酒": 3, "ます寿司": 4, "白えび": 4, "寒ブリ": 4,
    "昆布締め": 4, "ばい貝": 3,
    # 形式・スタイル
    "エッセイ": 3, "随筆": 3, "紀行": 4, "旅日記": 3, "雑記": 1,
    "日記": 1, "コラム": 1,
}

MID_KEYWORDS: dict[str, int] = {
    # AI/DX
    "AI": 3, "ChatGPT": 4, "Claude": 4, "Gemini": 3, "LLM": 3,
    "生成AI": 4, "プロンプト": 3, "RAG": 3,
    "DX": 3, "自動化": 3, "RPA": 3, "ノーコード": 2,
    # 副業・働き方（日本文脈）
    "副業": 3, "在宅ワーク": 3, "リモートワーク": 2,
    "フリーランス": 3, "個人事業主": 3,
    # ツール・テンプレ系（note 文化的）
    "テンプレート": 2, "スプレッドシート": 3, "Notion": 2, "Obsidian": 2,
    "note運用": 3, "SNS運用": 3, "Twitter運用": 3, "X運用": 3,
    "YouTube運用": 3, "Kindle出版": 3,
    # ノウハウ系
    "稼ぐ": 2, "収益化": 3, "マネタイズ": 3, "ライティング": 2,
    "SEO": 2, "ブログ運営": 2, "ChatGPT活用": 4,
}

LOW_KEYWORDS: dict[str, int] = {
    # 転職・雇用
    "転職": 4, "退職": 3, "求人": 4, "履歴書": 4, "職務経歴書": 4,
    "面接": 3, "ハローワーク": 5, "失業保険": 5,
    # 車・乗物（国内消費）
    "車検": 5, "燃費": 4, "買い替え": 3, "中古車": 4, "新車": 3,
    "ディーラー": 3, "軽自動車": 4, "自動車保険": 5,
    # 国内制度・実務
    "確定申告": 4, "年末調整": 5, "住民税": 4, "国民健康保険": 5,
    "国民年金": 5, "マイナンバー": 5, "ふるさと納税": 4,
    "iDeCo": 3, "NISA": 2, "扶養": 4,
    # 国内消費・生活
    "ニトリ": 4, "コストコ": 3, "100均": 4, "100円ショップ": 4,
    "ダイソー": 4, "セリア": 4, "業務スーパー": 4,
    # 住居・国内事情
    "賃貸": 3, "引越し": 2, "住宅ローン": 4, "団信": 5,
    # 国内お得情報
    "ポイ活": 4, "楽天経済圏": 5, "PayPay": 3, "クーポン": 3,
}

# 「副業 × 確定申告」のような Mid+Low 重複時の規律
# Low キーワードの方が文脈固有性が高いので、同点なら Low に倒す。
TIE_BREAK_ORDER = ("Low", "High", "Mid")


@dataclass
class Article:
    url: str
    title: str
    extra: dict = field(default_factory=dict)


@dataclass
class Classification:
    bucket: str  # "High" | "Mid" | "Low"
    scores: dict[str, int]
    matched: dict[str, list[str]]


def _score(text: str, kws: dict[str, int]) -> tuple[int, list[str]]:
    hits: list[str] = []
    total = 0
    for kw, w in kws.items():
        # 英字キーワードは大文字小文字を無視
        pattern = re.escape(kw)
        flags = re.IGNORECASE if re.fullmatch(r"[A-Za-z0-9]+", kw) else 0
        if re.search(pattern, text, flags):
            hits.append(kw)
            total += w
    return total, hits


def classify(title: str) -> Classification:
    scores: dict[str, int] = {}
    matched: dict[str, list[str]] = {}
    for bucket, kws in (
        ("High", HIGH_KEYWORDS),
        ("Mid", MID_KEYWORDS),
        ("Low", LOW_KEYWORDS),
    ):
        s, m = _score(title, kws)
        scores[bucket] = s
        matched[bucket] = m

    best_score = max(scores.values())
    if best_score == 0:
        # シグナルなし → 安全側に倒して Low
        bucket = "Low"
    else:
        winners = [b for b, s in scores.items() if s == best_score]
        if len(winners) == 1:
            bucket = winners[0]
        else:
            for b in TIE_BREAK_ORDER:
                if b in winners:
                    bucket = b
                    break
    return Classification(bucket=bucket, scores=scores, matched=matched)


def load_articles(path: Path) -> list[Article]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    # JSON か TSV かを自動判定
    if text.lstrip().startswith("["):
        data = json.loads(text)
        return [
            Article(
                url=d["url"],
                title=d.get("title", ""),
                extra={k: v for k, v in d.items() if k not in ("url", "title")},
            )
            for d in data
            if d.get("url")
        ]
    out: list[Article] = []
    for ln in text.splitlines():
        if not ln.strip():
            continue
        parts = ln.split("\t", 1)
        url = parts[0].strip()
        title = parts[1].strip() if len(parts) > 1 else ""
        if url:
            out.append(Article(url=url, title=title))
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Classify note articles into High/Mid/Low.")
    p.add_argument("--in", dest="inp", default="urls.txt", help="input TSV or JSON")
    p.add_argument("--out-high", default="urls_high.txt")
    p.add_argument("--out-mid", default="urls_mid.txt")
    p.add_argument("--out-low", default="urls_low.txt")
    p.add_argument(
        "--report",
        default="classification_report.json",
        help="per-article reasoning report (JSON)",
    )
    p.add_argument(
        "--print",
        action="store_true",
        help="print results to stdout in addition to writing files",
    )
    args = p.parse_args()

    inp = Path(args.inp)
    if not inp.exists():
        print(f"ERROR: input not found: {inp}", file=sys.stderr)
        return 2

    articles = load_articles(inp)
    if not articles:
        print(f"WARN: no articles in {inp}", file=sys.stderr)

    buckets: dict[str, list[tuple[Article, Classification]]] = {
        "High": [], "Mid": [], "Low": []
    }
    for a in articles:
        c = classify(a.title)
        buckets[c.bucket].append((a, c))

    out_paths = {
        "High": Path(args.out_high),
        "Mid": Path(args.out_mid),
        "Low": Path(args.out_low),
    }
    for b, items in buckets.items():
        with out_paths[b].open("w", encoding="utf-8") as f:
            for a, _c in items:
                f.write(f"{a.url}\t{a.title}\n")

    # 説明可能性のための JSON レポート
    report = []
    for b in ("High", "Mid", "Low"):
        for a, c in buckets[b]:
            report.append({
                "bucket": b,
                "url": a.url,
                "title": a.title,
                "scores": c.scores,
                "matched": c.matched,
            })
    Path(args.report).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # サマリ
    total = sum(len(v) for v in buckets.values())
    print(
        f"Classified {total} articles → "
        f"High={len(buckets['High'])}, "
        f"Mid={len(buckets['Mid'])}, "
        f"Low={len(buckets['Low'])}",
        file=sys.stderr,
    )
    print(
        f"Wrote: {out_paths['High']} / {out_paths['Mid']} / {out_paths['Low']} "
        f"and report → {args.report}",
        file=sys.stderr,
    )

    if args.print:
        for b in ("High", "Mid", "Low"):
            print(f"\n=== {b} ({len(buckets[b])}) ===")
            for a, c in buckets[b]:
                matched_flat = ",".join(
                    f"{k}:{'|'.join(v)}" for k, v in c.matched.items() if v
                ) or "(no keyword hits → default Low)"
                print(f"  {a.url}\t{a.title}\t[{matched_flat}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
