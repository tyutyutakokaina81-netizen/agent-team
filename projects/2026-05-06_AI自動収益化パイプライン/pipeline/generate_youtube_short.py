"""YouTube Shorts 自動生成（30〜60秒台本／タイトル／概要欄／タグ／サムネ文言）。

依存ゼロ。テーマは themes.py から日次ローテで取得。
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from _common import OUTPUTS, append_log, stamp, write_output
from themes import Theme, theme_for


SCRIPT_TEMPLATE = """\
（オープニング・3秒）
{hook}

（本編・約30秒）
{body}

（クロージング・5秒）
{cta}
"""


def _hook(theme: Theme) -> str:
    return f"{theme.title_ja}。\n見過ごされがちな、その魅力を30秒で。"


def _body(theme: Theme) -> str:
    keywords = "・".join(theme.keywords_ja)
    return (
        f"{theme.angle}\n"
        f"今日は『{keywords}』の視点から、土地の空気をそのまま届けます。\n"
        f"派手さはありません。けれど、見終わったあとに静かに残るものがあります。"
    )


def _cta(theme: Theme) -> str:
    return (
        "気に入ったら高評価とフォローを。\n"
        f"もっと詳しい話はnote記事『{theme.title_ja}』に書いています。"
    )


def build_youtube_short(now: datetime | None = None) -> Path:
    now = now or datetime.now()
    theme = theme_for(now.date())
    script = SCRIPT_TEMPLATE.format(
        hook=_hook(theme),
        body=_body(theme),
        cta=_cta(theme),
    )

    title = f"{theme.title_ja}｜{theme.keywords_ja[0]}の30秒"
    description = (
        f"# {theme.title_ja}\n\n"
        f"{theme.angle}\n\n"
        f"テーマ：{', '.join(theme.keywords_ja)}\n"
        f"English: {theme.title_en}\n\n"
        "🎥 関連note記事はプロフィール欄から。\n"
        "📩 取材・お問い合わせはX（@FujimoriTe27067）まで。\n"
    )
    hashtags = " ".join(
        f"#{k}" for k in (
            theme.keywords_ja
            + ["shorts", "日本の暮らし", "vlog"]
            + theme.keywords_en
        )
    )
    thumbnail = f"{theme.title_ja}\n— 30秒で伝える —"

    body = f"""# YouTube Shorts 台本（自動生成）

- 生成日時：{now.isoformat(timespec='seconds')}
- テーマslug：`{theme.slug}`

## タイトル
{title}

## 台本（30〜60秒）
```
{script}
```

## 概要欄
{description}

## ハッシュタグ
{hashtags}

## サムネイル文言
```
{thumbnail}
```

## 動画素材プロンプト（HeyGen / Kling AI に渡す）
- HeyGen 用：別ファイル `*_heygen_script.md` を参照
- Kling AI 用：別ファイル `*_kling_prompt.md` を参照
"""
    out = write_output(f"{stamp(now)}_youtube_short.md", body)
    append_log("daily", f"youtube_short generated: {out.name}")
    return out


if __name__ == "__main__":
    path = build_youtube_short()
    print(f"YouTube Shorts 台本を生成しました: {path.relative_to(OUTPUTS.parent)}")
