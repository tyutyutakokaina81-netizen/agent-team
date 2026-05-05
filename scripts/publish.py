"""publish.py — note/BOOTH/SNS 投稿補助スクリプト

apply.py と同じパターンで、登録・告知作業を「コピー＆貼り付け→Enter」だけで進める。
オーナーは最終アップの承認（ブラウザでボタンを押す）のみ。

使い方:
  python3 publish.py             # タスク一覧
  python3 publish.py 1           # タスク1のみ実行
  python3 publish.py 1 2 3       # 連続実行
  python3 publish.py all         # 全タスク順次実行
"""
import csv
import datetime as dt
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).parent.parent
LOG = REPO / "scripts/publish_log.csv"
LOG_HEADER = ["date", "task", "status", "note"]

# ---- タスク定義 -----------------------------------------------------------
# 本文はソースファイルから動的読み込みは避け、既存の販売ページMDの該当部分を直貼り
NOTE_NEW = "https://note.com/notes/new"
BOOTH_NEW = "https://manage.booth.pm/items/new"
X_NEW = "https://twitter.com/compose/tweet"
IG_NEW = "https://www.instagram.com/"
FB_NEW = "https://www.facebook.com/"

VOL2_NOTE_TITLE = "【月30分で1ヶ月の投稿が完成】SNS投稿カレンダー｜Instagram・X・Facebook対応"
VOL3_NOTE_TITLE = "【飲食店SNS担当者必見】AIに貼るだけで投稿文が30秒で完成｜プロンプト20選"
VOL4_NOTE_TITLE = "【3点セット・32%OFF】フリーランス独立スターターパック｜収支管理+SNSカレンダー+プロンプト集"

VOL2_X_A = """SNSの投稿、毎日「何書こう…」で消耗していませんか？

月初の30分で1ヶ月分の投稿計画が完成するスプレッドシートを作りました。

✅Instagram・X・Facebook同時管理
✅投稿テーマ50選付き
✅自動集計でグラフ表示

¥680で、もう「何書こう」に悩まない。

[note URL]

#SNS運用 #フリーランス"""

VOL2_X_B = """SNS運用が続かない原因の9割は「思いつかない」という小さな摩擦です。

これが解決すると、投稿継続率が劇的に変わります。

月30分で1ヶ月分の投稿カレンダーが完成するテンプレ、リリースしました。

価格：¥680（コーヒー2杯分）

[note URL]"""

VOL2_IG = """SNS運用に悩む全ての人へ📅

【月30分で1ヶ月の投稿が完成】
SNS投稿カレンダー Googleスプレッドシート、リリースしました。

✅Instagram・X・Facebookを一括管理
✅投稿テーマ50選付き（ネタ切れ防止）
✅自動集計で振り返りもラクラク

詳細はプロフィールリンクから🔗

#SNS運用 #フリーランス #個人事業主 #SNSマーケティング
#インスタ運用 #投稿カレンダー #スプレッドシート #テンプレート"""

VOL2_FB = """SNS投稿カレンダー Googleスプレッドシート版を公開しました。

「毎日何を投稿すればいいかわからない」を解決するために作った
シンプルなスプレッドシートです。

月初の30分で1ヶ月分の投稿計画が完成します。
Instagram / X（Twitter）/ Facebook 全対応。

価格は ¥680。コーヒー2杯分です。

▼ 詳細・購入はこちら
[note URL]

ご質問はコメント欄またはメッセージでどうぞ。"""

