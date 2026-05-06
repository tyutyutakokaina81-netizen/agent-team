#!/usr/bin/env python3
"""
柱A/B コールドアウトリーチ 半自動送信ツール

【重要：オーナー手動操作が必要】
- 環境変数で SMTP 認証情報を設定
- targets.csv に実際の企業情報を入力
- --dry-run で必ずプレビュー確認してから --send

【使い方】
  # プレビュー
  python send.py --dry-run

  # 実送信（※必ず先に dry-run で確認）
  python send.py --send

  # 1日5件制限で送信（スパム判定回避）
  python send.py --send --max 5

【法令遵守】
- 特定電子メール法に基づく送信
- 全メールに事業者名・送信者名・配信停止方法を必須記載
- 無差別送信は禁止（個別調査ベースで送信すること）
"""

import argparse
import csv
import json
import os
import smtplib
import sys
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

ROOT = Path(__file__).parent
TARGETS_CSV = ROOT / "targets.csv"
TEMPLATES_DIR = ROOT / "templates"
LOG_CSV = ROOT / "logs" / "send_log.csv"

# ─────────────────────────────────
# 設定読み込み
# ─────────────────────────────────

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SENDER_NAME = os.environ.get("SENDER_NAME", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "")
SENDER_BUSINESS = os.environ.get("SENDER_BUSINESS", "")
SENDER_ADDRESS = os.environ.get("SENDER_ADDRESS", "")
UNSUBSCRIBE_URL = os.environ.get("UNSUBSCRIBE_URL", "")

# ─────────────────────────────────
# テンプレ読込
# ─────────────────────────────────

def load_template(template_id: str) -> dict:
    path = TEMPLATES_DIR / f"{template_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"テンプレが見つかりません: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def render(template: dict, target: dict) -> tuple[str, str]:
    """件名と本文をレンダリング"""
    subject = template["subject"]
    body = template["body"]

    # ターゲット情報を置換
    for key, val in target.items():
        subject = subject.replace(f"{{{key}}}", val or "")
        body = body.replace(f"{{{key}}}", val or "")

    # 送信者情報（環境変数）も置換
    config_vars = {
        "sender_name": SENDER_NAME,
        "sender_email": SENDER_EMAIL,
        "sender_business": SENDER_BUSINESS,
    }
    for key, val in config_vars.items():
        subject = subject.replace(f"{{{key}}}", val or "")
        body = body.replace(f"{{{key}}}", val or "")

    # 法令遵守の必須情報を末尾に追加
    footer = (
        "\n\n"
        "─────────────────────\n"
        f"事業者名：{SENDER_BUSINESS}\n"
        f"担当：{SENDER_NAME}\n"
        f"住所：{SENDER_ADDRESS}\n"
        f"返信用メール：{SENDER_EMAIL}\n"
        f"配信停止：{UNSUBSCRIBE_URL or '本メールに『配信停止』と返信してください'}\n"
        "※特定電子メール法に基づき表示しています"
    )
    return subject, body + footer


# ─────────────────────────────────
# 送信処理
# ─────────────────────────────────

def send_mail(to_email: str, to_name: str, subject: str, body: str) -> bool:
    msg = MIMEMultipart()
    msg["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
    msg["To"] = f"{to_name} <{to_email}>"
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"[ERROR] 送信失敗: {to_email} → {e}", file=sys.stderr)
        return False


