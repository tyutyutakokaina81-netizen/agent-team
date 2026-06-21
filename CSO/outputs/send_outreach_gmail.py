#!/usr/bin/env python3
"""
CSO: SMB営業メール送信（Gmail SMTP・アプリパスワードのみ）

設計思想:
  旧 auto_outreach_inbound.py は「富裕層企業＋LinkedIn API」前提でハードルが高かった。
  本スクリプトはリサーチ反映版：
    - ターゲットは CSV でオーナーが手入力（地元×知人優先のSMB）
    - 送信は Gmail SMTP（アプリパスワードだけ・複雑なAPI不要）
    - 1通ずつ間隔を空けて送信（迷惑メール判定・評判毀損を回避）
    - dry-run で全文プレビュー → 問題なければ本送信
    - 送信ログを KPI funnel(outreach_sent) に転記できる形で出力

オーナー準備（一度だけ）:
  1. Gmail → アカウント → セキュリティ → 2段階認証ON
  2. 「アプリパスワード」を生成（16桁）
  3. 環境変数に: export GMAIL_ADDR="you@gmail.com"  export GMAIL_APP_PW="16桁"

実行:
  python3 send_outreach_gmail.py --template targets.csv   # 入力CSV雛形を生成
  python3 send_outreach_gmail.py --service seo --dry-run   # 全文プレビュー（送信しない）
  python3 send_outreach_gmail.py --service seo             # 本送信（5分間隔）

注意: コンテナは外部ネットブロック。本送信はオーナーのMac/PCで行う。
"""

import argparse
import csv
import os
import smtplib
import sys
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path

CSV_PATH = Path(__file__).parent / "targets.csv"
LOG_PATH = Path(__file__).parent / "outreach_sent_log.csv"

# 件名と本文（リサーチ反映版・SMB向け）。{company}{name}{industry}{sample_url} を差し込む
SERVICES = {
    "seo": {
        "subject": "{industry}のブログ記事、月数本だけ書きます",
        "body": """{company}
{name}さま

突然のご連絡失礼します。富山で個人でライティングをしている者です。

御社のブログ／お知らせを拝見し、
「更新の時間がなかなか取れない」課題がありそうだと感じ、ご連絡しました。

AIを使った下調べ＋人の手による校正で、
SEOを意識した記事を1本¥18,000〜で書いています。
初回はお試しで1本¥15,000、ご満足いただけなければ料金は頂きません。

・キーワード選定〜構成〜執筆〜納品まで一括
・最短5営業日／月1本から
・実物サンプル：{sample_url}

ご興味あれば、貴社の業種で「書けそうなテーマ案」を3つ無料でお送りします。
ご返信お待ちしています。
""",
    },
    "sns": {
        "subject": "御社のSNS、月の投稿を仕組みにしませんか",
        "body": """{company}
{name}さま

{industry}のSNS、「続けたいけど更新が止まる」状態になっていませんか。

月¥50,000〜で、以下をまるごと引き受けます：
・月20本の投稿案＋作成（写真は貴社支給 or ご相談）
・投稿カレンダーで「何を・いつ」を見える化
・月1回、数字（フォロワー／反応）の簡単レポート

初月は¥50,000・1ヶ月単位でOK（長期の縛りなし）。
合わなければ1ヶ月でやめられます。

サンプルのコンテンツカレンダーを無料でお見せできます。ご興味ありますか？

実物の発信例：{sample_url}
""",
    },
}


def make_template_csv():
    """ターゲット入力用CSVの雛形を生成"""
    if CSV_PATH.exists():
        print(f"⚠️ 既に存在します: {CSV_PATH}（上書きしません）")
        return
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["email", "company", "name", "industry", "sample_url", "sent"])
        w.writerow(["example@shop.jp", "株式会社サンプル 御中", "ご担当者", "飲食店",
                    "https://note.com/safe_canna441/n/nbf4956be87e5", ""])
    print(f"✅ 雛形を生成: {CSV_PATH}")
    print("   1行ずつ実在の見込み客を追記してください（地元×知人経由を優先）")
    print("   sent列は空のまま。送信済みになると自動で日付が入ります。")


