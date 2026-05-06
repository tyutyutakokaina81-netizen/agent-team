"""有料note記事の構造化下書きを生成。

- 無料パート（流入）→ 有料パート（収益化）の二段構成
- 海外向け英語サブタイトル
- SNS導線文を併記
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from _common import OUTPUTS, append_log, stamp, write_output
from themes import Theme, theme_for


PRICE_DEFAULT = 980  # 円


def _free_part(theme: Theme) -> str:
    return f"""## はじめに

{theme.angle}

私は富山県高岡市という、人口17万人ほどの地方都市に住んでいる。
東京から特急と新幹線で乗り継いで4時間。
派手な観光地ではないが、暮らしている人だけが知っている時間の流れがある。

このnoteでは、{', '.join(theme.keywords_ja)} を切り口に、
地方都市での日常をどう設計しているかを書く。

## 無料で読める範囲

ここから先は無料で読める部分。
最初の3つの観察は、この街に住んで気づいたことだ。

### 観察1：朝の音が違う

都市にいたころ、目覚まし時計か通勤電車の音で起きていた。
ここでは、隣家の雨戸を開ける音や、近くを通る車の少なさで起きる。
**音の総量が少ない**ので、自分の体のリズムが先に立つ。

### 観察2：店の人と顔見知りになる

スーパー、八百屋、書店、どこも同じ店員さんが立っている。
3ヶ月もいると、向こうから声をかけてくれるようになる。
これはコストではなく、**精神的な安全装置**として効いている。

### 観察3：移動コストが低い

主要な用事はすべて自転車で15分圏内に収まる。
家賃は東京の3分の1、生活費全体で月10万円下がった。
**浮いたコストは時間に変換できる**。
"""


def _paid_part(theme: Theme) -> str:
    return f"""## 有料パート（ここからは購入者限定）

ここから先は、私自身が実際に試してきた具体的な行動と数字を書く。
- 年間どれくらいで暮らせているか
- 仕事はどう回しているか
- 50代以降に同じ動きを再現するためのチェックリスト

### 年間の固定費（実額）

| 項目 | 年額 |
|------|------|
| 家賃 | （実数値） |
| 通信費 | （実数値） |
| 食費 | （実数値） |
| 光熱費 | （実数値） |
| 趣味・交際費 | （実数値） |
| 合計 | （実数値） |

### 仕事の比率

- 受託（CrowdWorks 中心）：◯割
- 自社販売（noteテンプレ）：◯割
- 広告／印税系：◯割

### 50代から同じ動きをするためのチェックリスト

- [ ] 1ヶ月の生活費をリアル数値で把握する
- [ ] 通勤前提を一度外して住む場所を選ぶ
- [ ] 1案件あたりの単価ではなく、**継続クライアントの数**を指標にする
- [ ] AIを使う作業を週単位で1つ増やしていく
- [ ] 体力低下を前提にスケジュールを組む

…

（※ 実数値・経験談はオーナーが手動で埋める）
"""


def _sns_hook(theme: Theme) -> str:
    return (
        f"📓 新しいnoteを公開しました。\n"
        f"『{theme.title_ja}』\n"
        f"{theme.angle}\n"
        f"無料で観察3つ／有料で生活費の実数値・仕事比率・移行チェックリストを公開。\n"
        f"#{theme.keywords_ja[0]} #note #地方暮らし"
    )


def build_paid_note(now: datetime | None = None) -> Path:
    now = now or datetime.now()
    theme = theme_for(now.date())

    body = f"""---
title: {theme.title_ja}
subtitle: {theme.title_en}
price: {PRICE_DEFAULT}
tags_ja: [{', '.join(theme.keywords_ja)}]
tags_en: [{', '.join(theme.keywords_en)}]
generated_at: {now.isoformat(timespec='seconds')}
slug: {theme.slug}
---

# {theme.title_ja}
*{theme.title_en}*

> 想定価格：¥{PRICE_DEFAULT}（無料試し読み 約40%）
> 想定読者：地方移住・AI副業・50代以降の働き方に関心がある人

{_free_part(theme)}

---

{_paid_part(theme)}

---

## SNS告知文（X / Threads 用）
```
{_sns_hook(theme)}
```

## 公開前チェック
- [ ] 実数値・体験談を埋めた（プレースホルダ削除）
- [ ] 無料／有料の区切りが「観察3」直後にある
- [ ] サムネ画像を準備した
- [ ] 価格・タグを設定した
- [ ] 関連noteへの内部リンクを2つ以上入れた
"""
    out = write_output(f"{stamp(now)}_paid_note.md", body)
    append_log("daily", f"paid_note generated: {out.name}")
    return out


if __name__ == "__main__":
    path = build_paid_note()
    print(f"有料note下書きを生成しました: {path.relative_to(OUTPUTS.parent)}")
