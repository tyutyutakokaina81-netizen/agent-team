#!/usr/bin/env python3
"""
apply_cw_today.py — CW案件 今日の5件を順番に応募
URLを開いて応募文をクリップボードにコピー → Cmd+V で貼るだけ
"""
import subprocess, time, sys

JOBS = [
    {
        "id": "A1",
        "title": "【100%採用】データ入力業務",
        "url": "https://crowdworks.jp/public/jobs/12876568",
        "text": """はじめまして。
データ入力業務で応募いたします。

ご提示の条件で問題なく対応可能です。
・指示通りの正確な作業
・ダブルチェックによるミス防止
・納期厳守・迅速な連絡対応

平日3〜5時間、土日も対応可能です。
ご指示いただければすぐに作業開始いたします。

よろしくお願いいたします。""",
    },
    {
        "id": "A2",
        "title": "ポータルサイトへの店舗入力作業",
        "url": "https://crowdworks.jp/public/jobs/13059624",
        "text": """はじめまして。
ポータルサイトへの店舗情報入力のご案件に応募いたします。

店舗データの入力作業は得意分野で、類似案件にも対応経験があります。

■ 対応スタンス
・マニュアル通りの正確な作業
・表記ゆれ・入力漏れの徹底防止
・ダブルチェックによる品質確保

平日3〜5時間確保可能で、納期厳守いたします。
ご指示いただければすぐに作業開始いたします。

よろしくお願いいたします。""",
    },
    {
        "id": "A3",
        "title": "月初3日間限定・画像情報を文字起こし",
        "url": "https://crowdworks.jp/public/jobs/12965543",
        "text": """はじめまして。
月初限定の画像→テキスト化業務に応募いたします。

画像からの文字起こし、データ入力は得意分野です。
正確性とスピードを両立できます。

■ 稼働
月初3日間は優先的に時間確保可能です。
専用システムの操作もすぐ習熟できます。

■ 強み
・ダブルチェックによるミス防止
・納期厳守
・迅速な連絡対応

ご指示いただければすぐに作業開始いたします。
よろしくお願いいたします。""",
    },
    {
        "id": "A4",
        "title": "繁忙期・好きな時間にできる簡単データ入力",
        "url": "https://crowdworks.jp/public/jobs/12876562",
        "text": """はじめまして。
繁忙期のデータ入力スタッフとして応募いたします。

■ 稼働時間の自由度
平日3〜5時間、土日も対応可能。
繁忙期はさらに時間確保できます。

■ 対応範囲
・Excel・Googleスプレッドシートでの入力
・ダブルチェックによる精度確保
・納期前倒し納品を心がけ

即日対応可能です。
ご指示いただければすぐに作業開始いたします。

よろしくお願いいたします。""",
    },
    {
        "id": "A5",
        "title": "スマートフォンを用いた事務作業",
        "url": "https://crowdworks.jp/public/jobs/12529225",
        "text": """はじめまして。
スマートフォンを用いた事務作業に応募いたします。

■ 対応可能
・スマホ操作に慣れており、スキマ時間活用可能
・事務作業（入力・確認・コピペ）の経験あり
・マニュアル通りの正確な作業

■ 稼働
平日3〜5時間、土日対応可能。
即レス（数時間以内）を心がけております。

ご指示いただければすぐに作業開始いたします。
よろしくお願いいたします。""",
    },
]


def copy_to_clipboard(text):
    subprocess.run("pbcopy", input=text.encode("utf-8"), check=True)


def open_url(url):
    subprocess.run(["open", url])


def main():
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  CW 今日の5件 応募ヘルパー")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  操作: Enter → 次の案件 | s+Enter → スキップ | q+Enter → 終了\n")

    done = []
    for job in JOBS:
        print(f"[{job['id']}] {job['title']}")
        print(f"  URL: {job['url']}")

        # URLを開く & 応募文をコピー
        open_url(job["url"])
        copy_to_clipboard(job["text"])

        print("  ✅ ブラウザ起動 + 応募文コピー完了")
        print("     → 「応募する」をクリック → Cmd+V で貼り付け → 送信")

        ans = input("  送信完了 → Enter  ／  スキップ → s+Enter : ").strip().lower()
        if ans == "q":
            break
        elif ans == "s":
            print("  ⏭  スキップ")
            continue
        else:
            done.append(job["id"])
            print(f"  ✅ {job['id']} 応募完了\n")
        time.sleep(0.5)

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  応募完了: {len(done)}/5 件 {done}")
    if done:
        print("\n  次: python3 scripts/application_tracker.py で記録")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    main()
