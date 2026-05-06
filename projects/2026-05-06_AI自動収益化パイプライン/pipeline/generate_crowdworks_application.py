"""CrowdWorks 応募文の日次生成。

- 引き継ぎ書 第14章のテンプレートをベースに、応募ジャンルを日次ローテ
- 単価感・納期感・実績文は環境変数で上書き可（CW_PROFILE_NAME 等）
- 完成文は outputs/{stamp}_crowdworks_application.txt に保存
"""
from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

from _common import OUTPUTS, append_log, env, stamp, write_output


GENRES = [
    {
        "slug": "data-entry",
        "label": "データ入力・リスト作成",
        "skills": "Excel／Google Sheets／CSV整形",
        "speed": "100行/30分目安",
        "pitch": "正確性と速度を両立し、フォーマット指定にも柔軟に対応します。",
    },
    {
        "slug": "research",
        "label": "簡易リサーチ・情報収集",
        "skills": "Web検索／一次情報の特定／出典明記",
        "speed": "10件/2時間目安",
        "pitch": "出典URLを必ず添え、根拠が辿れる形でレポートします。",
    },
    {
        "slug": "writing",
        "label": "SEOライティング",
        "skills": "1記事1,500〜3,000字／構成案＋本文／見出し最適化",
        "speed": "3,000字/1日",
        "pitch": "キーワード設計から納品まで一貫対応します。継続案件歓迎です。",
    },
    {
        "slug": "transcription",
        "label": "文字起こし・要約",
        "skills": "音声→テキスト／タイムスタンプ付き／要約2段階",
        "speed": "60分音声/3時間",
        "pitch": "原文忠実版と要約版の2形態で納品し、用途に合わせて使い分け可能です。",
    },
    {
        "slug": "ai-prompt",
        "label": "AIプロンプト設計・運用代行",
        "skills": "ChatGPT／Claude／業務テンプレ化",
        "speed": "1業務フロー/2日",
        "pitch": "属人化していた業務を再現可能なプロンプトに落とし込みます。",
    },
    {
        "slug": "sns-support",
        "label": "SNS運用補助・投稿文作成",
        "skills": "X／Instagram／投稿カレンダー作成",
        "speed": "1ヶ月分/3日",
        "pitch": "ターゲット設定からトーン設計まで一貫し、継続運用に耐える型を作ります。",
    },
    {
        "slug": "spreadsheet",
        "label": "スプレッドシート整備・関数設計",
        "skills": "Excel関数／GAS／シンプルなダッシュボード",
        "speed": "中規模1日",
        "pitch": "誰が触っても壊れない設計で、引き継ぎを前提に整備します。",
    },
]


def _genre_for(d: datetime) -> dict:
    digest = hashlib.sha256(d.date().isoformat().encode()).digest()
    return GENRES[digest[1] % len(GENRES)]


def _profile_name() -> str:
    return env("CW_PROFILE_NAME", "高岡（フリーランス）")


def build_crowdworks_application(now: datetime | None = None) -> Path:
    now = now or datetime.now()
    genre = _genre_for(now)
    name = _profile_name()

    text = f"""はじめまして、{name}と申します。

【対応可能業務】
{genre['label']}

【スキル・ツール】
{genre['skills']}

【作業スピード目安】
{genre['speed']}

【一言】
{genre['pitch']}
ご指示内容を正確に確認し、納期厳守で丁寧に作業いたします。
不明点はその都度確認させていただきます。
まずは少量・短期からでも対応可能です。
ご検討のほど、よろしくお願いいたします。
"""

    body = f"""# CrowdWorks 応募文（自動生成）

- 生成日時：{now.isoformat(timespec='seconds')}
- 想定ジャンル：{genre['label']}（slug: `{genre['slug']}`）

## 応募文（コピペ用）

```
{text}
```

## 同ジャンルでの実績欄テンプレ
- 過去の類似案件：（記入欄）
- 直近1ヶ月の納品件数：（記入欄）
- 納期遵守率：100%（実績ベースで更新）

## 応募チェック
- [ ] 案件ページの必須スキル要件と上記スキルが一致している
- [ ] 単価が `CW_MIN_HOURLY` (環境変数) を下回っていない
- [ ] 同一クライアントへの重複応募になっていない
- [ ] 応募後に `logs/posted_{now.strftime('%Y-%m-%d')}_cw_{genre['slug']}.log` に記録した
"""
    out = write_output(f"{stamp(now)}_crowdworks_application.md", body)
    # 純テキスト版も併出（クリップボードコピーしやすい）
    write_output(f"{stamp(now)}_crowdworks_application.txt", text)
    append_log("daily", f"crowdworks_application generated: {out.name}")
    return out


if __name__ == "__main__":
    path = build_crowdworks_application()
    print(f"CrowdWorks応募文を生成しました: {path.relative_to(OUTPUTS.parent)}")
