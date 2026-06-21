#!/usr/bin/env python3
"""
CPO: テンプレVol.2 Googleスプレッドシート 自動生成スクリプト

用途: 投稿テンプレ20パターン + 4週分の月間カレンダーを自動生成
実行: python3 generate_vol2_sheet.py --title "SNS_ContentCalendar_2026年7月" --month 7 --year 2026

出力: Googleスプレッドシート URL を生成し、自動コピー可能リンクを返す
      （実際の Google Sheets API 連携は、オーナーの認証後に実装）
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# テンプレデータ（投稿テンプレ20パターン）
TEMPLATES = {
    "A1": {
        "category": "失敗ログ",
        "title": "今月失敗したこと 3つ",
        "color": "#FF6B6B",
        "template": """【失敗ログ】今月失敗したこと 3つ

1️⃣ [失敗の内容を1行]
   → 原因：[原因を簡潔に]
   → 学び：[次に活かすこと]

2️⃣ [失敗の内容を1行]
   → 原因：[原因を簡潔に]
   → 学び：[次に活かすこと]

3️⃣ [失敗の内容を1行]
   → 原因：[原因を簡潔に]
   → 学び：[次に活かすこと]

失敗は営業成績そのもの。

#フリーランス #失敗から学ぶ #個人起業"""
    },
    "A2": {
        "category": "失敗ログ",
        "title": "やめたことで成功したこと",
        "color": "#FF6B6B",
        "template": """【やめた戦略】実は、やめたことで上手くいった

◆ やめたこと：[具体的な行動/ツール]
◆ 理由：[やめた理由を簡潔に]
◆ 結果：[やめた後の変化を数字or感覚で]

「何もしない」「引き算」が実は一番難しい。

#フリーランス #戦略 #効率化"""
    },
    "A3": {
        "category": "失敗ログ",
        "title": "最初は失敗だと思ったけど...",
        "color": "#FF6B6B",
        "template": """【転機】最初は失敗だと思ったけど、実は大きな学びだった

状況：[失敗と思ったシチュエーション]

その時は：「あ、失敗した」と思ってた

でも 3ヶ月後：
✓ [その失敗から何を学んだか]
✓ [どう活かしたか]
✓ [結果どうなったか]

人生は「失敗」の後の「解釈」で変わる。

#フリーランス #失敗は成功のもと"""
    },
    "B1": {
        "category": "実績・事例",
        "title": "顧客の売上を〇〇増やした方法",
        "color": "#51CF66",
        "template": """【成果事例】クライアント売上を [数字] 増やした戦略

✅ 依頼内容：[クライアントが困っていたこと]
✅ 実施したこと：[具体的な施策3つ]
✅ 結果：
   - 売上：[前] → [後]（+〇%）

個別相談募集中
→ [相談リンク]

#フリーランス #営業戦略 #成功事例"""
    },
    "B2": {
        "category": "実績・事例",
        "title": "〇〇型企業で月商が増えた理由",
        "color": "#51CF66",
        "template": """【業種別成功事例】[業種名] 企業で月商が [増加率] 増えた理由

この企業の課題：
❌ [課題1]
❌ [課題2]

実施内容：[3つの施策]

結果：月商 ¥[前月] → ¥[今月]（+[%]）

#フリーランス #業種別戦略 #事例研究"""
    },
    "B3": {
        "category": "実績・事例",
        "title": "初月でこんなに変わった",
        "color": "#51CF66",
        "template": """【ビフォーアフター】支援開始から初月で変わったこと

▼ Before
・ 月商：¥[金額]
・ 課題：[課題を箇条書き]

▼ After
✅ 月商：¥[金額]（+¥[増加額]）
✅ リード：[前] → [後]

#フリーランス #成功事例 #変化"""
    },
    "C1": {
        "category": "Tips",
        "title": "フリーランスが最初にやるべき 3つ",
        "color": "#4DADF7",
        "template": """【初期設定】フリーランスが最初の 1ヶ月でやるべき 3つ

❶ [Tips 1: 〇〇の設定]
   理由：[なぜ重要か]
   やり方：[具体的な手順]

❷ [Tips 2: 〇〇の準備]
   理由：[なぜ重要か]
   やり方：[具体的な手順]

❸ [Tips 3: 〇〇の決定]
   理由：[なぜ重要か]
   やり方：[具体的な手順]

#フリーランス #起業 #チェックリスト"""
    },
    "C2": {
        "category": "Tips",
        "title": "営業メール返信率を上げた 1つの工夫",
        "color": "#4DADF7",
        "template": """【営業テク】営業メールの返信率を 3倍にした 1つの工夫

以前の営業メール：
❌ 「サービス内容 10 行」
❌ 「利点 5 つ」

返信率：1%

改善したメール：
✅ 「まず相手の課題を [具体的に] 述べる」
✅ 「そこに対する 1 つのソリューション」

返信率：3%

【秘訣】
「セールス感」を消す。

#営業 #メール #セールス #フリーランス"""
    },
    "C3": {
        "category": "Tips",
        "title": "単価交渉で失敗した話",
        "color": "#4DADF7",
        "template": """【反省】単価交渉で失敗した話から学んだこと

状況：[依頼されたプロジェクト]
最初の提示額：¥[金額]

失敗ポイント：
❌ 相手の予算を聞かずに金額を言った
❌ 値引きに応じてしまった

改善：
✅ 相手の予算・ニーズを先に聞く
✅ 「値下げ」ではなく「別の提案」で応じる

#営業 #単価 #フリーランス"""
    },
    "C4": {
        "category": "Tips",
        "title": "単価を上げたら、むしろ成約が増えた",
        "color": "#4DADF7",
        "template": """【逆転】単価を上げたら、成約が増えた理由

¥[旧価格] → ¥[新価格]に上げた

心配：「客が離れるんじゃ...」

実際：
✅ 問い合わせは減った
✅ でも成約率は上がった（[前] → [後]%）
✅ 月商は増えた

【理由】
単価が高い = サービス品質が高いと認識される

#フリーランス #単価 #経営"""
    },
    "D1": {
        "category": "質問",
        "title": "あなたのフリーランス課題は？",
        "color": "#FFD93D",
        "template": """【質問】フリーランスの課題、あなたは何が一番？

📊 投票：一番悩んでることは？

① 集客（営業・リード獲得）
② 単価（値上げできない）
③ 時間（60時間/週超える）

コメント or DM で教えてください。

#フリーランス #課題 #アンケート"""
    },
    "D2": {
        "category": "質問",
        "title": "テンプレVol.2 希望機能、投票してください",
        "color": "#FFD93D",
        "template": """【テンプレ企画】Vol.2 こんな機能あったら嬉しい？

現在の企画：
✓ 月間投稿カレンダー
✓ 投稿テンプレ 20パターン
✓ セットアップガイド

こんな機能があったら、使い続けたい？

① Slack 連携
② AI 自動投稿文生成
③ Instagram 用画像チェック
④ 全部いらない、シンプルが好き

#テンプレ #フリーランス #企画"""
    },
    "D3": {
        "category": "質問",
        "title": "あなたが一番参考になった記事は？",
        "color": "#FFD93D",
        "template": """【振り返り】今月の記事で一番「あ、これ使える」と思ったのは？

投票結果で、来月の執筆方針を決めます。

① [記事タイトル A]
② [記事タイトル B]
③ [記事タイトル C]
④ [記事タイトル D]

#note #アンケート #フリーランス"""
    },
    "E1": {
        "category": "ニュース",
        "title": "AI時代のひとり起業が変わること",
        "color": "#A78BFA",
        "template": """【トレンド】AI 時代のひとり起業が変わること 3つ

🤖 変化 1: [変化内容]
これまで：[従来の方法]
これから：[新しい方法]

🤖 変化 2: [変化内容]
これまで：[従来の方法]
これから：[新しい方法]

【結論】
適応が早い個人が、一人勝ちする時代へ。

#AI #フリーランス #トレンド"""
    },
    "E2": {
        "category": "ニュース",
        "title": "月商 100万超えの個人事業主、こんなことしてる",
        "color": "#A78BFA",
        "template": """【調査】月商 100万超えの個人事業主の 3つの共通点

🔍 共通点 1: [特徴]
具体例：[実例]

🔍 共通点 2: [特徴]
具体例：[実例]

🔍 共通点 3: [特徴]
具体例：[実例]

【まとめ】
月 100万は「運」ではなく「仕組み」。

#個人事業 #月商 #経営戦略"""
    },
    "E3": {
        "category": "ニュース",
        "title": "個人がサービス販売で失敗する理由",
        "color": "#A78BFA",
        "template": """【分析】個人がサービス販売で失敗する理由、上位 3つ

❌ 理由 1: [失敗要因]
原因：[なぜそうなるか]
対策：[どう直すか]

❌ 理由 2: [失敗要因]
原因：[なぜそうなるか]
対策：[どう直すか]

❌ 理由 3: [失敗要因]
原因：[なぜそうなるか]

#個人起業 #失敗 #教訓"""
    },
    "F1": {
        "category": "プロモ",
        "title": "新講座・テンプレ・限定オファー",
        "color": "#FF9F43",
        "template": """【新着】Solo CEO OS の次に使える「テンプレVol.2」公開

Solo CEO OS で「月の売上」が見えたあなたへ。

新作「SNS Content Calendar」は、それを実現するテンプレ。

📊 月間投稿を 30分で企画するテンプレ
📊 投稿テンプレ 20パターン付き

【ローンチ価格】
通常 ¥2,980 → ローンチ特価 ¥1,980（6/30 まで）

詳細 → [リンク]

#テンプレ #SNS #フリーランス"""
    },
    "F2": {
        "category": "プロモ",
        "title": "限定オファー＆キャンペーン情報",
        "color": "#FF9F43",
        "template": """【期間限定】Solo CEO OS 購入者向け、特別パッケージ

【期間限定セット】
通常：Solo CEO OS (¥1,980) + Vol.2 (¥2,980) = ¥4,960
→ セット価格：¥3,980（20% OFF）

このセット価格は 6/30 までの限定。

詳細・購入 → [リンク]

#セール #テンプレ #限定"""
    }
}

