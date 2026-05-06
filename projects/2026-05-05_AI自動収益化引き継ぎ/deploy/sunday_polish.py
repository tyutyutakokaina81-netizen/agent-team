"""日曜18時のハイブリッド運用支援ツール。

直近7日の note 投稿テーマから、有料note・SEO記事・提案書として展開すべき
高単価候補を3本選び、骨組みを生成して outputs/ に保存する。

cron: 0 18 * * 0 cd ~/ai-auto && python3 sunday_polish.py >> logs/sunday.log 2>&1

人間は claude.ai に prompts/polish_prompts.md のプロンプトを貼って肉付けし、
note または CrowdWorks に貼って公開・応募する。
"""
from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import generate_paid_note
import generate_proposal
import generate_seo_article

BASE = Path.home() / "ai-auto"
CSV_PATH = BASE / "published.csv"
LOG = BASE / "logs" / "sunday.log"

WINDOW_DAYS = 7


def recent_note_titles() -> list[str]:
    if not CSV_PATH.exists():
        return []
    cutoff = datetime.now() - timedelta(days=WINDOW_DAYS)
    titles: list[str] = []
    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r.get("kind") != "note":
                continue
            if datetime.fromisoformat(r["timestamp"]) < cutoff:
                continue
            titles.append(r["title"])
    return titles


def pick_top_themes(titles: list[str], n: int = 3) -> list[str]:
    if not titles:
        return [
            "AI時代の地方副業を続ける小さな型",
            "AI ライティング 副業",
            "SNS運用代行 個人 始め方",
        ]
    seen: dict[str, int] = Counter()
    for t in titles:
        for word in t.split():
            if len(word) > 1:
                seen[word] += 1
    if seen:
        top_words = [w for w, _ in seen.most_common(n)]
        return [f"{w} 完全ガイド" for w in top_words]
    return titles[:n]


def main() -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    titles = recent_note_titles()
    themes = pick_top_themes(titles)

    paid_path = BASE / "outputs" / f"{datetime.now():%Y-%m-%d}_paid_note_{themes[0].replace(' ', '_')[:30]}.md"
    paid_path.write_text(generate_paid_note.build(themes[0], 2980), encoding="utf-8")

    seo_path = BASE / "outputs" / f"{datetime.now():%Y-%m-%d}_seo_article_{themes[1].replace(' ', '_')[:30]}.md"
    seo_path.write_text(generate_seo_article.build(themes[1], intent="info"), encoding="utf-8")

    prop_path = BASE / "outputs" / f"{datetime.now():%Y-%m-%d}_proposal_{themes[2].replace(' ', '_')[:30]}.md"
    prop_path.write_text(generate_proposal.build(themes[2], "ご担当者様", 50000, 8), encoding="utf-8")

    msg = f"今週の高単価候補3本:\n  1) 有料note ¥2,980 → {paid_path.name}\n  2) SEO記事 → {seo_path.name}\n  3) 提案書 → {prop_path.name}"
    print(msg)
    print("\n次：claude.ai に prompts/polish_prompts.md のプロンプトを貼って肉付け → 公開・送付")

    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')} themes={themes}\n")


if __name__ == "__main__":
    main()