TASKS = [
    {
        "id": 1, "name": "Vol.2 note タイトル", "url": NOTE_NEW,
        "content": VOL2_NOTE_TITLE,
        "hint": "→ 新規記事 → 有料記事 → タイトル欄に Cmd+V → 価格680円 → タグ設定 → 公開",
    },
    {
        "id": 2, "name": "Vol.2 BOOTH タイトル", "url": BOOTH_NEW,
        "content": "SNS投稿カレンダー Googleスプレッドシート【Instagram・X・Facebook対応】",
        "hint": "→ アイテム情報のタイトル欄に Cmd+V → 説明欄は vol2_sns_calendar.md の BOOTH説明文を別途貼付",
    },
    {
        "id": 3, "name": "Vol.3 note タイトル", "url": NOTE_NEW,
        "content": VOL3_NOTE_TITLE,
        "hint": "→ 新規記事 → 有料記事 → タイトル欄 → 本文は vol3_prompt_collection_restaurant.md → 価格1,980円",
    },
    {
        "id": 4, "name": "Vol.3 BOOTH タイトル", "url": BOOTH_NEW,
        "content": "AIプロンプト集：飲食店向けSNS投稿20選【ChatGPT・Claude対応】",
        "hint": "→ vol3_prompt_collection_restaurant.md の BOOTH説明文を別途貼付",
    },
    {
        "id": 5, "name": "Vol.4 note タイトル", "url": NOTE_NEW,
        "content": VOL4_NOTE_TITLE,
        "hint": "→ Vol.1〜3公開後 → 価格2,480円 → 各単品ページから Vol.4 への導線を追加",
    },
    {
        "id": 6, "name": "Vol.4 BOOTH タイトル", "url": BOOTH_NEW,
        "content": "【3点セット・32%OFF】フリーランス独立スターターパック｜収支管理+SNSカレンダー+プロンプト集",
        "hint": "→ vol4_bundle_pack.md の説明文を別途貼付",
    },
    {
        "id": 7, "name": "Vol.2 告知 X (パターンA)", "url": X_NEW,
        "content": VOL2_X_A,
        "hint": "→ note URL を [note URL] と置き換えてから投稿",
    },
    {
        "id": 8, "name": "Vol.2 告知 X (パターンB・4時間後)", "url": X_NEW,
        "content": VOL2_X_B,
        "hint": "→ パターンA投稿の4時間後にこちらを投稿（時間帯分散）",
    },
    {
        "id": 9, "name": "Vol.2 告知 Instagram", "url": IG_NEW,
        "content": VOL2_IG,
        "hint": "→ ストーリー or フィード → リンクスタンプで note URL を追加",
    },
    {
        "id": 10, "name": "Vol.2 告知 Facebook", "url": FB_NEW,
        "content": VOL2_FB,
        "hint": "→ note URL を [note URL] と置き換えてから投稿",
    },
]


def list_tasks():
    print("📋 publish.py — note/BOOTH/SNS 投稿タスク一覧\n")
    for t in TASKS:
        print(f"  {t['id']:2}. {t['name']}")
    print("\n使い方: python3 publish.py <番号> [<番号> ...]")
    print("       python3 publish.py all   （全タスク順次）")


def log_task(task_name, status, note=""):
    new = not LOG.exists()
    with LOG.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(LOG_HEADER)
        w.writerow([dt.date.today().isoformat(), task_name, status, note])


def run_task(task, idx, total):
    print(f"\n[{idx}/{total}] 📝 {task['name']}")
    print(f"   {task['hint']}")
    try:
        subprocess.run("pbcopy", input=task["content"].encode(), check=True)
        print(f"   ✓ クリップボードにコピー（{len(task['content'])}文字）")
        subprocess.run(["open", task["url"]], check=True)
        print(f"   ✓ ブラウザで開いた → {task['url']}")
    except Exception as e:
        print(f"   ❌ エラー: {e}")
        log_task(task["name"], "エラー", str(e))
        return "error"
    try:
        ans = input("   投稿完了したら Enter（s=スキップ, q=中断）: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n   中断")
        return "quit"
    if ans == "q":
        return "quit"
    if ans == "s":
        log_task(task["name"], "スキップ")
        return "skip"
    log_task(task["name"], "完了")
    print("   ✅ ログ記録済")
    return "done"


def main():
    if len(sys.argv) < 2:
        list_tasks()
        return
    if sys.argv[1] == "all":
        indexes = [t["id"] - 1 for t in TASKS]
    else:
        indexes = []
        for arg in sys.argv[1:]:
            try:
                i = int(arg) - 1
            except ValueError:
                print(f"❌ 番号は整数で: {arg}")
                sys.exit(1)
            if not (0 <= i < len(TASKS)):
                print(f"❌ {arg} は範囲外（1〜{len(TASKS)}）")
                sys.exit(1)
            indexes.append(i)
    print(f"🚀 {len(indexes)}タスクを処理します")
    done = 0
    for n, i in enumerate(indexes, 1):
        result = run_task(TASKS[i], n, len(indexes))
        if result == "done":
            done += 1
        elif result == "quit":
            print("\n⏹  中断しました")
            break
    print(f"\n✅ 完了: {done}/{len(indexes)} 件をログ記録（{LOG}）")


if __name__ == "__main__":
    main()
