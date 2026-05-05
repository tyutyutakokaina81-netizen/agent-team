"""GitHub Actions から毎朝呼ばれる、当日ドラフト一括生成スクリプト。

各 generator の `build()` を import して、出力先を `daily/<YYYY-MM-DD>/` に
向けて書き出す。既存の generator 本体（OUT が `~/ai-auto/outputs` に向いている）は
触らない設計。

使い方:
    python3 tools/daily_drafts.py
    # 出力: daily/<YYYY-MM-DD>/{note_draft.md, paid_note_2980.md, ...}
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEPLOY = REPO / "projects" / "2026-05-05_AI自動収益化引き継ぎ" / "deploy"
sys.path.insert(0, str(DEPLOY))

from generate_note import build as build_note  # noqa: E402
from generate_reddit import build as build_reddit  # noqa: E402
from generate_youtube_short import build as build_youtube  # noqa: E402
from generate_paid_note import build as build_paid  # noqa: E402
from generate_seo_article import build as build_seo  # noqa: E402
from cw_apply import build as build_cw  # noqa: E402
from generate_proposal import build as build_proposal  # noqa: E402

OUT = REPO / "daily" / date.today().isoformat()
OUT.mkdir(parents=True, exist_ok=True)


def pick(items: list) -> object:
    return items[date.today().toordinal() % len(items)]


def main() -> None:
    themes = json.loads((DEPLOY / "prompts" / "themes.json").read_text(encoding="utf-8"))
    note_theme = pick(themes["note"])
    reddit_theme = pick(themes["reddit"])
    youtube_theme = pick(themes["youtube"])
    seo = pick(themes["seo_keywords"])
    seo_keyword = seo["keyword"] if isinstance(seo, dict) else seo

    files = {
        "note_draft.md": build_note(note_theme),
        "reddit_post.md": build_reddit(reddit_theme),
        "youtube_short.md": build_youtube(youtube_theme),
        "crowdworks_application_data.txt": build_cw("データ入力・リスト作成のお仕事", "data"),
        "crowdworks_application_writer.txt": build_cw(f"{seo_keyword} のSEO記事執筆", "writer"),
        "paid_note_2980.md": build_paid(note_theme, 2980),
        "seo_article.md": build_seo(seo_keyword, intent="info"),
        "proposal_sample.md": build_proposal("SNS運用代行", "ご担当者様", 50000, 8),
    }
    for name, body in files.items():
        (OUT / name).write_text(body, encoding="utf-8")

    today_str = date.today().isoformat()
    readme = f"""# {today_str} のドラフト集

GitHub Actions により毎朝 07:00 (JST) に自動生成されたドラフト。
mac セットアップ不要・iPhone のブラウザだけで運用できます。

## ファイル一覧

| ファイル | 用途 | 公開先 |
|---------|------|-------|
| `note_draft.md` | 無料note記事 | note.com |
| `paid_note_2980.md` | 有料note ¥2,980 | note.com |
| `reddit_post.md` | Reddit投稿（英語） | reddit.com |
| `youtube_short.md` | YouTube Shorts台本 | youtube.com |
| `seo_article.md` | SEO記事骨組み（claude.ai でポリッシュ推奨） | クライアント納品 |
| `crowdworks_application_data.txt` | CW応募文（データ入力系） | crowdworks.jp |
| `crowdworks_application_writer.txt` | CW応募文（ライター系） | crowdworks.jp |
| `proposal_sample.md` | 法人向け提案書サンプル | 個別調整 |

## iPhone での1分運用

1. iPhone で GitHub アプリを開く（無料）
2. このリポジトリ → `daily/{today_str}/` を開く
3. 公開したいファイル（例：`note_draft.md`）をタップ
4. 右上の `…` → コピー（または Raw 表示で全選択コピー）
5. note アプリを開く → 新規記事 → 貼り付け → 公開
6. 公開後の URL を控えて、後で `published.csv` に記録（任意）

**所要：1分以内 / mac 不要 / cron 不要 / 認証不要**

## 今日のテーマ選定

| 種別 | テーマ |
|------|--------|
| note | {note_theme} |
| reddit | {reddit_theme} |
| youtube | {youtube_theme} |
| SEO記事 | {seo_keyword} |
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")

    print(f"Generated {len(files) + 1} files in {OUT}")
    for name in list(files) + ["README.md"]:
        print(f"  - daily/{today_str}/{name}")


if __name__ == "__main__":
    main()
