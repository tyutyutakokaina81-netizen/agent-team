#!/usr/bin/env python3
"""
mac_check_sales.py — BOOTH売上を30分ごとに自動チェック（Mac通知つき）
クッキーはChromeから自動再取得するので期限切れ不要
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

AGENT_DIR = Path(__file__).parent
SESSION_FILE = AGENT_DIR / ".sessions" / "booth_session.json"
LOG_FILE = AGENT_DIR / "logs" / "booth_sales.json"
ALERT_FILE = AGENT_DIR / "logs" / "booth_alerts.json"
SESSION_FILE.parent.mkdir(exist_ok=True)
LOG_FILE.parent.mkdir(exist_ok=True)


def notify(title: str, message: str):
    """Mac通知センターに通知を送る"""
    script = f'display notification "{message}" with title "{title}" sound name "Glass"'
    subprocess.run(["osascript", "-e", script], capture_output=True)


def refresh_cookie():
    """Chromeからクッキーを自動再取得して保存"""
    try:
        import browser_cookie3
        jar = browser_cookie3.chrome(domain_name='.booth.pm')
        cookies = {c.name: c.value for c in jar}
        if not cookies:
            jar = browser_cookie3.safari(domain_name='.booth.pm')
            cookies = {c.name: c.value for c in jar}
        if cookies:
            cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
            SESSION_FILE.write_text(
                json.dumps({"cookie": cookie_str, "updated": datetime.now().isoformat()}),
                encoding="utf-8"
            )
            return cookie_str
    except Exception as e:
        print(f"[cookie] 再取得失敗: {e}")
    return None


def check_sales():
    try:
        import requests
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "requests", "-q"])
        import requests

    # クッキー取得（保存済み優先、なければ再取得）
    cookie_str = None
    if SESSION_FILE.exists():
        try:
            data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
            cookie_str = data.get("cookie", "")
        except Exception:
            pass

    if not cookie_str:
        cookie_str = refresh_cookie()
    if not cookie_str:
        print(f"[{datetime.now().strftime('%H:%M')}] クッキーなし — スキップ")
        return

    # セッション作成
    sess = requests.Session()
    sess.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    })
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            sess.cookies.set(k.strip(), v.strip(), domain=".booth.pm")

    # セッション確認
    try:
        r = sess.get("https://manage.booth.pm/orders", timeout=15)
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M')}] 接続エラー: {e}")
        return

    # セッション切れ → クッキー再取得して1回リトライ
    if "sign_in" in r.url or "login" in r.url:
        print(f"[{datetime.now().strftime('%H:%M')}] セッション切れ → 再取得中...")
        cookie_str = refresh_cookie()
        if not cookie_str:
            return
        for part in cookie_str.split(";"):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                sess.cookies.set(k.strip(), v.strip(), domain=".booth.pm")
        try:
            r = sess.get("https://manage.booth.pm/orders", timeout=15)
        except Exception:
            return

    html = r.text
    now_str = datetime.now().strftime("%Y/%m/%d %H:%M")

    # 売上データ読み込み
    sales_data = {}
    if LOG_FILE.exists():
        try:
            sales_data = json.loads(LOG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass

    prev_total = sales_data.get("total_revenue", 0)

    # 金額抽出
    import re
    amounts = re.findall(r"¥([\d,]+)", html)
    total = 0
    for a in amounts:
        v = int(a.replace(",", ""))
        if 100 <= v <= 100000:
            total += v

    # 振込口座チェック
    bank_alert = "payment_account" in html and ("未登録" in html or "register" in html.lower())

    # ログ更新
    sales_data.update({
        "total_revenue": total,
        "last_checked": now_str,
    })
    LOG_FILE.write_text(json.dumps(sales_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[{now_str}] 売上: ¥{total:,}（前回: ¥{prev_total:,}）")

    # 売上増加通知
    if total > prev_total:
        diff = total - prev_total
        msg = f"+¥{diff:,} の売上！合計 ¥{total:,}"
        print(f"  🎉 {msg}")
        notify("BOOTH 売上通知", msg)

    # 振込口座通知
    if bank_alert:
        alerts = []
        if ALERT_FILE.exists():
            try:
                alerts = json.loads(ALERT_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        # 重複通知しない（24時間以内に同じ通知があればスキップ）
        already = any(a.get("type") == "bank_account" for a in alerts[-5:])
        if not already:
            notify("BOOTH【要対応】", "振込口座の登録が必要です")
            alerts.append({"type": "bank_account", "date": now_str, "resolved": False})
            ALERT_FILE.write_text(json.dumps(alerts, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  🚨 振込口座未登録アラート送信")


if __name__ == "__main__":
    check_sales()