def load_targets():
    if not CSV_PATH.exists():
        print(f"❌ {CSV_PATH} がありません。--template で雛形を作ってください")
        sys.exit(1)
    with open(CSV_PATH, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def render(service: str, t: dict):
    s = SERVICES[service]
    fields = {
        "company": t.get("company", ""),
        "name": t.get("name", "ご担当者"),
        "industry": t.get("industry", "御社"),
        "sample_url": t.get("sample_url", ""),
    }
    return s["subject"].format(**fields), s["body"].format(**fields)


def log_sent(t: dict, service: str):
    new = not LOG_PATH.exists()
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["sent_at", "email", "company", "service"])
        w.writerow([datetime.now().isoformat(timespec="seconds"),
                    t.get("email"), t.get("company"), service])


def mark_sent_in_csv(targets):
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["email", "company", "name",
                                          "industry", "sample_url", "sent"])
        w.writeheader()
        w.writerows(targets)


def main():
    p = argparse.ArgumentParser(description="SMB営業メール送信（Gmail SMTP）")
    p.add_argument("--service", choices=list(SERVICES), default="seo")
    p.add_argument("--delay", type=int, default=300, help="送信間隔・秒（既定5分）")
    p.add_argument("--dry-run", action="store_true", help="送信せず全文プレビュー")
    p.add_argument("--template", action="store_true", help="入力CSV雛形を生成")
    p.add_argument("--limit", type=int, default=0, help="今回送る最大件数（0=全件）")
    args = p.parse_args()

    if args.template:
        make_template_csv()
        return

    targets = load_targets()
    pending = [t for t in targets if not t.get("sent")]
    if args.limit:
        pending = pending[:args.limit]

    if not pending:
        print("送信対象なし（全件 sent 済み or CSV が空）")
        return

    print(f"サービス: {args.service} ／ 送信対象: {len(pending)}件 ／ 間隔: {args.delay}秒")
    print("=" * 56)

    if args.dry_run:
        for t in pending:
            subj, body = render(args.service, t)
            print(f"\n--- To: {t.get('email')} ({t.get('company')}) ---")
            print(f"件名: {subj}")
            print(body)
        print("=" * 56)
        print(f"✅ dry-run: {len(pending)}件をプレビュー（送信していません）")
        print("   本送信は --dry-run を外し、GMAIL_ADDR / GMAIL_APP_PW を設定してください")
        return

    # 本送信：認証情報チェック
    addr = os.environ.get("GMAIL_ADDR")
    pw = os.environ.get("GMAIL_APP_PW")
    if not addr or not pw:
        print("❌ 環境変数 GMAIL_ADDR と GMAIL_APP_PW を設定してください")
        sys.exit(1)

    sent_count = 0
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(addr, pw)
        for i, t in enumerate(pending):
            subj, body = render(args.service, t)
            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subj
            msg["From"] = formataddr(("", addr))
            msg["To"] = t["email"]
            try:
                server.send_message(msg)
                t["sent"] = datetime.now().strftime("%Y-%m-%d")
                log_sent(t, args.service)
                sent_count += 1
                print(f"✅ 送信 {sent_count}/{len(pending)}: {t.get('company')}")
            except Exception as e:
                print(f"⚠️ 失敗: {t.get('email')} → {e}")
            if i < len(pending) - 1:
                time.sleep(args.delay)

    mark_sent_in_csv(targets)
    print("=" * 56)
    print(f"✅ 送信完了: {sent_count}件")
    print(f"📝 ログ: {LOG_PATH}")
    print(f"→ KPI記録: kpi_dashboard.py --record の outreach_sent に {sent_count} を入力")


if __name__ == "__main__":
    main()
