"""
check_booth_sales.py — BOOTH売上を随時チェック（Playwright）

やること:
  1. 保存済みBOOTHセッションで管理画面にアクセス
  2. 注文履歴・売上金額を取得
  3. 新規売上があればログに記録
  4. 振込口座未登録の通知が出ていたら BANK_ACCOUNT_REQUIRED フラグを立てる
     → 口座登録自体は手動で行う（自動化しない）

実行方法:
  python3 check_booth_sales.py

cron（30分ごと）:
  */30 * * * * python3 /path/to/check_booth_sales.py >> /path/to/logs/booth_sales.log 2>&1
"""

import json
import time
from datetime import datetime
from pathlib import Path

REPO_DIR          = Path(__file__).parent
SESSION_FILE      = REPO_DIR / ".sessions" / "booth_session.json"
LOG_DIR           = REPO_DIR / "logs"
SALES_FILE        = LOG_DIR / "booth_sales.json"
ALERT_FILE        = LOG_DIR / "booth_alerts.json"
LOG_DIR.mkdir(exist_ok=True)


# ─────────────────────────────────────────────
# データ管理
# ─────────────────────────────────────────────

def load_sales() -> dict:
    if SALES_FILE.exists():
        try:
            return json.loads(SALES_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"sales": [], "last_checked": None, "total_revenue": 0}


def save_sales(data: dict):
    SALES_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_alerts() -> list:
    if ALERT_FILE.exists():
        try:
            return json.loads(ALERT_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def save_alerts(alerts: list):
    ALERT_FILE.write_text(json.dumps(alerts, ensure_ascii=False, indent=2), encoding="utf-8")


# ─────────────────────────────────────────────
# BOOTH スクレイピング
# ─────────────────────────────────────────────

def scrape_booth_sales() -> dict:
    """
    BOOTHの管理画面から売上情報を取得する（requests版・ブラウザ不要）。
    """
    if not SESSION_FILE.exists():
        return {"orders": [], "total_revenue": 0, "bank_account_required": False, "error": "セッション未設定"}

    try:
        import requests as req
    except ImportError:
        return {"orders": [], "total_revenue": 0, "bank_account_required": False, "error": "requests未インストール"}

    try:
        data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        cookie_str = data.get("cookie", "")
        if not cookie_str:
            return {"orders": [], "total_revenue": 0, "bank_account_required": False, "error": "クッキー未設定"}
    except Exception:
        return {"orders": [], "total_revenue": 0, "bank_account_required": False, "error": "セッションファイル読み込み失敗"}

    sess = req.Session()
    sess.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            sess.cookies.set(k.strip(), v.strip(), domain=".booth.pm")

    orders = []
    total_revenue = 0
    bank_account_required = False
    error = None

    try:
        import re as _re

        # 注文履歴ページ
        r = sess.get("https://manage.booth.pm/orders", timeout=15)
        if "sign_in" in r.url or "login" in r.url:
            return {"orders": [], "total_revenue": 0, "bank_account_required": False,
                    "error": "セッション期限切れ（再ログインが必要）"}

        html = r.text

        # 振込口座未登録チェック
        if "payment_account" in html and ("未登録" in html or "口座" in html):
            bank_account_required = True

        # 注文IDと金額を正規表現で抽出
        order_blocks = _re.findall(
            r'(order[_-]?\d+|#\d{6,}|注文番号[^\d]*(\d+))',
            html, _re.IGNORECASE
        )
        amounts_raw = _re.findall(r"¥([\d,]+)", html)
        for a in amounts_raw:
            v = int(a.replace(",", ""))
            if 100 <= v <= 50000:
                orders.append({"amount": v, "id": f"order_{len(orders)}", "date": ""})
                total_revenue += v

        # 売上サマリー
        r2 = sess.get("https://manage.booth.pm/stats", timeout=15)
        m = _re.search(r"累計売上[^\d]*([\d,]+)", r2.text)
        if m:
            v = int(m.group(1).replace(",", ""))
            if v > total_revenue:
                total_revenue = v
        else:
            # 最大の数値を合計売上として採用
            all_amounts = [int(a.replace(",", "")) for a in _re.findall(r"¥([\d,]+)", r2.text)]
            big = [a for a in all_amounts if a > 1000]
            if big:
                total_revenue = max(total_revenue, max(big))

    except Exception as e:
        error = str(e)

    return {
        "orders": orders,
        "total_revenue": total_revenue,
        "bank_account_required": bank_account_required,
        "error": error,
    }


# ─────────────────────────────────────────────
# メイン
# ─────────────────────────────────────────────

def main():
    now = datetime.now()
    now_str = now.strftime("%Y/%m/%d %H:%M")

    print(f"\n[{now_str}] BOOTH売上チェック開始...")

    # 既存データ読み込み
    data = load_sales()
    alerts = load_alerts()
    prev_revenue = data.get("total_revenue", 0)
    known_ids = {s.get("id") for s in data.get("sales", [])}

    # スクレイピング実行
    result = scrape_booth_sales()

    if result["error"]:
        print(f"  ⚠️  エラー: {result['error']}")
        if result["error"] == "セッション期限切れ（再ログインが必要）":
            alert = {
                "type": "session_expired",
                "message": "BOOTHセッション期限切れ。再ログインが必要です。\n  → python3 projects/2026-04-08_月30万自動化/C_テンプレ販売/auto_booth_publish.py",
                "time": now_str,
                "resolved": False,
            }
            if not any(a.get("type") == "session_expired" and not a.get("resolved") for a in alerts):
                alerts.append(alert)
                save_alerts(alerts)
                print(f"  🚨 アラート追加: {alert['message']}")
        data["last_checked"] = now_str
        save_sales(data)
        return

    # 新規注文の検出
    new_orders = []
    for order in result["orders"]:
        if order["id"] not in known_ids:
            new_orders.append(order)
            data["sales"].append({**order, "detected_at": now_str})
            known_ids.add(order["id"])

    # 売上更新
    if result["total_revenue"] > prev_revenue:
        diff = result["total_revenue"] - prev_revenue
        print(f"  🎉 新規売上: +¥{diff:,}  累計: ¥{result['total_revenue']:,}")
    elif new_orders:
        print(f"  🎉 新規注文: {len(new_orders)}件")
    else:
        print(f"  → 変化なし（累計: ¥{result['total_revenue']:,}）")

    data["total_revenue"] = result["total_revenue"]
    data["last_checked"] = now_str
    save_sales(data)

    # 口座未登録アラート（自動入力はしない・手動対応を促す）
    if result["bank_account_required"]:
        already_alerted = any(
            a.get("type") == "bank_account_required" and not a.get("resolved")
            for a in alerts
        )
        if not already_alerted:
            alert = {
                "type": "bank_account_required",
                "message": (
                    "⚠️  BOOTH振込口座が未登録です。売上を受け取るために手動で登録してください。\n"
                    "  → https://manage.booth.pm/payment_accounts"
                ),
                "time": now_str,
                "resolved": False,
            }
            alerts.append(alert)
            save_alerts(alerts)
            print(f"\n  {'='*50}")
            print(f"  🚨 ACTION REQUIRED（手動対応）")
            print(f"  {alert['message']}")
            print(f"  {'='*50}\n")

    # 未解決アラートの表示
    unresolved = [a for a in alerts if not a.get("resolved")]
    if unresolved:
        print(f"\n  未対応アラート: {len(unresolved)}件")
        for a in unresolved:
            print(f"    [{a['time']}] {a['message'].splitlines()[0]}")

    print(f"  ✅ 完了 → {SALES_FILE}")


if __name__ == "__main__":
    main()