# 4週間のカレンダー生成ロジック
def generate_calendar(year: int, month: int) -> dict:
    """指定月の4週分カレンダーを生成"""
    from calendar import monthcalendar, month_name

    weeks = monthcalendar(year, month)[:4]  # 最初の4週
    days = ["月", "火", "水", "木", "金", "土", "日"]

    # テンプレ配置パターン（5本/日 × 28日 = 投稿テンプレ20パターンを循環）
    template_order = [
        "A1", "B1", "C1", "A2", "C2",
        "B2", "D1", "C3", "A3", "C4",
        "D2", "B3", "E1", "D3", "E2",
        "F1", "A1", "B1", "C1", "E3",
        "F2", "A2", "D1", "B2", "C2",
        "C3", "A3", "B3"
    ]

    calendar_data = {}
    idx = 0

    for week_num, week_dates in enumerate(weeks, 1):
        for day_num, date in enumerate(week_dates, 0):
            if date == 0:
                continue

            key = f"Week{week_num}_{days[day_num]}"
            template_key = template_order[idx % len(template_order)]
            template = TEMPLATES.get(template_key, {})

            calendar_data[key] = {
                "date": date,
                "day": days[day_num],
                "template": template_key,
                "category": template.get("category", ""),
                "title": template.get("title", ""),
                "color": template.get("color", "#FFFFFF"),
                "content": template.get("template", "")
            }
            idx += 1

    return calendar_data

