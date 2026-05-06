"""SNS / Reddit 投稿補助生成。

完全自動投稿は規約リスクのため、生成 → コピペ → ブラウザ起動 方式の
「投稿文セット」を outputs/ に保存する。
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from _common import OUTPUTS, append_log, stamp, write_output
from themes import Theme, theme_for


# Reddit 投稿先サブレディット候補（規約準拠順に並べる）
SUBREDDITS = [
    ("r/JapanTravel", "旅行視点で土地の魅力を伝える。質問形で締める。"),
    ("r/japanlife", "在住者の生活感が伝わる文体。宣伝は控えめに。"),
    ("r/Toyama", "地元コミュニティ。地域名を必ずタイトルに含める。"),
    ("r/JapanPics", "画像付きが望ましい。短文＋風景描写。"),
]


def _reddit_post(theme: Theme) -> str:
    return f"""Title:
{theme.title_en}

Body:
I live in a small city in Toyama, far from the speed of Tokyo.
{theme.angle.replace('。', '. ')}.
Nothing dramatic here, but maybe that's exactly why it feels peaceful —
small streets, quiet mornings, seasonal food, ordinary routines.

Has anyone else found unexpected calm in a place like this?
"""


def _x_post(theme: Theme) -> str:
    return (
        f"📍 {theme.title_ja}\n"
        f"{theme.angle}\n"
        f"地方には地方の速度がある。\n"
        f"続きはnoteに書きました → [URL]\n"
        f"#{theme.keywords_ja[0]} #{theme.keywords_ja[-1]} #地方暮らし"
    )


def _instagram_caption(theme: Theme) -> str:
    return (
        f"{theme.title_ja} ／ {theme.title_en}\n\n"
        f"{theme.angle}\n\n"
        "—\n"
        f"📓 noteに記事を公開しました（プロフィールリンクから）\n"
        "—\n"
        + " ".join(f"#{k}" for k in theme.keywords_ja)
        + " "
        + " ".join(f"#{k.replace(' ', '')}" for k in theme.keywords_en)
    )


def _english_intro(theme: Theme) -> str:
    return (
        f"📰 New note article: \"{theme.title_en}\"\n\n"
        f"A short essay from a small city in Toyama, Japan.\n"
        f"Theme: {', '.join(theme.keywords_en)}.\n\n"
        f"{theme.angle.replace('。', '. ')}.\n"
        f"Read it here → [URL]"
    )


def build_sns_posts(now: datetime | None = None) -> Path:
    now = now or datetime.now()
    theme = theme_for(now.date())

    sub_block = "\n".join(
        f"- **{name}** — {note}" for name, note in SUBREDDITS
    )

    body = f"""# SNS / Reddit 投稿セット（自動生成）

- 生成日時：{now.isoformat(timespec='seconds')}
- テーマslug：`{theme.slug}`
- 関連note記事：{theme.title_ja}

## 1. 英語紹介文（X / Reddit / Threads 共用）
```
{_english_intro(theme)}
```

## 2. Reddit 投稿テンプレ
推奨サブレディット：

{sub_block}

```
{_reddit_post(theme)}
```

## 3. X (Twitter) 投稿
```
{_x_post(theme)}
```

## 4. Instagram キャプション
```
{_instagram_caption(theme)}
```

## 投稿チェックリスト（規約安全）
- [ ] 同一文面を5アカウント以上に連投しない
- [ ] サブレディットごとに1日1投稿まで
- [ ] [URL] を実URLに置換した
- [ ] 画像必須サブレディット（r/JapanPics 等）には画像を添付した
- [ ] X は1日3投稿まで（自動化はしない）

## 投稿後に実施
公開できたら以下コマンドでマーカを残す（手動）：
```
echo "$(date -Iseconds) sns_post {theme.slug}" >> logs/posted_$(date +%F)_{theme.slug}.log
```
"""
    out = write_output(f"{stamp(now)}_sns_posts.md", body)
    append_log("daily", f"sns_posts generated: {out.name}")
    return out


if __name__ == "__main__":
    path = build_sns_posts()
    print(f"SNS投稿セットを生成しました: {path.relative_to(OUTPUTS.parent)}")
