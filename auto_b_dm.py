#!/usr/bin/env python3
"""
auto_b_dm.py — SNS DM 一括起動ヘルパー

Instagram/X の検索タブを一括起動し、DM文をクリップボードに順番にコピー。
※ Instagram/X の直接DM自動送信は規約違反のため、
   「タブを開く + コピペ支援」で最大限効率化。
   1日2〜3件ペース厳守（BANリスク軽減）
"""

import subprocess
import time
import sys

TARGETS = [
    {
        "id": 1,
        "type": "飲食店",
        "search_url": "https://www.instagram.com/explore/tags/%E5%AF%8C%E5%B1%B1%E5%B8%82%E3%82%B0%E3%83%AB%E3%83%A1/",
        "search_hint": "Instagram #富山市グルメ",
        "dm_type": "food",
    },
    {
        "id": 2,
        "type": "飲食店",
        "search_url": "https://www.instagram.com/explore/tags/%E5%AF%8C%E5%B1%B1%E5%B8%82%E3%83%A9%E3%83%B3%E3%83%81/",
        "search_hint": "Instagram #富山市ランチ",
        "dm_type": "food",
    },
    {
        "id": 3,
        "type": "美容室",
        "search_url": "https://www.instagram.com/explore/tags/%E5%AF%8C%E5%B1%B1%E5%B8%82%E7%BE%8E%E5%AE%B9%E5%AE%A4/",
        "search_hint": "Instagram #富山市美容室",
        "dm_type": "beauty",
    },
    {
        "id": 4,
        "type": "美容室",
        "search_url": "https://www.instagram.com/explore/tags/%E5%AF%8C%E5%B1%B1%E5%B8%82%E3%83%98%E3%82%A2%E3%82%B5%E3%83%AD%E3%83%B3/",
        "search_hint": "Instagram #富山市ヘアサロン",
        "dm_type": "beauty",
    },
    {
        "id": 5,
        "type": "エステ/ネイル",
        "search_url": "https://www.instagram.com/explore/tags/%E5%AF%8C%E5%B1%B1%E5%B8%82%E3%83%8D%E3%82%A4%E3%83%AB/",
        "search_hint": "Instagram #富山市ネイル",
        "dm_type": "beauty",
    },
    {
        "id": 6,
        "type": "税理士",
        "search_url": "https://twitter.com/search?q=%E7%A8%8E%E7%90%86%E5%A3%AB%20%E5%AF%8C%E5%B1%B1&f=user",
        "search_hint": "X 税理士 富山",
        "dm_type": "pro",
    },
    {
        "id": 7,
        "type": "行政書士",
        "search_url": "https://twitter.com/search?q=%E8%A1%8C%E6%94%BF%E6%9B%B8%E5%A3%AB%20%E5%AF%8C%E5%B1%B1&f=user",
        "search_hint": "X 行政書士 富山",
        "dm_type": "pro",
    },
]

DM_TEXTS = {
    "food": """はじめまして。SNS運用代行をしている[名前]と申します。

突然のご連絡失礼いたします。
[店名]さんのInstagramを拝見し、料理の写真がとても魅力的でご連絡しました。

現在、飲食店様向けにInstagram・X運用代行を月¥30,000〜で承っております。

▼ よくあるお悩み
・投稿が続かない
・フォロワーが増えない
・仕込みや接客で手が回らない

▼ 私ができること
・週3投稿の作成・予約投稿
・ハッシュタグ・キャプション最適化
・月次レポートで効果を見える化

まずは無料で1週間分の投稿サンプルを作成させていただきます。
ご興味があればお気軽にご返信ください。

よろしくお願いいたします。""",

    "beauty": """はじめまして。SNS運用代行をしている[名前]と申します。

[サロン名]さんのInstagramを拝見し、施術写真がとても素敵でご連絡しました。

美容室・サロン様向けにInstagram運用代行を月¥30,000〜で承っております。

▼ 提供内容
・週3〜5投稿の作成・予約投稿
・ビフォーアフター投稿の文章作成
・新メニュー・キャンペーン告知
・ハッシュタグ選定（集客特化）

施術に集中していただくため、SNSは丸ごとお任せください。

まず無料で1週間分の投稿案を作らせていただきます。
ご興味があればご返信ください。

よろしくお願いいたします。""",

    "pro": """はじめまして。SNS運用代行をしている[名前]と申します。

[事務所名]のSNSを拝見し、専門知識を多くの方に届けるお手伝いができると思いご連絡しました。

士業の先生方向けにX・Instagram運用代行を月¥50,000〜で承っております。

▼ 提供内容
・週5投稿（専門知識を分かりやすく）
・お問い合わせ増加を目的とした運用
・月次レポート

本業に集中していただけるよう、情報発信は全てお任せください。

まず無料で1週間分の投稿案を作成させていただきます。
ご興味があればご返信ください。

よろしくお願いいたします。""",
}

TYPE_LABELS = {"food": "飲食店向け", "beauty": "美容室・サロン向け", "pro": "士業向け"}

MAX_PER_DAY = 3  # 1日上限（BAN防止）


def copy_to_clipboard(text: str):
    subprocess.run("pbcopy", input=text.encode("utf-8"), check=True)


def open_url(url: str):
    subprocess.run(["open", url])


def run():
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  SNS DM 一括起動ヘルパー（今日の3件）")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  操作: Enter → 次へ  |  s → スキップ  |  q → 終了\n")
    print(f"  ※ 1日{MAX_PER_DAY}件ペース厳守（BAN防止）\n")

    done = []
    current_dm_type = None

    for target in TARGETS:
        if len(done) >= MAX_PER_DAY:
            print(f"\n  今日の上限 {MAX_PER_DAY}件に達しました。明日また実行してください。")
            break

        print(f"[{target['id']}] {target['type']} — {target['search_hint']}")

        # DM文が変わったらクリップボードを更新
        if target["dm_type"] != current_dm_type:
            current_dm_type = target["dm_type"]
            dm_text = DM_TEXTS[current_dm_type]
            copy_to_clipboard(dm_text)
            print(f"  📋 クリップボード更新: {TYPE_LABELS[current_dm_type]}DM文")

        # 検索ページを開く
        open_url(target["search_url"])
        print(f"  🌐 ブラウザ起動: {target['search_hint']}")
        print(f"  手順: 投稿停止中のアカウントを選ぶ → フォロー+いいね → DM → Cmd+V → 送信")

        ans = input("  送信完了 → Enter  ／  スキップ → s  ／  終了 → q : ").strip().lower()
        if ans == "q":
            break
        elif ans == "s":
            print("  ⏭  スキップ")
            continue
        else:
            done.append(f"{target['id']}:{target['type']}")
            print(f"  ✅ 完了\n")
        time.sleep(1)

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  DM送付完了: {len(done)}/{MAX_PER_DAY}件")
    for d in done:
        print(f"    ✅ {d}")
    print("\n  次: python3 scripts/application_tracker.py で記録")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    run()