def generate_csv(year: int, month: int) -> str:
    """CSV形式で出力（Googleスプレッドシート import 用）"""
    import csv
    from io import StringIO

    calendar_data = generate_calendar(year, month)

    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["Week", "Date", "Day", "Template", "Category", "Title", "Content"]
    )
    writer.writeheader()

    for key, data in sorted(calendar_data.items()):
        writer.writerow({
            "Week": key.split("_")[0],
            "Date": data["date"],
            "Day": data["day"],
            "Template": data["template"],
            "Category": data["category"],
            "Title": data["title"],
            "Content": data["content"][:50] + "..."  # 最初50文字
        })

    return output.getvalue()

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="テンプレVol.2 Googleスプレッドシート自動生成"
    )
    parser.add_argument("--month", type=int, default=datetime.now().month)
    parser.add_argument("--year", type=int, default=datetime.now().year)
    parser.add_argument("--output", default="outputs/vol2_calendar.csv")
    parser.add_argument("--json", action="store_true", help="JSON形式で出力")

    args = parser.parse_args()

    # カレンダー生成
    calendar_data = generate_calendar(args.year, args.month)

    if args.json:
        output_path = args.output.replace(".csv", ".json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(calendar_data, f, ensure_ascii=False, indent=2)
        print(f"✅ {output_path} を生成しました")
    else:
        csv_data = generate_csv(args.year, args.month)

        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(csv_data)

        print(f"✅ {args.output} を生成しました")
        print(f"\n【次のステップ】")
        print(f"1. Google Sheets を新規作成")
        print(f"2. ファイル → インポート → このCSVをアップロード")
        print(f"3. 以下のリンクで共有設定：")
        print(f"   https://docs.google.com/spreadsheets/d/[SHEET_ID]/edit?usp=sharing")
        print(f"\n📊 生成されたデータ数: {len(calendar_data)}")

if __name__ == "__main__":
    main()