def log_send(target: dict, template_id: str, status: str, note: str = ""):
    LOG_CSV.parent.mkdir(parents=True, exist_ok=True)
    is_new = not LOG_CSV.exists()
    with LOG_CSV.open("a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(["timestamp", "target_company", "target_email", "template_id", "status", "note"])
        w.writerow([
            datetime.now().isoformat(timespec="seconds"),
            target.get("company", ""),
            target.get("email", ""),
            template_id,
            status,
            note,
        ])


def already_sent(target_email: str, template_id: str) -> bool:
    """同じ企業に同じテンプレを過去に送ったか"""
    if not LOG_CSV.exists():
        return False
    with LOG_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("target_email") == target_email and row.get("template_id") == template_id:
                if row.get("status") == "sent":
                    return True
    return False


# ─────────────────────────────────
# メイン
# ─────────────────────────────────

def validate_config(send_mode: bool):
    """送信前の設定確認"""
    missing = []
    if send_mode:
        for var in ["SMTP_USER", "SMTP_PASS", "SENDER_NAME", "SENDER_EMAIL",
                    "SENDER_BUSINESS", "SENDER_ADDRESS"]:
            if not os.environ.get(var):
                missing.append(var)
    if missing:
        print("[ERROR] 必須環境変数が未設定:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        print("\n.env ファイルを作成して export するか、直接 export してください。", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="柱A/B コールドアウトリーチ送信ツール")
    parser.add_argument("--dry-run", action="store_true", help="プレビューのみ（実送信しない）")
    parser.add_argument("--send", action="store_true", help="実送信を実行")
    parser.add_argument("--max", type=int, default=5, help="1回の最大送信数（デフォルト5）")
    parser.add_argument("--interval", type=int, default=30, help="送信間隔（秒、デフォルト30）")
    args = parser.parse_args()

    if not (args.dry_run or args.send):
        parser.print_help()
        sys.exit(0)

    validate_config(args.send)

    if not TARGETS_CSV.exists():
        print(f"[ERROR] {TARGETS_CSV} が存在しません。targets.csv を作成してください。",
              file=sys.stderr)
        sys.exit(1)

    sent_count = 0
    skipped_count = 0
    error_count = 0

    with TARGETS_CSV.open(encoding="utf-8") as f:
        targets = list(csv.DictReader(f))

    print(f"[INFO] {len(targets)} 件のターゲットを読み込みました")
    print(f"[INFO] 最大 {args.max} 件まで処理（間隔 {args.interval} 秒）")
    print(f"[INFO] モード: {'DRY RUN' if args.dry_run else 'SEND'}")
    print()

    for i, target in enumerate(targets, 1):
        if sent_count >= args.max:
            print(f"[INFO] 上限 {args.max} 件に到達。終了。")
            break

        template_id = target.get("template_id", "").strip()
        if not template_id:
            print(f"[SKIP] {target.get('company','?')}：template_id 未指定")
            skipped_count += 1
            continue

        target_email = target.get("email", "").strip()
        if not target_email:
            print(f"[SKIP] {target.get('company','?')}：email 未指定")
            skipped_count += 1
            continue

        if already_sent(target_email, template_id):
            print(f"[SKIP] {target.get('company','?')}：送信済み")
            skipped_count += 1
            continue

        try:
            template = load_template(template_id)
        except FileNotFoundError as e:
            print(f"[ERROR] {target.get('company','?')}：{e}")
            error_count += 1
            continue

        subject, body = render(template, target)

        # プレビュー or 送信
        print("─" * 60)
        print(f"[{i}/{len(targets)}] {target.get('company','?')} ({target_email})")
        print(f"件名：{subject}")
        print(f"本文（先頭200字）：{body[:200]}...")
        print()

        if args.dry_run:
            print("[DRY-RUN] 送信せずスキップ")
            log_send(target, template_id, "dry_run")
        else:
            print(f"[SEND] {args.interval}秒待機後に送信...")
            time.sleep(args.interval)
            ok = send_mail(target_email, target.get("name", ""), subject, body)
            if ok:
                print("[SEND] 送信成功")
                log_send(target, template_id, "sent")
                sent_count += 1
            else:
                log_send(target, template_id, "error")
                error_count += 1

    print()
    print("─" * 60)
    print(f"完了：送信 {sent_count} / スキップ {skipped_count} / エラー {error_count}")


if __name__ == "__main__":
    main()
