"""HeyGen / AI女子アナ用の口語スクリプト生成。

- AIっぽさを消すために、句点で区切り、間（ま）の指示を入れる
- 高岡市・日本文化・静かな暮らしをテーマ化
- YouTube Shorts 向け 30〜45秒構成
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from _common import OUTPUTS, append_log, stamp, write_output
from themes import Theme, theme_for


def _opening(theme: Theme) -> str:
    return (
        f"こんにちは、Annieです。\n"
        f"今日は「{theme.title_ja}」を、ほんの少しだけご紹介させてください。"
    )


def _middle(theme: Theme) -> str:
    return (
        f"{theme.angle}\n"
        "観光名所を巡る話ではありません。\n"
        "そこで暮らす人だけが知っている、何でもない時間の話です。\n"
        f"キーワードは、{ '、'.join(theme.keywords_ja[:3]) }。\n"
        "派手さはありませんが、静かな満足が積み重なっていく感覚があります。"
    )


def _closing(theme: Theme) -> str:
    return (
        f"続きはnote『{theme.title_ja}』で書いています。\n"
        "もしよかったら、概要欄からのぞいてみてください。\n"
        "それではまた、明日。Annieでした。"
    )


def build_heygen_script(now: datetime | None = None) -> Path:
    now = now or datetime.now()
    theme = theme_for(now.date())
    opening = _opening(theme)
    middle = _middle(theme)
    closing = _closing(theme)

    full = f"{opening}\n\n（一拍）\n\n{middle}\n\n（一拍）\n\n{closing}"

    body = f"""# HeyGen Annie 用スクリプト（自動生成）

- 生成日時：{now.isoformat(timespec='seconds')}
- テーマslug：`{theme.slug}`
- 想定尺：30〜45秒

## 演出メモ
- 話速：やや遅め（NHKアナ + 1割ゆっくり）
- 表情：微笑み弱め、目線は中央
- カメラ：胸上、背景は無地または高岡市の静かな風景の合成
- 言い回し：句点で区切る／同じ語尾を3回続けない

## スクリプト全文
```
{full}
```

## 切り出し用（30秒版）
```
{opening}
{middle}
{closing.splitlines()[0]}
```

## HeyGen 操作手順
1. https://app.heygen.com にログイン
2. Avatar: Annie を選択
3. Voice: 日本語ナチュラル女性（中速）
4. 上記スクリプトを貼り付け
5. Background: 既存テンプレートまたは Image_fx.png をアップロード
6. Generate → ダウンロード → YouTube Studio へアップロード

## 関連
- 同日YouTube台本：`{stamp(now)}_youtube_short.md`
- 同日Klingプロンプト：`{stamp(now)}_kling_prompt.md`
"""
    out = write_output(f"{stamp(now)}_heygen_script.md", body)
    append_log("daily", f"heygen_script generated: {out.name}")
    return out


if __name__ == "__main__":
    path = build_heygen_script()
    print(f"HeyGen スクリプトを生成しました: {path.relative_to(OUTPUTS.parent)}")
